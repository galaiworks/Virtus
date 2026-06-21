"""Proposer — ステージ 5:提案・見積(Virtus: Drafter + Designer)。

合格ゲート:価格ガードレール(決定論)・整合チェック。galai-tone を適用。
"""

from __future__ import annotations

from typing import Any

from src.agents.base import AgentResult, BaseAgent


class Proposer(BaseAgent):
    name = "proposer"

    def execute(self, task: dict[str, Any]) -> AgentResult:
        requirements = task.get("requirements", {})
        list_price = float(task.get("list_price_usd", 0.0))
        price = float(task.get("price_usd", list_price))
        proposal = {
            "title": f"{requirements.get('goal', 'AI エージェント構築')} ご提案",
            "scope": requirements.get("scope", ""),
            "success_criteria": requirements.get("success_criteria", ""),
            "sow": task.get("sow", "要件定義 → 設計 → 実装 → 検証 → 納品"),
            "skills_applied": ["galai-tone"] + self.skills,
        }
        return AgentResult(
            agent=self.name,
            content_type="proposal",
            output={
                "proposal": proposal,
                "content": str(proposal),
                "gate": {
                    "price_usd": price,
                    "list_price_usd": list_price,
                    "discount_approved": bool(task.get("discount_approved", False)),
                },
            },
            meta={"stage": 5, "price_usd": price},
        )
