"""助成金の適格性判定・週次モニタ・エスカレーションのテスト。"""

from __future__ import annotations

from datetime import date

from src.officina.incorporation.escalation import (
    check_deadlines,
    check_escalations,
    check_lead_time,
    check_social_insurance_gap,
    check_substance_risk,
)
from src.officina.incorporation.grants import (
    Eligibility,
    GrantProgram,
    default_programs,
    evaluate_eligibility,
    weekly_check,
)
from src.officina.incorporation.state import IncorporationState

TODAY = date(2026, 8, 3)

NIIGATA_PROFILE = {
    "industry": "AI 開発・導入支援",
    "region": "新潟市",
    "established": False,
}


class TestEligibility:
    def test_region_mismatch_is_excluded(self) -> None:
        program = GrantProgram(key="x", name="県制度", regions=["東京"])
        result = evaluate_eligibility(program, NIIGATA_PROFILE, today=TODAY)
        assert result.eligibility is Eligibility.EXCLUDED
        assert result.actionable is False

    def test_region_match_is_likely(self) -> None:
        program = GrantProgram(key="x", name="県制度", regions=["新潟"])
        result = evaluate_eligibility(program, NIIGATA_PROFILE, today=TODAY)
        assert result.eligibility is Eligibility.LIKELY

    def test_passed_deadline_is_excluded(self) -> None:
        program = GrantProgram(
            key="x", name="終了", deadline=date(2026, 6, 18), deadline_confirmed=True
        )
        result = evaluate_eligibility(program, NIIGATA_PROFILE, today=TODAY)
        assert result.eligibility is Eligibility.EXCLUDED

    def test_unconfirmed_deadline_warns(self) -> None:
        program = GrantProgram(key="x", name="未確認", deadline=date(2026, 12, 15))
        result = evaluate_eligibility(program, NIIGATA_PROFILE, today=TODAY)
        assert any("公式一次情報" in w for w in result.warnings)

    def test_pre_establishment_warns_but_not_excluded(self) -> None:
        program = GrantProgram(key="x", name="国制度", requires_established=True)
        result = evaluate_eligibility(program, NIIGATA_PROFILE, today=TODAY)
        assert result.eligibility is not Eligibility.EXCLUDED
        assert any("設立前は申請できない" in w for w in result.warnings)

    def test_family_hiring_excluded_from_employment_subsidy(self) -> None:
        """設計レビュー A-1:家族採用ではキャリアアップ助成金を使えない。"""
        program = GrantProgram(key="career_up", name="キャリアアップ", excludes_relatives=True)
        result = evaluate_eligibility(
            program, {**NIIGATA_PROFILE, "hiring_target": "family"}, today=TODAY
        )
        assert result.eligibility is Eligibility.EXCLUDED

    def test_external_hiring_allowed_for_employment_subsidy(self) -> None:
        program = GrantProgram(key="career_up", name="キャリアアップ", excludes_relatives=True)
        result = evaluate_eligibility(
            program, {**NIIGATA_PROFILE, "hiring_target": "external"}, today=TODAY
        )
        assert result.eligibility is not Eligibility.EXCLUDED
        assert any("3 親等以内の親族は対象外" in w for w in result.warnings)


class TestWeeklyCheck:
    def test_sorts_by_nearest_deadline(self) -> None:
        programs = [
            GrantProgram(key="far", name="遠い", deadline=date(2026, 12, 15)),
            GrantProgram(key="near", name="近い", deadline=date(2026, 8, 20)),
            GrantProgram(key="none", name="未定"),
        ]
        report = weekly_check(programs, NIIGATA_PROFILE, today=TODAY)
        assert [c["key"] for c in report["candidates"]] == ["near", "far", "none"]

    def test_separates_excluded(self) -> None:
        programs = [
            GrantProgram(key="ok", name="対象", regions=["新潟"]),
            GrantProgram(key="ng", name="対象外", regions=["大阪"]),
        ]
        report = weekly_check(programs, NIIGATA_PROFILE, today=TODAY)
        assert report["summary"]["actionable"] == 1
        assert report["summary"]["excluded"] == 1

    def test_default_programs_include_niigata_and_vendor_note(self) -> None:
        programs = {p.key: p for p in default_programs()}
        assert "niigata_tokutei_sogyo" in programs
        assert programs["career_up"].excludes_relatives is True
        # ベンダー登録の代替経路(コンソーシアム)が注記されている。
        assert any("コンソーシアム" in n for n in programs["digital_ai"].notes)

    def test_confirmed_deadlines_are_marked(self) -> None:
        """締切を入れた制度は必ず確認済みフラグを立てる(二次情報を流さない)。"""
        for program in default_programs():
            if program.deadline is not None:
                assert program.deadline_confirmed is True, program.key


