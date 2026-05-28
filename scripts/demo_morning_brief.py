"""サミット 6/4 ライブデモ用: 朝報生成エントリポイント.

使い方:
    export ANTHROPIC_API_KEY=sk-ant-...
    python -m scripts.demo_morning_brief
"""

from __future__ import annotations

import os
import sys
from datetime import date

from src.agents.lead_strategist import LeadStrategist

DEMO_BRAND_DNA = {
    "identity": {
        "name": "galaiworks (デモ)",
        "primary_target_audience": "ひとり社長・コーチ・コンサル",
    },
    "voice": {
        "tone": "プロフェッショナル × 親近感 × 直球",
        "vocabulary": {
            "preferred": ["率直に言うと", "結論から言うと", "本質は"],
            "avoid": ["絶対", "必ず", "100%", "簡単"],
        },
        "signature_phrases": ["率直に言います", "現実的かつ厳密に"],
    },
    "forbidden": {
        "expressions": ["絶対稼げる", "誰でも簡単に", "魔法のような"],
    },
}


def main() -> int:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY が未設定です。.env を確認してください。", file=sys.stderr)
        return 1

    agent = LeadStrategist(
        api_key=api_key,
        model=os.getenv("MODEL_OPUS", "claude-opus-4-7"),
        brand_dna=DEMO_BRAND_DNA,
    )

    result = agent.morning_brief(
        {
            "customer_name": "ガライ",
            "current_date": date.today().isoformat(),
            "yesterday_data": {
                "note_pv": 1240,
                "x_impressions": 8200,
                "new_leads": 3,
            },
            "active_leads": [
                {"id": "A 社", "score": 87, "stage": "1on1 セット待ち"},
                {"id": "B 社", "score": 76, "stage": "提案書送付待ち"},
            ],
            "active_deals": [
                {"id": "M 社", "stage": "月次レビュー本日 15:00"},
            ],
            "kpi_status": {
                "june_cash_target": 2_500_000,
                "june_cash_actual": 0,
                "summit_days_until": 7,
            },
        }
    )

    print("=" * 60)
    print("Virtus - Lead Strategist 朝報生成デモ")
    print("=" * 60)
    print(result["output"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
