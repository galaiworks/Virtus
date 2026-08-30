"""Incorporation & Growth Advisor(クロエ)。

`.claude/agents/incorporation-advisor.md` の Python 実装。
法人設立 → 収益最大化 → 節税 → 助成金活用を一気通貫で伴走する。

設計上の要点:
- 判断は ``incorporation.rules`` の決定論ロジックへ委譲する(同じ入力に同じ結論)。
- **対外文書は必ず Guardian の 95 点ゲートを通す**(設計レビュー B-5)。
  不合格なら返さずエスカレーションする。
- 状態は ``IncorporationState`` に集約する(設計レビュー B-7)。
- 確定的な税務・法務助言はしない。すべての出力に専門家確認の注記を添える。
"""

from __future__ import annotations

from datetime import date
from typing import Any

from src.agents.base import AgentResult, BaseAgent
from src.officina.governance.guardian_gate import GuardianGate
from src.officina.incorporation.escalation import check_escalations
from src.officina.incorporation.grants import (
    GrantProgram,
    default_programs,
    weekly_check,
)
from src.officina.incorporation.rules import (
    Advice,
    capital_advice,
    family_split_advice,
    invoice_advice,
    officer_comp_advice,
    side_income_filing_note,
)
from src.officina.incorporation.state import IncorporationState, ValueEntry

#: すべての出力に添える免責(専門家の独占業務を侵さないため)。
EXPERT_DISCLAIMER = (
    "本内容は決断のための整理であり、確定的な税務・法務・社会保険の助言ではありません。"
    "最終確認は司法書士(登記)・税理士(税務)・社労士(社会保険)と行ってください。"
)

#: 対外文書とみなす task_type(Guardian の 95 点ゲートを必ず通す)。
OUTBOUND_TASKS = {"draft_outreach"}

#: 判断項目 -> ``rules`` の関数名。
_DECISION_TOPICS = {
    "invoice",
    "capital",
    "officer_comp",
    "family_split",
    "side_income",
}


