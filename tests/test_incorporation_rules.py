"""判断の型(rules)のテスト。

ガライさんのケースで確定した結論を、回帰テストとして固定する。
"""

from __future__ import annotations

from src.officina.incorporation.rules import (
    capital_advice,
    family_split_advice,
    invoice_advice,
    officer_comp_advice,
    side_income_filing_note,
)


class TestInvoice:
    def test_b2c_keeps_exemption(self) -> None:
        advice = invoice_advice("b2c")
        assert "登録しない" in advice.conclusion
        assert advice.needs_expert is True

    def test_b2b_registers(self) -> None:
        assert "登録する" in invoice_advice("b2b").conclusion

    def test_mixed_is_uncertain(self) -> None:
        advice = invoice_advice("mixed")
        assert advice.conclusion.startswith("要確認")
        assert advice.follow_up

    def test_large_capital_breaks_exemption_premise(self) -> None:
        advice = invoice_advice("b2c", capital_jpy=10_000_000)
        assert any("免税前提を満たさない" in w for w in advice.warnings)


class TestCapital:
    def test_micro_capital_warns_about_bank_account(self) -> None:
        advice = capital_advice(10_000, needs_bank_account_soon=True)
        assert "妥当" in advice.conclusion  # 免税前提は満たす
        assert any("法人口座" in w for w in advice.warnings)
        assert any("着金" in w for w in advice.warnings)

    def test_micro_capital_with_virtual_office_stacks_warning(self) -> None:
        advice = capital_advice(10_000, virtual_office=True)
        assert any("バーチャルオフィス" in w for w in advice.warnings)

    def test_capital_over_limit_loses_exemption(self) -> None:
        advice = capital_advice(10_000_000)
        assert "引き下げ" in advice.conclusion
        assert any("2 期免税を失う" in w for w in advice.warnings)


class TestOfficerComp:
    def test_full_time_rejects_one_yen(self) -> None:
        advice = officer_comp_advice("full_time", living_cost_monthly_jpy=500_000)
        assert "1 円はナシ" in advice.conclusion
        # 手取り年 600 万 -> 額面 750〜857 万のレンジが根拠に含まれる。
        assert any("7,500,000" in r for r in advice.reasons)

    def test_side_job_suppresses_comp(self) -> None:
        advice = officer_comp_advice("side")
        assert "抑える" in advice.conclusion

    def test_always_warns_about_teiki_dogaku(self) -> None:
        for mode in ("full_time", "side", ""):
            assert any("3 ヶ月以内" in w for w in officer_comp_advice(mode).warnings)

    def test_unknown_employment_is_uncertain(self) -> None:
        assert officer_comp_advice("").conclusion.startswith("要確認")


class TestFamilySplit:
    def test_always_warns_subsidy_exclusion(self) -> None:
        """設計レビュー A-1:雇用助成金と家族雇用は併用できない。"""
        advice = family_split_advice([{"relation": "配偶者", "can_work_on": "経理"}])
        assert any("3 親等以内の親族が対象外" in w for w in advice.warnings)

    def test_no_duties_means_no_split(self) -> None:
        advice = family_split_advice([{"relation": "配偶者"}])
        assert "推奨しない" in advice.conclusion
        assert any("実態" in w for w in advice.warnings)

    def test_pattern_a_within_wall(self) -> None:
        advice = family_split_advice(
            [{"relation": "配偶者", "can_work_on": "経理"}], planned_salary_jpy=1_000_000
        )
        assert "A" in advice.conclusion

    def test_pattern_b_above_wall(self) -> None:
        advice = family_split_advice(
            [{"relation": "配偶者", "can_work_on": "運用代行"}],
            planned_salary_jpy=2_500_000,
        )
        assert "B" in advice.conclusion


class TestSideIncome:
    def test_employee_under_threshold_no_filing(self) -> None:
        advice = side_income_filing_note(500_000, 350_000, True)
        assert "不要" in advice.conclusion

    def test_employee_over_threshold_requires_filing(self) -> None:
        advice = side_income_filing_note(500_000, 100_000, True)
        assert "必要" in advice.conclusion

    def test_resident_tax_warning_always_present(self) -> None:
        advice = side_income_filing_note(500_000, 400_000, True)
        assert any("住民税" in w for w in advice.warnings)

    def test_non_employee_is_uncertain(self) -> None:
        assert side_income_filing_note(500_000, 0, False).conclusion.startswith("要確認")
