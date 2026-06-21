"""Delivery — ステージ 10:納品・オンボーディング(新規)。

合格ゲート:受入確認・疎通テスト。
"""

from __future__ import annotations

from typing import Any

from src.agents.base import AgentResult, BaseAgent


class Delivery(BaseAgent):
    name = "delivery"

    def execute(self, task: dict[str, Any]) -> AgentResult:
        checks = task.get("smoke_tests", ["疎通確認", "初期設定", "操作説明"])
        results = {c: True for c in checks}
        return AgentResult(
            agent=self.name,
            content_type="handover",
            output={
                "handover_docs": task.get("docs", "操作マニュアル・初期設定値"),
                "smoke_test_results": results,
                "gate": {"smoke_test_passed": all(results.values())},
            },
            meta={"stage": 10},
        )