class IncorporationAdvisor(BaseAgent):
    """クロエ本体。

    Args:
        model: 使用モデル。定型タスク中心のため上位モデルは必須ではない。
        brand_dna: 顧客ブランド DNA(Guardian の禁止語照合にも使う)。
        state: 顧客の設立支援状態。省略時は ``customer_id`` から新規生成。
        programs: 監視対象の助成金一覧。省略時は既定セット。
        guardian: 95 点ゲート。省略時は ``brand_dna`` を渡して生成。
        その他は ``BaseAgent`` に準じる。
    """

    name = "incorporation_advisor"

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        brand_dna: dict[str, Any] | None = None,
        *,
        state: IncorporationState | None = None,
        programs: list[GrantProgram] | None = None,
        guardian: GuardianGate | None = None,
        api_key: str | None = None,
        skills: list[str] | None = None,
        dry_run: bool = True,
    ) -> None:
        super().__init__(
            model=model,
            brand_dna=brand_dna or {},
            api_key=api_key,
            skills=skills,
            dry_run=dry_run,
        )
        self.state = state or IncorporationState(customer_id="unknown")
        self.programs = programs if programs is not None else default_programs()
        self.guardian = guardian or GuardianGate(brand_dna=self.brand_dna)

    # ------------------------------------------------------------------ #
    # エントリポイント
    # ------------------------------------------------------------------ #
    def execute(self, task: dict[str, Any]) -> AgentResult:
        """task_type に応じて処理を振り分ける。

        Args:
            task: ``task_type`` と各処理の入力を含む dict。

        Returns:
            ``AgentResult``。対外文書は Guardian 合格時のみ本文を含む。

        Raises:
            ValueError: 未知の ``task_type`` の場合。
        """
        task_type = task.get("task_type", "")
        handlers = {
            "decide_item": self._decide_item,
            "monitor_grants": self._monitor_grants,
            "check_escalations": self._check_escalations,
            "draft_outreach": self._draft_outreach,
            "value_report": self._value_report,
        }
        handler = handlers.get(task_type)
        if handler is None:
            raise ValueError(
                f"未知の task_type: {task_type!r}(利用可能: {sorted(handlers)})"
            )
        return handler(task)

    # ------------------------------------------------------------------ #
    # 意思決定
    # ------------------------------------------------------------------ #
    def _decide_item(self, task: dict[str, Any]) -> AgentResult:
        """D-1〜D-7 等の意思決定を 1 件返し、確定なら state へ記録する。"""
        topic = task.get("topic", "")
        if topic not in _DECISION_TOPICS:
            raise ValueError(f"未知の topic: {topic!r}(利用可能: {sorted(_DECISION_TOPICS)})")

        profile = {**self.state.profile, **task.get("profile", {})}
        advice = self._advise(topic, profile, task)

        # 「要確認」で始まる結論は未確定として扱う。
        confirmed = not advice.conclusion.startswith("要確認")
        if task.get("record", True):
            self.state.set_decision(
                key=task.get("decision_key", topic),
                title=task.get("title", topic),
                value=advice.conclusion,
                confirmed=confirmed,
                rationale=" / ".join(advice.reasons),
                needs_expert=advice.needs_expert,
            )

        return AgentResult(
            agent=self.name,
            content_type="incorporation_decision",
            output={
                "topic": topic,
                "conclusion": advice.conclusion,
                "reasons": advice.reasons,
                "warnings": advice.warnings,
                "follow_up": advice.follow_up,
                "confirmed": confirmed,
                "disclaimer": EXPERT_DISCLAIMER,
            },
            meta={"needs_expert": advice.needs_expert},
        )

    def _advise(self, topic: str, profile: dict[str, Any], task: dict[str, Any]) -> Advice:
        """topic ごとに ``rules`` の判断関数へ委譲する。"""
        if topic == "invoice":
            return invoice_advice(
                profile.get("client_mix", ""),
                capital_jpy=profile.get("capital_jpy"),
            )
        if topic == "capital":
            return capital_advice(
                int(profile.get("capital_jpy", 0) or 0),
                needs_bank_account_soon=bool(profile.get("expected_inflow_jpy", 0)),
                virtual_office=bool(profile.get("virtual_office", False)),
            )
        if topic == "officer_comp":
            return officer_comp_advice(
                profile.get("employment", ""),
                living_cost_monthly_jpy=int(profile.get("living_cost_monthly_jpy", 0) or 0),
            )
        if topic == "family_split":
            return family_split_advice(
                profile.get("family"),
                planned_salary_jpy=int(task.get("planned_salary_jpy", 0) or 0),
            )
        # side_income
        return side_income_filing_note(
            int(profile.get("existing_personal_sales_jpy", 0) or 0),
            int(task.get("expenses_jpy", 0) or 0),
            bool(profile.get("is_employee", False)),
        )

    # ------------------------------------------------------------------ #
    # 助成金モニタ
    # ------------------------------------------------------------------ #
    def _monitor_grants(self, task: dict[str, Any]) -> AgentResult:
        """週次チェックを実行し、結果を state のウォッチリストへ反映する。"""
        today = _as_date(task.get("today"))
        profile = {**self.state.profile, **task.get("profile", {})}
        report = weekly_check(self.programs, profile, today=today)

        for candidate in report["candidates"]:
            key = candidate["key"]
            existing = self.state.watchlist.get(key, {})
            # 既定カタログの締切は未定(None)のことが多い。運用者が公式一次情報で
            # 確認して入力した締切を None で上書きしない(消すと締切エスカレーション
            # が発火しなくなり、取り逃しに直結する)。
            deadline = candidate["deadline"] or existing.get("deadline")
            days_left = candidate["days_left"]
            if days_left is None and deadline:
                days_left = _days_until(deadline, today)
            self.state.watchlist[key] = {
                **existing,
                "name": candidate["name"],
                "deadline": deadline,
                "days_left": days_left,
                "eligibility": candidate["eligibility"],
                "max_amount_jpy": candidate["max_amount_jpy"],
                # 所要期間型の制度の着手期限(エスカレーション判定が参照する)。
                "lead_time_slack_days": candidate["lead_time_slack_days"],
                # 既に着手済みならステータスを維持する。
                "status": existing.get("status", "eligible"),
            }

        return AgentResult(
            agent=self.name,
            content_type="grant_watch_report",
            output={**report, "disclaimer": EXPERT_DISCLAIMER},
            meta={"actionable": report["summary"]["actionable"]},
        )

    def _check_escalations(self, task: dict[str, Any]) -> AgentResult:
        """エスカレーション事由を検出し通知計画を返す。"""
        today = _as_date(task.get("today"))
        triggers = check_escalations(self.state, today=today)
        notifications = [t.notify() for t in triggers] if task.get("notify", False) else []
        return AgentResult(
            agent=self.name,
            content_type="escalation_report",
            output={
                "triggers": [
                    {"level": t.level, "reason": t.reason, "details": t.details}
                    for t in triggers
                ],
                "notifications": notifications,
                "highest_level": max((t.level for t in triggers), default=0),
            },
            meta={"count": len(triggers)},
        )

    # ------------------------------------------------------------------ #
    # 対外文書(Guardian 必須)
    # ------------------------------------------------------------------ #
    def _draft_outreach(self, task: dict[str, Any]) -> AgentResult:
        """専門家への依頼メール等の対外文書を生成し Guardian に通す。

        Notes:
            content_type は ``professional_inquiry``。専門家への業務依頼は
            広告宣伝メールではないため、特定電子メール法の配信解除要件は
            適用しない(過剰約束・ブランド DNA の照合は行う)。
        """
        body = task.get("body", "")
        if not body:
            raise ValueError("draft_outreach には body が必要です")

        gate = self.guardian.evaluate(body, content_type="professional_inquiry")
        approved = gate.passed

        output: dict[str, Any] = {
            "approved": approved,
            "guardian": {
                "verdict": gate.verdict.value,
                "score": gate.score,
                "reasons": gate.reasons,
            },
            "disclaimer": EXPERT_DISCLAIMER,
        }
        if approved:
            output["body"] = body
        else:
            # 不合格の本文は配布させない。改善指示のみ返す。
            output["revision_required"] = gate.reasons or ["95 点未満のため要改善"]

        return AgentResult(
            agent=self.name,
            content_type="professional_inquiry",
            output=output,
            meta={"guardian_score": gate.score, "approved": approved},
        )

    # ------------------------------------------------------------------ #
    # 北極星指標
    # ------------------------------------------------------------------ #
    def _value_report(self, task: dict[str, Any]) -> AgentResult:
        """金銭価値回収額(北極星指標)を報告する。"""
        for raw in task.get("add", []):
            self.state.add_value(ValueEntry(**raw))
        for label in task.get("confirm", []):
            self.state.confirm_value(label)

        confirmed = self.state.value_recovered("confirmed")
        potential = self.state.value_recovered("potential")
        return AgentResult(
            agent=self.name,
            content_type="value_report",
            output={
                "confirmed_jpy": confirmed,
                "potential_jpy": potential,
                "confirmed_breakdown": self.state.value_breakdown("confirmed"),
                "potential_breakdown": self.state.value_breakdown("potential"),
                "entries": [
                    {
                        "category": e.category,
                        "label": e.label,
                        "amount_jpy": e.amount_jpy,
                        "status": e.status,
                        "source": e.source,
                    }
                    for e in self.state.value_ledger
                ],
                "disclaimer": EXPERT_DISCLAIMER,
            },
            meta={"north_star_jpy": confirmed},
        )


def _as_date(value: Any) -> date | None:
    """ISO 文字列または ``date`` を ``date`` へ正規化する。"""
    if isinstance(value, date):
        return value
    if not value:
        return None
    return date.fromisoformat(str(value))


def _days_until(deadline: str, today: date | None) -> int | None:
    """ISO 文字列の締切までの残日数。解釈できなければ ``None``。"""
    try:
        return (date.fromisoformat(str(deadline)) - (today or date.today())).days
    except ValueError:
        return None
