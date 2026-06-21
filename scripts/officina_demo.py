#!/usr/bin/env python3
"""Officina パイプラインのエンドツーエンド・デモ(オフライン/API キー不要)。

1 案件を ICP リサーチ → … → 契約ゲート(🚩)→ 開発 → 納品ゲート(🚩)→ 納品まで
自律実行し、各ステージの合格ゲート結果(監査証跡)を表示する。

実行:
    python scripts/officina_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.officina.models import Deal, Lead, Stage  # noqa: E402
from src.officina.orchestrator import Orchestrator  # noqa: E402

BRAND_DNA = {
    "identity": {
        "name": "galaiworks",
        "unique_value_proposition": "海外最先端の AI を日本のひとり社長へ",
    },
    "voice": {"avoid": ["絶対", "必ず", "簡単"]},
    "forbidden": {"expressions": ["絶対稼げる", "誰でも簡単に", "魔法のような"]},
}

STAGE_INPUTS = {
    Stage.PROSPECTING: {
        "candidates": [
            {"company": "A社", "contact": "佐藤", "email": "a@a.co.jp", "score": 88},
            {"company": "B社", "contact": "鈴木", "email": "b@b.co.jp", "score": 72},
            {"company": "重複", "contact": "x", "email": "a@a.co.jp"},  # 重複→除去
            {"company": "不達", "contact": "y", "email": ""},  # 不達→除去
        ]
    },
    Stage.OUTREACH: {
        "lead": {"company": "A社", "contact": "佐藤"},
        "deliverability": {"domain_reputation": 95.0, "sent_today": 10, "domain_age_days": 30},
    },
    Stage.QUALIFY: {"reply_text": "ご連絡ありがとうございます。興味があります。資料をください。"},
    Stage.DISCOVERY: {
        "meeting_notes": {
            "goal": "集客から商談までの自動化",
            "pain_points": ["属人化", "時間不足"],
            "scope": "クライアント向け AI エージェント構築",
            "success_criteria": "月間商談 20 件",
            "budget": "12,000 USD",
            "timeline": "8 週間",
        }
    },
    Stage.PROPOSAL: {"price_usd": 12_000.0, "list_price_usd": 12_000.0},
    Stage.BUILD: {"acceptance_tests": ["疎通テスト", "品質テスト", "受入テスト"]},
}


def _print_trail(deal: Deal) -> None:
    for r in deal.history:
        mark = "🚩" if r.gate.gate_type.value == "human" else "  "
        score = f" score={r.gate.score:.0f}" if r.gate.score is not None else ""
        reasons = f" :: {'; '.join(r.gate.reasons)}" if r.gate.reasons else ""
        print(
            f" {mark} [{int(r.stage):>2}] {r.stage.name:<18} "
            f"{r.gate.gate_type.value:<13} -> {r.gate.verdict.value}{score}{reasons}"
        )


def main() -> None:
    deal = Deal(
        lead=Lead(company="株式会社デモ", contact="ガライ", email="garai@demo.co.jp"),
        acv=12_000.0,  # 低 ACV = AI 主導が機能する帯
        metadata={"icp_approved": True},  # ステージ0:ICP は人間承認済み
    )
    orch = Orchestrator(brand_dna=BRAND_DNA)

    print("=== Officina 自律実行(ICP 承認済み案件) ===")
    orch.run(deal, STAGE_INPUTS)
    _print_trail(deal)
    print(f"\n状態: {deal.status} / 現在ステージ: {deal.current_stage.name}")

    print("\n=== 🚩 ゲート A:契約締結を人間が承認 ===")
    orch.resume(deal, "approve", note="条件合意・署名済み", stage_inputs=STAGE_INPUTS)
    print(f"状態: {deal.status} / 現在ステージ: {deal.current_stage.name}")

    print("\n=== 🚩 ゲート B:納品物 最終承認を人間が承認 ===")
    orch.resume(deal, "approve", note="受入基準クリア", stage_inputs=STAGE_INPUTS)
    print(f"状態: {deal.status} / 現在ステージ: {deal.current_stage.name}")

    print("\n=== 全工程の監査証跡 ===")
    _print_trail(deal)
    print(f"\nリジェクトログ件数(= 回帰テスト数): {len(orch.reject_log)}")


if __name__ == "__main__":
    main()
