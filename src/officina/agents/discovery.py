"""Discovery — ステージ 4:商談・ヒアリング・要件抽出(Faber: Discovery 層)。

合格ゲート:必須項目充足チェック。曖昧入力に強さが要るため Opus。
"""

from __future__ import annotations

from typing import Any

from src.agents.base import AgentResult, BaseAgent

#: 構造化要件の必須項目。
REQUIRED_FIELDS = ["goal", "pain_points", "scope", "success_criteria", "budget", "timeline"]


class Discovery(BaseAgent):
    name = "discovery"

    def execute(self, task: dict[str, Any]) -> AgentResult:
        notes = task.get("meeting_notes", {})
        requirements = {field: notes.get(field) for field in REQUIRED_FIELDS}
        missing = [f for f, v in requirements.items() if not v]
        return AgentResult(
            agent=self.name,
            content_type="requirements",
            output={
                "requirements": requirements,
                "pain_map": notes.get("pain_map", {}),
                "gate": {
                    "required_fields_complete": not missing,
                    "missing_fields": missing,
                },
            },
            meta={"stage": 4},
        )
