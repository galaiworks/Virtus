#!/usr/bin/env python3
"""クロエの週次モニタ実行スクリプト(設計レビュー B-8)。

助成金/補助金の該当候補を洗い出し、締切からエスカレーションを判定して
状態ファイルへ反映する。cron / スケジューラから定期実行する想定。

使い方::

    python scripts/chloe_weekly_check.py --state brain/customers/founding_001/incorporation-state.json

状態ファイルが無い場合は ``--customer-id`` で新規作成する。
LLM を呼ばないためオフライン・API キー無しで動作する。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.agents.incorporation_advisor import IncorporationAdvisor  # noqa: E402
from src.officina.incorporation.state import IncorporationState  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """コマンドライン引数を定義する。"""
    parser = argparse.ArgumentParser(description="クロエ 週次助成金モニタ")
    parser.add_argument("--state", required=True, help="状態ファイル(.json / .yaml)")
    parser.add_argument("--customer-id", default="founding_001", help="新規作成時の顧客 ID")
    parser.add_argument("--today", default=None, help="判定基準日(ISO。既定は本日)")
    parser.add_argument(
        "--notify", action="store_true", help="エスカレーションの通知計画を生成する"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="状態ファイルへ書き戻さない"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """週次チェックを実行し結果を標準出力へ JSON で返す。"""
    args = build_parser().parse_args(argv)
    state_path = Path(args.state)

    if state_path.exists():
        state = IncorporationState.load(state_path)
    else:
        state = IncorporationState(customer_id=args.customer_id)

    advisor = IncorporationAdvisor(state=state, dry_run=True)
    grants = advisor.execute({"task_type": "monitor_grants", "today": args.today})
    escalations = advisor.execute(
        {"task_type": "check_escalations", "today": args.today, "notify": args.notify}
    )
    value = advisor.execute({"task_type": "value_report"})

    if not args.dry_run:
        state.save(state_path)

    report = {
        "customer_id": state.customer_id,
        "checked_at": grants.output["checked_at"],
        "grants": grants.output["summary"],
        "candidates": grants.output["candidates"],
        "escalations": escalations.output["triggers"],
        "highest_escalation_level": escalations.output["highest_level"],
        "north_star_confirmed_jpy": value.output["confirmed_jpy"],
        "north_star_potential_jpy": value.output["potential_jpy"],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    # 締切が逼迫している(Level 3 以上)場合は非ゼロで返し、
    # スケジューラ側でアラートに接続できるようにする。
    return 1 if escalations.output["highest_level"] >= 3 else 0


if __name__ == "__main__":
    raise SystemExit(main())
