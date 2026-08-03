"""IncorporationAdvisor(クロエ)のテスト。"""

from __future__ import annotations

from datetime import date

import pytest

from src.agents.incorporation_advisor import EXPERT_DISCLAIMER, IncorporationAdvisor
from src.officina.incorporation.grants import GrantProgram
from src.officina.incorporation.state import IncorporationState

TODAY = date(2026, 8, 3)

#: ガライさんのケースを模したプロフィール。
GARAI_PROFILE = {
    "industry": "AI 開発・導入支援・運用代行",
    "region": "新潟市",
    "client_mix": "b2c",
    "employment": "full_time",
    "capital_jpy": 10_000,
    "living_cost_monthly_jpy": 500_000,
    "expected_inflow_jpy": 6_500_000,
    "existing_personal_sales_jpy": 500_000,
    "is_employee": True,
    "established": False,
    "family": [{"relation": "配偶者", "can_work_on": "経理・事務"}],
}


@pytest.fixture
def advisor(brand_dna) -> IncorporationAdvisor:
    state = IncorporationState(customer_id="founding_001", profile=dict(GARAI_PROFILE))
    return IncorporationAdvisor(brand_dna=brand_dna, state=state)


class TestDispatch:
    def test_unknown_task_type_raises(self, advisor) -> None:
        with pytest.raises(ValueError, match="未知の task_type"):
            advisor.execute({"task_type": "nope"})

    def test_unknown_topic_raises(self, advisor) -> None:
        with pytest.raises(ValueError, match="未知の topic"):
            advisor.execute({"task_type": "decide_item", "topic": "nope"})


class TestDecideItem:
    def test_invoice_decision_recorded(self, advisor) -> None:
        result = advisor.execute(
            {"task_type": "decide_item", "topic": "invoice", "decision_key": "D-2"}
        )
        assert "登録しない" in result.output["conclusion"]
        assert result.output["confirmed"] is True
        assert advisor.state.decisions["D-2"].value == result.output["conclusion"]

    def test_officer_comp_uses_living_cost(self, advisor) -> None:
        result = advisor.execute({"task_type": "decide_item", "topic": "officer_comp"})
        assert "1 円はナシ" in result.output["conclusion"]

    def test_uncertain_conclusion_is_not_confirmed(self, brand_dna) -> None:
        state = IncorporationState(customer_id="c1", profile={"client_mix": "mixed"})
        advisor = IncorporationAdvisor(brand_dna=brand_dna, state=state)
        result = advisor.execute(
            {"task_type": "decide_item", "topic": "invoice", "decision_key": "D-2"}
        )
        assert result.output["confirmed"] is False
        assert advisor.state.decisions["D-2"].confirmed is False

    def test_every_decision_carries_disclaimer(self, advisor) -> None:
        for topic in ("invoice", "capital", "officer_comp", "family_split", "side_income"):
            result = advisor.execute({"task_type": "decide_item", "topic": topic})
            assert result.output["disclaimer"] == EXPERT_DISCLAIMER

    def test_record_false_leaves_state_untouched(self, advisor) -> None:
        advisor.execute({"task_type": "decide_item", "topic": "invoice", "record": False})
        assert advisor.state.decisions == {}


class TestMonitorGrants:
    def test_updates_watchlist(self, advisor) -> None:
        result = advisor.execute({"task_type": "monitor_grants", "today": "2026-08-03"})
        assert result.output["summary"]["actionable"] > 0
        assert advisor.state.watchlist  # state へ反映されている
        assert "niigata_tokutei_sogyo" in advisor.state.watchlist

    def test_preserves_existing_status(self, advisor) -> None:
        advisor.state.watchlist["jizokuka"] = {"status": "applied"}
        advisor.execute({"task_type": "monitor_grants", "today": "2026-08-03"})
        assert advisor.state.watchlist["jizokuka"]["status"] == "applied"

    def test_does_not_clobber_operator_supplied_deadline(self, advisor) -> None:
        """既定カタログの締切未定(None)で、確認済みの締切を消さないこと。

        消してしまうと締切エスカレーションが発火せず取り逃しに直結する。
        """
        advisor.state.watchlist["niigata_tokutei_sogyo"] = {
            "deadline": "2026-08-08",
            "status": "eligible",
        }
        advisor.execute({"task_type": "monitor_grants", "today": "2026-08-03"})

        entry = advisor.state.watchlist["niigata_tokutei_sogyo"]
        assert entry["deadline"] == "2026-08-08"
        assert entry["days_left"] == 5

    def test_preserved_deadline_still_escalates(self, advisor) -> None:
        advisor.state.watchlist["niigata_tokutei_sogyo"] = {
            "deadline": "2026-08-08",
            "status": "eligible",
        }
        advisor.execute({"task_type": "monitor_grants", "today": "2026-08-03"})
        result = advisor.execute({"task_type": "check_escalations", "today": "2026-08-03"})

        assert result.output["highest_level"] == 3

    def test_excludes_other_prefecture(self, brand_dna) -> None:
        state = IncorporationState(customer_id="c1", profile={"region": "大阪市"})
        advisor = IncorporationAdvisor(
            brand_dna=brand_dna,
            state=state,
            programs=[GrantProgram(key="niigata", name="新潟制度", regions=["新潟"])],
        )
        result = advisor.execute({"task_type": "monitor_grants", "today": "2026-08-03"})
        assert result.output["summary"]["actionable"] == 0


