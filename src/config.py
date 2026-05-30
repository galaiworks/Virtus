"""Virtus の設定ローダーとエージェントファクトリ.

`.env` から環境変数を読み、`brain/customers/{id}/brand-dna.yml` から
ブランド DNA をロードし、全エージェントをワイヤリングする.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.agents.analyst import Analyst
from src.agents.connector import Connector
from src.agents.drafter import Drafter
from src.agents.guardian import Guardian
from src.agents.lead_strategist import LeadStrategist
from src.agents.researcher import Researcher
from src.brain.store import BrainStore
from src.brand_dna import load_brand_dna
from src.orchestrator import Orchestrator
from src.prospecting.sources import PRTimesRSSSource, ProspectingSource


@dataclass
class Settings:
    """環境変数から組み立てる設定."""

    anthropic_api_key: str
    customer_id: str = "founding_001"
    customer_name: str = ""
    model_opus: str = "claude-opus-4-7"
    model_sonnet: str = "claude-sonnet-4-6"
    model_haiku: str = "claude-haiku-4-5-20251001"
    brain_dir: Path = field(default_factory=lambda: Path("brain"))

    @classmethod
    def from_env(cls, env_file: str | Path | None = ".env") -> "Settings":
        """`.env` (あれば) と環境変数から構築."""
        if env_file and Path(env_file).exists():
            load_dotenv(env_file)
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY が未設定です。.env または環境変数を確認してください。"
            )
        return cls(
            anthropic_api_key=api_key,
            customer_id=os.environ.get("CUSTOMER_ID", "founding_001"),
            customer_name=os.environ.get("CUSTOMER_NAME", ""),
            model_opus=os.environ.get("MODEL_OPUS", "claude-opus-4-7"),
            model_sonnet=os.environ.get("MODEL_SONNET", "claude-sonnet-4-6"),
            model_haiku=os.environ.get("MODEL_HAIKU", "claude-haiku-4-5-20251001"),
            brain_dir=Path(os.environ.get("BRAIN_DIR", "brain")),
        )

    @property
    def customer_brand_dna_path(self) -> Path:
        return self.brain_dir / "customers" / self.customer_id / "brand-dna.yml"

    @property
    def customer_db_path(self) -> Path:
        return self.brain_dir / "customers" / self.customer_id / "store.sqlite"


@dataclass
class VirtusTeam:
    """ワイヤリング済みの 8 体エージェントチーム (Phase 1 は 6 体)."""

    settings: Settings
    brand_dna: dict[str, Any]
    store: BrainStore
    lead_strategist: LeadStrategist
    researcher: Researcher
    drafter: Drafter
    connector: Connector
    analyst: Analyst
    guardian: Guardian
    orchestrator: Orchestrator

    def close(self) -> None:
        """ストアと所有リソースを開放."""
        self.store.close()


def build_team(
    settings: Settings | None = None,
    brand_dna: dict[str, Any] | None = None,
    sources: list[ProspectingSource] | None = None,
    store: BrainStore | None = None,
) -> VirtusTeam:
    """全エージェントをワイヤリングして返す.

    Args:
        settings: 既存の Settings (省略時は env から).
        brand_dna: ブランド DNA (省略時は customer_brand_dna_path から).
        sources: Researcher のソース (省略時は PRTimesRSSSource).
        store: BrainStore (省略時はディスク上の customer_db_path).
    """
    settings = settings or Settings.from_env()
    brand_dna = brand_dna or load_brand_dna(settings.customer_brand_dna_path)
    store = store or BrainStore(db_path=settings.customer_db_path)
    sources = sources if sources is not None else [PRTimesRSSSource()]

    common = {
        "api_key": settings.anthropic_api_key,
        "brand_dna": brand_dna,
    }
    lead_strategist = LeadStrategist(model=settings.model_opus, **common)
    researcher = Researcher(
        model=settings.model_sonnet,
        sources=sources,
        store=store,
        **common,
    )
    drafter = Drafter(
        model=settings.model_sonnet,
        skills=["garai-tone", "dream-writing", "impact-v2-0r"],
        **common,
    )
    connector = Connector(model=settings.model_sonnet, **common)
    analyst = Analyst(model=settings.model_sonnet, store=store, **common)
    guardian = Guardian(model=settings.model_opus, **common)
    orchestrator = Orchestrator(lead_strategist, drafter, guardian)

    return VirtusTeam(
        settings=settings,
        brand_dna=brand_dna,
        store=store,
        lead_strategist=lead_strategist,
        researcher=researcher,
        drafter=drafter,
        connector=connector,
        analyst=analyst,
        guardian=guardian,
        orchestrator=orchestrator,
    )
