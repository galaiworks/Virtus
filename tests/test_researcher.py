"""Researcher エージェントの統合テスト."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.agents.researcher import Researcher
from src.brain.store import BrainStore
from src.prospecting.sources import PressRelease, ProspectingSource


class _StubSource(ProspectingSource):
    name = "stub"

    def __init__(self, releases: list[PressRelease]) -> None:
        self.releases = releases
        self.calls: list[int] = []

    def fetch(self, period_hours: int = 24):
        self.calls.append(period_hours)
        return list(self.releases)


def _release(
    title: str,
    description: str,
    source_id: str | None = None,
    categories: tuple[str, ...] = ("SaaS",),
) -> PressRelease:
    return PressRelease(
        source_id=source_id or f"id_{title}",
        title=title,
        description=description,
        url=f"https://example.com/{title}",
        published_at=datetime(2030, 5, 25, 10, 0, tzinfo=timezone.utc),
        company="テスト株式会社",
        categories=categories,
    )


def test_active_prospecting_filters_scores_and_persists(galaiworks_brand_dna):
    """フィルタ → スコアリング → 上位だけ Brain 保存、監査ログも記録."""
    high = _release(
        "シリーズ A で 5 億円の資金調達",
        "年商 12 億円規模、採用拡大も進めます",
        source_id="hi",
    )
    low = _release("新製品の発表", "詳細は HP で", source_id="lo")
    off_industry = _release(
        "ヘルスケア分野でシリーズA調達",
        "売上高 20 億円規模、採用拡大",
        source_id="off",
        categories=("ヘルスケア",),
    )
    source = _StubSource([high, low, off_industry])
    store = BrainStore()

    researcher = Researcher(
        api_key="x",
        model="claude-sonnet-4-6",
        brand_dna=galaiworks_brand_dna,
        sources=[source],
        store=store,
        client=MagicMock(),
    )

    result = researcher.execute(
        {
            "task_type": "active_prospecting",
            "context": {
                "target_industries": ["SaaS", "AI"],
                "period_hours": 24,
                "top_n": 10,
                "min_score": 60,
            },
        }
    )

    # SaaS カテゴリの 2 件のみ業界フィルタ通過、high のみ 60 点以上
    assert result["count"] == 1
    assert result["leads"][0]["title"].startswith("シリーズ A")
    assert result["leads"][0]["score"] >= 60
    assert source.calls == [24]
    assert result["fetched_by_source"]["stub"] == 3

    # Brain に保存
    top_in_brain = store.top_leads(min_score=0)
    assert len(top_in_brain) == 1

    # 監査ログ
    audit = store.recent_audit()
    assert audit[0]["agent"] == "Researcher"
    assert audit[0]["payload"]["qualified"] == 1
    assert audit[0]["payload"]["after_industry_filter"] == 2
    store.close()


def test_researcher_requires_source(galaiworks_brand_dna):
    """ソース 0 件は初期化時に ValueError."""
    with pytest.raises(ValueError, match="最低 1 つのソース"):
        Researcher(
            api_key="x",
            model="claude-sonnet-4-6",
            brand_dna=galaiworks_brand_dna,
            sources=[],
            store=BrainStore(),
            client=MagicMock(),
        )


def test_unsupported_task_type(galaiworks_brand_dna):
    """未サポート task_type は ValueError."""
    researcher = Researcher(
        api_key="x",
        model="claude-sonnet-4-6",
        brand_dna=galaiworks_brand_dna,
        sources=[_StubSource([])],
        store=BrainStore(),
        client=MagicMock(),
    )
    with pytest.raises(ValueError, match="サポートしていません"):
        researcher.execute({"task_type": "unknown"})
