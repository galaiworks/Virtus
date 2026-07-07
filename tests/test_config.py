"""config.Settings + build_team のテスト."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from src.brain.store import BrainStore
from src.config import Settings, build_team
from src.prospecting.sources import PressRelease, ProspectingSource


class _StubSource(ProspectingSource):
    name = "stub"

    def fetch(self, period_hours: int = 24) -> list[PressRelease]:
        return []


def test_settings_from_env_requires_api_key(monkeypatch, tmp_path):
    """ANTHROPIC_API_KEY が未設定なら RuntimeError."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # env_file は存在しないものを渡す
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        Settings.from_env(env_file=tmp_path / "nope.env")


def test_settings_from_env_loads_env_file(monkeypatch, tmp_path):
    """.env ファイルから値を読む."""
    env = tmp_path / ".env"
    env.write_text(
        "ANTHROPIC_API_KEY=sk-test\n"
        "CUSTOMER_ID=founding_007\n"
        "CUSTOMER_NAME=テスト顧客\n"
        "BRAIN_DIR=/tmp/brain\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CUSTOMER_ID", raising=False)

    settings = Settings.from_env(env_file=env)
    assert settings.anthropic_api_key == "sk-test"
    assert settings.customer_id == "founding_007"
    assert settings.customer_name == "テスト顧客"
    assert settings.brain_dir == Path("/tmp/brain")


def test_settings_paths_derive_from_brain_dir(tmp_path):
    settings = Settings(
        anthropic_api_key="x",
        customer_id="abc",
        brain_dir=tmp_path,
    )
    assert settings.customer_brand_dna_path == tmp_path / "customers" / "abc" / "brand-dna.yml"
    assert settings.customer_db_path == tmp_path / "customers" / "abc" / "store.sqlite"


def test_build_team_wires_all_agents(galaiworks_brand_dna, tmp_path):
    """build_team が 6 エージェントを生成し共通設定を共有する."""
    fake_client = MagicMock()
    settings = Settings(
        anthropic_api_key="sk-test",
        customer_id="test_001",
        brain_dir=tmp_path,
    )
    store = BrainStore()  # in-memory

    team = build_team(
        settings=settings,
        brand_dna=galaiworks_brand_dna,
        sources=[_StubSource()],
        store=store,
        client=fake_client,
    )

    assert team.lead_strategist.model == settings.model_opus
    assert team.researcher.model == settings.model_sonnet
    assert team.drafter.model == settings.model_sonnet
    assert team.connector.model == settings.model_sonnet
    assert team.analyst.model == settings.model_sonnet
    assert team.guardian.model == settings.model_opus
    # 全エージェントが同じブランド DNA を共有
    for agent in (
        team.lead_strategist,
        team.researcher,
        team.drafter,
        team.connector,
        team.analyst,
        team.guardian,
    ):
        assert agent.brand_dna is galaiworks_brand_dna
    # Researcher の store と Analyst の store は同一インスタンス
    assert team.researcher.store is store
    assert team.analyst.store is store
    # Drafter は規定スキルで初期化される
    assert "garai-tone" in team.drafter.skills
    # 全エージェントが同一の共有クライアントを使う (コネクション節約)
    for agent in (
        team.lead_strategist,
        team.researcher,
        team.drafter,
        team.connector,
        team.analyst,
        team.guardian,
    ):
        assert agent.client is fake_client
    team.close()


def test_build_team_reads_brand_dna_from_disk(tmp_path):
    """brand_dna 未指定時は customer_brand_dna_path から読む."""
    settings = Settings(
        anthropic_api_key="sk-test",
        customer_id="ondisk",
        brain_dir=tmp_path,
    )
    settings.customer_brand_dna_path.parent.mkdir(parents=True, exist_ok=True)
    settings.customer_brand_dna_path.write_text(
        yaml.safe_dump({"identity": {"name": "ディスク顧客"}}, allow_unicode=True),
        encoding="utf-8",
    )

    team = build_team(
        settings=settings,
        sources=[_StubSource()],
        store=BrainStore(),
        client=MagicMock(),
    )
    assert team.brand_dna["identity"]["name"] == "ディスク顧客"
    team.close()


def test_team_close_releases_sources(galaiworks_brand_dna, tmp_path):
    """VirtusTeam.close がソースの close も呼ぶ."""

    class _ClosableSource(_StubSource):
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    source = _ClosableSource()
    team = build_team(
        settings=Settings(
            anthropic_api_key="sk-test", customer_id="c", brain_dir=tmp_path
        ),
        brand_dna=galaiworks_brand_dna,
        sources=[source],
        store=BrainStore(),
        client=MagicMock(),
    )
    team.close()
    assert source.closed is True
