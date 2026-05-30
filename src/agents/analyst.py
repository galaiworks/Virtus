"""Analyst - 分析・学習・KPI 集約."""

from __future__ import annotations

from collections import Counter
from typing import Any

from src.agents.base import BaseAgent
from src.brain.store import BrainStore

ANALYST_SYSTEM = """あなたは Virtus の Analyst エージェントです。

# あなたの使命
顧客のすべての活動データを集約し、
「何が効いて、何が効かなかったか」を言語化する。

# 顧客のブランド DNA
{brand_dna}

# 守るべき原則

第一に、データドリブン判断。感覚論ではなく数字に基づく。
第二に、ハルシネーション禁止。データにないことは言わない。
第三に、勝ちパターンと負けパターンを公平に分析。
第四に、改善提案は具体的に (「もう少し」ではなく「○○を△△に変える」).
第五に、再現性を重視 (1 回の成功は偶然、3 回続いてパターン認定).
"""


class Analyst(BaseAgent):
    """分析エージェント.

    Brain 層に蓄積されたリード/監査ログを集計し、KPI サマリを返す.
    LLM は所感生成にのみ使う (集計はコードで決定的に).
    """

    SUPPORTED_TASKS = frozenset({"kpi_snapshot", "monthly_review"})

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        brand_dna: dict[str, Any],
        store: BrainStore,
        skills: list[str] | None = None,
        client: Any | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            brand_dna=brand_dna,
            skills=skills,
            client=client,
        )
        self.store = store

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        task_type = task.get("task_type")
        if task_type not in self.SUPPORTED_TASKS:
            raise ValueError(f"Analyst は task_type={task_type} をサポートしていません")
        if task_type == "kpi_snapshot":
            return self.kpi_snapshot()
        return self.monthly_review(task.get("context") or {})

    def kpi_snapshot(self) -> dict[str, Any]:
        """Brain 層から決定的に KPI を集計 (LLM 呼び出しなし)."""
        top = self.store.top_leads(limit=200, min_score=0)
        priority_counts = Counter(row["priority"] for row in top)
        recent_audit = self.store.recent_audit(limit=200)
        actions_by_agent = Counter(row["agent"] for row in recent_audit)

        return {
            "task_type": "kpi_snapshot",
            "leads": {
                "total": len(top),
                "by_priority": dict(priority_counts),
                "average_score": (
                    round(sum(row["score"] for row in top) / len(top), 1) if top else 0
                ),
                "top_5_titles": [row["title"] for row in top[:5]],
            },
            "audit": {
                "total_events": len(recent_audit),
                "by_agent": dict(actions_by_agent),
            },
        }

    def monthly_review(self, context: dict[str, Any]) -> dict[str, Any]:
        """月次レビューの所感を LLM で生成 (集計サマリは決定的)."""
        snapshot = self.kpi_snapshot()
        prior_summary = context.get("prior_month_summary", "(前月データなし)")
        kpi_targets = context.get("kpi_targets", {})

        system = ANALYST_SYSTEM.format(brand_dna=self.brand_dna_block())
        user_msg = (
            f"# 今月の集計サマリ (決定的)\n{snapshot}\n\n"
            f"# 前月サマリ\n{prior_summary}\n\n"
            f"# KPI 目標\n{kpi_targets}\n\n"
            "上記を元に月次レビューを Markdown で生成してください。\n"
            "セクション: ## 要約 / ## 勝ちパターン / ## 負けパターン / ## 改善提案 / ## 次月戦略"
        )
        text = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        return {
            "task_type": "monthly_review",
            "snapshot": snapshot,
            "report": text,
        }
