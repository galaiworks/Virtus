"""Ops + Analyst — ステージ 11:アフター(請求・保守・拡張)(Virtus: Analyst)。

合格ゲート:課金トリガー(決定論)・ドリフト監視。
本番保守は 1 体あたり 0.25〜0.5 人月/継続(§3)を織り込む。
"""

from __future__ import annotations

from typing import Any

from src.agents.base import AgentResult, BaseAgent


class Ops(BaseAgent):
    name = "ops"

    def execute(self, task: dict[str, Any]) -> AgentResult:
        contract_active = bool(task.get("contract_active", True))
        deliverable_accepted = bool(task.get("deliverable_accepted", True))
        upsell = task.get("upsell_signals", [])
        return AgentResult(
            agent=self.name,
            content_type="aftercare",
            output={
                "invoice_ready": contract_active and deliverable_accepted,
                "monitoring": {"drift": "baseline_ok"},
                "upsell_proposals": [f"アップセル候補: {s}" for s in upsell],
                "gate": {
                    "contract_active": contract_active,
                    "deliverable_accepted": deliverable_accepted,
                },
            },
            meta={"stage": 11},
        )
