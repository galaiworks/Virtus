"""Prospector — ステージ 1:リスト構築・エンリッチ(新規 / Clay 相当)。

シグナル層が本丸(成否の 80-90%)。検証済みリードとシグナルを返す。
合格ゲート:データ検証率・重複/不達除去。
"""

from __future__ import annotations

from typing import Any

from src.agents.base import AgentResult, BaseAgent
from src.officina.models import Lead


class Prospector(BaseAgent):
    name = "prospector"

    def execute(self, task: dict[str, Any]) -> AgentResult:
        raw = task.get("candidates", [])
        seen: set[str] = set()
        leads: list[Lead] = []
        duplicates = 0
        unreachable = 0
        for c in raw:
            email = (c.get("email") or "").strip().lower()
            if email and email in seen:
                duplicates += 1
                continue
            if email:
                seen.add(email)
            verified = bool(email) and "@" in email
            if not verified:
                unreachable += 1
                continue
            leads.append(
                Lead(
                    company=c.get("company", ""),
                    contact=c.get("contact", ""),
                    email=email,
                    source=c.get("source", ""),
                    signals=c.get("signals", []),
                    score=float(c.get("score", 0.0)),
                    verified=True,
                )
            )
        total = max(1, len(raw))
        verification_rate = len(leads) / total
        return AgentResult(
            agent=self.name,
            content_type="lead_list",
            output={
                "leads": [lead.__dict__ for lead in leads],
                "gate": {
                    "verification_rate": verification_rate,
                    "duplicates_removed": duplicates,
                    "unreachable_removed": unreachable,
                },
            },
            meta={"stage": 1, "lead_count": len(leads)},
        )
