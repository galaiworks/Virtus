"""サミット 6/4 デモ用: 能動営業ターゲット抽出.

使い方:
    export ANTHROPIC_API_KEY=sk-ant-...   # 現状は LLM 呼ばないので任意
    python -m scripts.demo_active_prospecting
"""

from __future__ import annotations

import os
import sys

from src.agents.researcher import Researcher
from src.brain.store import BrainStore
from src.prospecting.sources import PRTimesRSSSource

DEMO_BRAND_DNA = {
    "identity": {
        "name": "galaiworks (デモ)",
        "primary_target_audience": "ひとり社長・コーチ・コンサル",
    },
    "voice": {
        "vocabulary": {"avoid": ["絶対", "必ず", "100%"]},
    },
    "forbidden": {"expressions": []},
}


def main() -> int:
    api_key = os.getenv("ANTHROPIC_API_KEY", "demo")  # 探索のみなら LLM 未使用

    store = BrainStore(db_path="brain/galaiworks/leads.sqlite")
    source = PRTimesRSSSource()

    researcher = Researcher(
        api_key=api_key,
        model=os.getenv("MODEL_SONNET", "claude-sonnet-4-6"),
        brand_dna=DEMO_BRAND_DNA,
        sources=[source],
        store=store,
    )

    print("=" * 60)
    print("Virtus - Researcher 能動営業ターゲット探索デモ")
    print("=" * 60)

    try:
        result = researcher.execute(
            {
                "task_type": "active_prospecting",
                "context": {
                    "target_industries": ["AI", "SaaS", "コンサル", "DX"],
                    "period_hours": 24,
                    "top_n": 20,
                    "min_score": 60,
                },
            }
        )
    finally:
        source.close()
        store.close()

    print(f"\n取得件数 (ソース別): {result['fetched_by_source']}")
    print(f"スコア 60 以上の適格リード: {result['count']} 件")
    print(f"スキップ (60 点未満): {result['skipped']} 件")
    print("\n上位リード:")
    for lead in result["leads"][:10]:
        print(f"  [{lead['score']:>3}/{lead['priority']}] {lead['title'][:60]}")
        print(f"        {lead['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