class TestLeadTime:
    """公募締切を持たず目標日から逆算する型の制度(特定創業支援等)。"""

    PROGRAM = GrantProgram(
        key="tokutei", name="特定創業支援", lead_time_days=45, requires_established=False
    )

    def test_slack_positive_when_in_time(self) -> None:
        result = evaluate_eligibility(
            self.PROGRAM, {"target_date": "2026-10-01"}, today=TODAY
        )
        assert result.lead_time_slack_days == 14
        assert any("残り 14 日以内に着手" in r for r in result.reasons)

    def test_slack_negative_when_too_late(self) -> None:
        # 目標 9/1 − 所要 45 日 = 着手期限 7/18。基準日 8/3 なので 16 日超過。
        result = evaluate_eligibility(
            self.PROGRAM, {"target_date": "2026-09-01"}, today=TODAY
        )
        assert result.lead_time_slack_days == -16
        assert any("間に合わない" in w for w in result.warnings)

    def test_no_target_date_means_no_slack(self) -> None:
        result = evaluate_eligibility(self.PROGRAM, {}, today=TODAY)
        assert result.lead_time_slack_days is None

    def test_overrun_escalates_level3(self) -> None:
        """着手期限の超過は金銭損失に直結するため必ず人間を呼ぶ。"""
        watchlist = {
            "tokutei": {"name": "特定創業支援", "lead_time_slack_days": -18, "status": "eligible"}
        }
        triggers = check_lead_time(watchlist)
        assert triggers[0].level == 3

    def test_near_start_deadline_escalates_level3(self) -> None:
        watchlist = {"t": {"name": "x", "lead_time_slack_days": 5, "status": "eligible"}}
        assert check_lead_time(watchlist)[0].level == 3

    def test_approaching_start_deadline_escalates_level2(self) -> None:
        watchlist = {"t": {"name": "x", "lead_time_slack_days": 12, "status": "eligible"}}
        assert check_lead_time(watchlist)[0].level == 2

    def test_ample_slack_is_quiet(self) -> None:
        watchlist = {"t": {"name": "x", "lead_time_slack_days": 60, "status": "eligible"}}
        assert check_lead_time(watchlist) == []

    def test_started_program_is_not_escalated(self) -> None:
        watchlist = {"t": {"name": "x", "lead_time_slack_days": -30, "status": "preparing"}}
        assert check_lead_time(watchlist) == []


class TestEscalation:
    def test_deadline_within_7_days_is_level3(self) -> None:
        watchlist = {
            "x": {"name": "持続化", "deadline": "2026-08-08", "status": "eligible"}
        }
        triggers = check_deadlines(watchlist, today=TODAY)
        assert triggers[0].level == 3

    def test_deadline_within_14_days_is_level2(self) -> None:
        watchlist = {
            "x": {"name": "持続化", "deadline": "2026-08-15", "status": "eligible"}
        }
        assert check_deadlines(watchlist, today=TODAY)[0].level == 2

    def test_started_application_is_not_escalated(self) -> None:
        watchlist = {
            "x": {"name": "持続化", "deadline": "2026-08-05", "status": "preparing"}
        }
        assert check_deadlines(watchlist, today=TODAY) == []

    def test_social_insurance_gap_detected(self) -> None:
        profile = {
            "employment": "full_time",
            "resignation_date": "2026-07-20",
            "establishment_date": "2026-08-10",
        }
        triggers = check_social_insurance_gap(profile)
        assert triggers[0].level == 3
        assert triggers[0].details["gap_days"] == 21

    def test_seamless_transition_has_no_gap(self) -> None:
        profile = {
            "employment": "full_time",
            "resignation_date": "2026-07-31",
            "establishment_date": "2026-08-01",
        }
        assert check_social_insurance_gap(profile) == []

    def test_side_job_skips_social_insurance_check(self) -> None:
        assert check_social_insurance_gap({"employment": "side"}) == []

    def test_salary_without_duties_is_level4(self) -> None:
        triggers = check_substance_risk(
            [{"relation": "配偶者", "salary_jpy": 2_000_000, "can_work_on": ""}]
        )
        assert triggers[0].level == 4

    def test_salary_with_duties_is_clean(self) -> None:
        assert (
            check_substance_risk(
                [{"relation": "配偶者", "salary_jpy": 1_000_000, "can_work_on": "経理"}]
            )
            == []
        )

    def test_check_escalations_sorts_by_severity(self) -> None:
        state = IncorporationState(
            customer_id="c1",
            profile={
                "employment": "full_time",
                "resignation_date": "2026-07-01",
                "establishment_date": "2026-08-10",
                "family_salaries": [{"relation": "配偶者", "salary_jpy": 3_000_000}],
            },
            watchlist={
                "x": {"name": "持続化", "deadline": "2026-08-15", "status": "eligible"}
            },
        )
        levels = [t.level for t in check_escalations(state, today=TODAY)]
        assert levels == sorted(levels, reverse=True)
        assert levels[0] == 4
