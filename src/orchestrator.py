"""Orchestrator - Lead Strategist が指揮する 8 体連携の最小実装."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.agents.drafter import Drafter
from src.agents.guardian import Guardian, GuardianVerdict
from src.agents.lead_strategist import LeadStrategist

MAX_RETRIES = 3


@dataclass
class OrchestrationResult:
    """1 回のワークフロー実行結果."""

    final_content: str | None
    approved: bool
    retry_count: int
    verdicts: list[GuardianVerdict] = field(default_factory=list)
    escalation_reason: str | None = None


class Orchestrator:
    """Lead Strategist を中心とした最小オーケストレーター.

    Phase 1 では「Drafter が書く → Guardian が 95 点ループ」のフローのみ実装.
    """

    def __init__(
        self,
        lead_strategist: LeadStrategist,
        drafter: Drafter,
        guardian: Guardian,
    ) -> None:
        self.lead_strategist = lead_strategist
        self.drafter = drafter
        self.guardian = guardian

    def run_write_with_guardian_loop(
        self,
        content_type: str,
        brief: str,
        extra_context: dict[str, Any] | None = None,
    ) -> OrchestrationResult:
        """Drafter が書き Guardian が 95 点ループでチェックするワークフロー.

        Args:
            content_type: 執筆種別.
            brief: 指示.
            extra_context: 追加コンテキスト.

        Returns:
            OrchestrationResult.
        """
        verdicts: list[GuardianVerdict] = []
        write_result = self.drafter.write(content_type, brief, extra_context)
        content = write_result["output"]

        for retry in range(MAX_RETRIES + 1):
            verdict = self.guardian.evaluate(content, content_type=content_type)
            verdict.retry_count = retry
            verdicts.append(verdict)

            if verdict.force_reject:
                return OrchestrationResult(
                    final_content=content,
                    approved=False,
                    retry_count=retry,
                    verdicts=verdicts,
                    escalation_reason="critical_violation",
                )

            if verdict.approved:
                return OrchestrationResult(
                    final_content=content,
                    approved=True,
                    retry_count=retry,
                    verdicts=verdicts,
                )

            # 最終試行でも未達ならエスカレーションする
            if retry == MAX_RETRIES:
                break

            # 95 点未到達 → Drafter に差し戻し
            refine_result = self.drafter.refine(content, verdict.feedback)
            content = refine_result["output"]

        return OrchestrationResult(
            final_content=content,
            approved=False,
            retry_count=MAX_RETRIES,
            verdicts=verdicts,
            escalation_reason="max_retries_exceeded",
        )

    def generate_morning_brief(self, context: dict[str, Any]) -> dict[str, Any]:
        """朝報を Lead Strategist で生成 (Guardian チェックは別途)."""
        return self.lead_strategist.morning_brief(context)
