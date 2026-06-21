"""Closer — ステージ 6:クロージング補助(新規・人間主導の補助役)。

AI は補助まで。高額・複数意思決定者の案件は人間判断(非ゴール §1.2)。
自動ゲートなし。高額時は ``human_led`` を立てて人間主導を要求する。
"""

from __future__ import annotations

from typing import Any

from src.agents.base import AgentResult, BaseAgent


class Closer(BaseAgent):
    name = "closer"

    def execute(self, task: dict[str, Any]) -> AgentResult:
        objections = task.get("objections", [])
        rebuttals = [
            {"objection": o, "response": f"「{o}」への対応案(条件整理・補助のみ)"}
            for o in objections
        ]
        return AgentResult(
            agent=self.name,
            content_type="closing_support",
            output={
                "rebuttals": rebuttals,
                "terms_summary": task.get("terms", {}),
                "gate": {},  # 自動ゲートなし。人間判断は orchestrator が ACV で制御。
            },
            meta={"stage": 6},
        )