class TestEscalations:
    def test_detects_substance_risk(self, advisor) -> None:
        advisor.state.profile["family_salaries"] = [
            {"relation": "配偶者", "salary_jpy": 3_000_000}
        ]
        result = advisor.execute({"task_type": "check_escalations", "today": "2026-08-03"})
        assert result.output["highest_level"] == 4

    def test_notify_builds_channel_plan(self, advisor) -> None:
        advisor.state.profile["family_salaries"] = [
            {"relation": "配偶者", "salary_jpy": 3_000_000}
        ]
        result = advisor.execute(
            {"task_type": "check_escalations", "today": "2026-08-03", "notify": True}
        )
        assert result.output["notifications"][0]["channels"] == [
            "slack",
            "line",
            "email",
            "sms",
        ]

    def test_clean_state_has_no_triggers(self, brand_dna) -> None:
        advisor = IncorporationAdvisor(
            brand_dna=brand_dna, state=IncorporationState(customer_id="c1")
        )
        result = advisor.execute({"task_type": "check_escalations"})
        assert result.output["highest_level"] == 0


class TestGuardianIntegration:
    """設計レビュー B-5:対外文書は 95 点ゲートを必ず通す。"""

    CLEAN_BODY = (
        "はじめまして。株式会社設立の登記についてご相談させてください。"
        "商号・資本金・事業目的は要件定義書のとおりです。"
        "お見積りとスケジュールをご教示いただけますと幸いです。"
    )

    def test_clean_body_is_approved(self, advisor) -> None:
        result = advisor.execute({"task_type": "draft_outreach", "body": self.CLEAN_BODY})
        assert result.output["approved"] is True
        assert result.output["body"] == self.CLEAN_BODY

    def test_overpromise_is_blocked_and_body_withheld(self, advisor) -> None:
        body = self.CLEAN_BODY + "弊社なら必ず100%成功します。誰でも簡単に稼げます。"
        result = advisor.execute({"task_type": "draft_outreach", "body": body})
        assert result.output["approved"] is False
        assert "body" not in result.output  # 不合格の本文は配布させない
        assert result.output["revision_required"]

    def test_missing_body_raises(self, advisor) -> None:
        with pytest.raises(ValueError, match="body"):
            advisor.execute({"task_type": "draft_outreach"})

    def test_professional_inquiry_not_treated_as_ad_mail(self, advisor) -> None:
        """専門家への依頼は広告メールではないため解除動線を要求しない。"""
        result = advisor.execute({"task_type": "draft_outreach", "body": self.CLEAN_BODY})
        assert all("配信解除" not in r for r in result.output["guardian"]["reasons"])


class TestValueReport:
    def test_adds_and_confirms_entries(self, advisor) -> None:
        result = advisor.execute(
            {
                "task_type": "value_report",
                "add": [
                    {
                        "category": "tax_saving",
                        "label": "登録免許税の軽減",
                        "amount_jpy": 75_000,
                    },
                    {
                        "category": "grant",
                        "label": "起業チャレンジ応援事業",
                        "amount_jpy": 2_000_000,
                    },
                ],
                "confirm": ["登録免許税の軽減"],
            }
        )
        assert result.output["confirmed_jpy"] == 75_000
        assert result.output["potential_jpy"] == 2_000_000
        assert result.meta["north_star_jpy"] == 75_000
