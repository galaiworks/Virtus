"""Tests for all 8 Virtus agents and orchestrator."""

from unittest.mock import MagicMock, patch

import pytest

from src.agents import (
    Analyst,
    BaseAgent,
    Connector,
    Designer,
    Distributor,
    Drafter,
    Guardian,
    LeadStrategist,
    Researcher,
)
from src.agents.guardian import Evaluation, Violation


BRAND_DNA = {
    "identity": {"name": "TestBrand"},
    "voice": {
        "tone": "プロフェッショナル × 親近感",
        "vocabulary": {
            "preferred": ["率直に言うと", "結論から"],
            "avoid": ["絶対", "必ず"],
        },
        "signature_phrases": ["率直に言います"],
    },
    "forbidden": {
        "topics": ["競合のディスり", "政治的発言"],
        "expressions": ["絶対稼げる"],
    },
    "visual": {
        "colors": ["#1a1a2e", "#eaeaea"],
        "fonts": {"heading": "Noto Sans JP", "body": "Noto Sans JP"},
    },
}


def _mock_llm_response(text: str) -> MagicMock:
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    return response


class TestBaseAgent:
    """Tests for BaseAgent."""

    def test_brand_colors(self) -> None:
        class TestAgent(BaseAgent):
            def execute(self, task):
                return {}

        agent = TestAgent(
            api_key="test", model="claude-sonnet-4-6", brand_dna=BRAND_DNA
        )
        assert agent.get_brand_colors() == ["#1a1a2e", "#eaeaea"]

    def test_brand_fonts(self) -> None:
        class TestAgent(BaseAgent):
            def execute(self, task):
                return {}

        agent = TestAgent(
            api_key="test", model="claude-sonnet-4-6", brand_dna=BRAND_DNA
        )
        assert agent.get_brand_fonts()["heading"] == "Noto Sans JP"


class TestDrafter:
    """Tests for Drafter."""

    def test_init(self) -> None:
        drafter = Drafter(api_key="test", brand_dna=BRAND_DNA)
        assert drafter.model == "claude-sonnet-4-6"
        assert "garai-tone" in drafter.skills

    def test_extract_json_from_code_block(self) -> None:
        drafter = Drafter(api_key="test", brand_dna=BRAND_DNA)
        text = '```json\n{"title": "テスト"}\n```'
        result = drafter._extract_json(text)
        assert result == {"title": "テスト"}

    def test_extract_json_inline(self) -> None:
        drafter = Drafter(api_key="test", brand_dna=BRAND_DNA)
        text = 'これは結果です: {"key": "value"}'
        result = drafter._extract_json(text)
        assert result == {"key": "value"}

    def test_unknown_task_type_uses_generic(self) -> None:
        drafter = Drafter(api_key="test", brand_dna=BRAND_DNA)
        result = drafter.execute({"task_type": "unknown_type", "context": {}})
        assert result["success"] is False


class TestLeadStrategist:
    """Tests for LeadStrategist."""

    def test_init(self) -> None:
        ls = LeadStrategist(api_key="test", brand_dna=BRAND_DNA)
        assert ls.model == "claude-opus-4-7"

    def test_morning_brief(self) -> None:
        ls = LeadStrategist(api_key="test", brand_dna=BRAND_DNA)
        ls.call_llm = MagicMock(
            return_value="おはようございます、TestBrand さん。\n【今日の優先事項】\n1. ..."
        )
        result = ls.execute({
            "task_type": "morning_brief",
            "context": {"current_date": "2026-05-23"},
        })
        assert result["success"] is True
        assert "TestBrand" in result["output"]["content"]


class TestGuardian:
    """Tests for Guardian."""

    def test_init(self) -> None:
        guardian = Guardian(api_key="test", brand_dna=BRAND_DNA)
        assert guardian.model == "claude-opus-4-7"
        assert guardian.THRESHOLD == 95

    def test_unsubscribe_check_present(self) -> None:
        guardian = Guardian(api_key="test", brand_dna=BRAND_DNA)
        assert guardian._has_unsubscribe_link("配信停止はこちら: https://...")
        assert guardian._has_unsubscribe_link("解除リンク")

    def test_unsubscribe_check_missing(self) -> None:
        guardian = Guardian(api_key="test", brand_dna=BRAND_DNA)
        assert not guardian._has_unsubscribe_link("普通のメール本文だけ")

    def test_email_without_unsubscribe_fails(self) -> None:
        guardian = Guardian(api_key="test", brand_dna=BRAND_DNA)
        violations = guardian._check_legal_compliance(
            "営業メール本文だけ。送信者情報なし。", "outreach_email"
        )
        assert any(v.severity == "CRITICAL" for v in violations)

    def test_overpromise_detection(self) -> None:
        guardian = Guardian(api_key="test", brand_dna=BRAND_DNA)
        violations = guardian._check_overpromise("絶対に成功します。100%保証。")
        assert len(violations) >= 2
        assert all(v.severity == "MAJOR" for v in violations)

    def test_critical_violation_short_circuits(self) -> None:
        guardian = Guardian(api_key="test", brand_dna=BRAND_DNA)
        result = guardian.evaluate(
            "営業メール本文だけ。送信者情報なし。", "outreach_email"
        )
        assert result.verdict == "CRITICAL_VIOLATION"
        assert result.total_score == 0


class TestResearcher:
    """Tests for Researcher."""

    def test_init(self) -> None:
        researcher = Researcher(api_key="test", brand_dna=BRAND_DNA)
        assert researcher.model == "claude-sonnet-4-6"

    def test_unknown_task(self) -> None:
        researcher = Researcher(api_key="test", brand_dna=BRAND_DNA)
        result = researcher.execute({"task_type": "unknown", "context": {}})
        assert "error" in result


class TestDistributor:
    """Tests for Distributor."""

    def test_init(self, tmp_path) -> None:
        dist = Distributor(api_key="test", brand_dna=BRAND_DNA, log_dir=tmp_path)
        assert dist.model == "claude-haiku-4-5"

    def test_unapproved_content_rejected(self, tmp_path) -> None:
        dist = Distributor(api_key="test", brand_dna=BRAND_DNA, log_dir=tmp_path)
        result = dist.execute({
            "task_type": "schedule_post",
            "context": {"approval_status": "pending"},
        })
        assert "error" in result

    def test_compliance_x_length_check(self, tmp_path) -> None:
        dist = Distributor(api_key="test", brand_dna=BRAND_DNA, log_dir=tmp_path)
        long_text = "あ" * 300
        result = dist._check_platform_compliance("x", {"text": long_text})
        assert not result["passed"]

    def test_optimal_time_calculation(self, tmp_path) -> None:
        dist = Distributor(api_key="test", brand_dna=BRAND_DNA, log_dir=tmp_path)
        result = dist.execute({
            "task_type": "calculate_optimal_time",
            "context": {"platform": "x"},
        })
        assert result["success"]
        assert "optimal_time" in result["output"]

    def test_compliant_email_has_unsubscribe(self, tmp_path) -> None:
        dist = Distributor(api_key="test", brand_dna=BRAND_DNA, log_dir=tmp_path)
        email = dist._build_compliant_email(
            content={"subject": "Test", "body": "本文"},
            recipient={"email": "user@example.com"},
            sender_info={"company_name": "Test Co", "address": "東京", "phone": "03"},
        )
        assert "解除" in email["body"]
        assert "List-Unsubscribe" in email["headers"]


class TestConnector:
    """Tests for Connector."""

    def test_init(self) -> None:
        conn = Connector(api_key="test", brand_dna=BRAND_DNA)
        assert conn.model == "claude-sonnet-4-6"

    def test_escalation_level_4_keywords(self) -> None:
        conn = Connector(api_key="test", brand_dna=BRAND_DNA)
        result = conn._check_escalation_keywords("弁護士に相談します")
        assert result is not None
        assert result["level"] == 4

    def test_escalation_level_3_keywords(self) -> None:
        conn = Connector(api_key="test", brand_dna=BRAND_DNA)
        result = conn._check_escalation_keywords("クレームです")
        assert result is not None
        assert result["level"] == 3

    def test_no_escalation_for_normal(self) -> None:
        conn = Connector(api_key="test", brand_dna=BRAND_DNA)
        assert conn._check_escalation_keywords("こんにちは!") is None

    def test_dm_with_escalation(self) -> None:
        conn = Connector(api_key="test", brand_dna=BRAND_DNA)
        result = conn.draft_dm_reply({
            "incoming_message": {"text": "弁護士を立てます"},
            "sender_profile": {},
        })
        assert result["output"]["escalation_required"] is True

    def test_follow_up_sequence(self) -> None:
        conn = Connector(api_key="test", brand_dna=BRAND_DNA)
        result = conn.execute({
            "task_type": "plan_follow_up",
            "context": {"sequence_type": "post_meeting"},
        })
        actions = result["output"]["actions"]
        assert len(actions) == 4
        assert actions[0]["action"] == "thank_you"


class TestAnalyst:
    """Tests for Analyst."""

    def test_init(self) -> None:
        analyst = Analyst(api_key="test", brand_dna=BRAND_DNA)
        assert analyst.model == "claude-sonnet-4-6"

    def test_kpi_dashboard(self) -> None:
        analyst = Analyst(api_key="test", brand_dna=BRAND_DNA)
        result = analyst.execute({
            "task_type": "kpi_dashboard",
            "context": {
                "current_metrics": {
                    "content_volume": 35,
                    "lead_acquisition": 22,
                },
                "tier": 1,
            },
        })
        assert result["success"]
        kpis = result["output"]["kpis"]
        assert kpis["content_volume"]["status"] == "達成"
        assert kpis["lead_acquisition"]["status"] == "達成"

    def test_kpi_status_thresholds(self) -> None:
        analyst = Analyst(api_key="test", brand_dna=BRAND_DNA)
        assert analyst._kpi_status(100) == "達成"
        assert analyst._kpi_status(85) == "順調"
        assert analyst._kpi_status(60) == "要注意"
        assert analyst._kpi_status(30) == "未達"


class TestOrchestrator:
    """Tests for Orchestrator."""

    def test_init(self) -> None:
        from src.orchestrator import Orchestrator

        orch = Orchestrator(api_key="test", brand_dna=BRAND_DNA)
        assert "lead_strategist" in orch.agents
        assert len(orch.agents) == 8

    def test_delegate_unknown_agent(self) -> None:
        from src.orchestrator import Orchestrator

        orch = Orchestrator(api_key="test", brand_dna=BRAND_DNA)
        result = orch.delegate("nonexistent", {})
        assert "error" in result

    def test_extract_content_text_from_dict(self) -> None:
        from src.orchestrator import Orchestrator

        orch = Orchestrator(api_key="test", brand_dna=BRAND_DNA)
        assert orch._extract_content_text({"content": "本文"}) == "本文"
        assert orch._extract_content_text({"body": "メール"}) == "メール"
        assert orch._extract_content_text({"script": "台本"}) == "台本"


class TestScheduler:
    """Tests for Scheduler."""

    def test_add_task(self) -> None:
        from src.scheduler import Scheduler

        scheduler = Scheduler()
        scheduler.add_task("test", 7, 0, lambda: "result")
        assert len(scheduler.tasks) == 1
        assert scheduler.tasks[0].name == "test"

    def test_list_tasks(self) -> None:
        from src.scheduler import Scheduler

        scheduler = Scheduler()
        scheduler.add_task("morning", 7, 0, lambda: "ok", description="朝報")
        tasks = scheduler.list_tasks()
        assert tasks[0]["schedule"] == "07:00"
        assert tasks[0]["description"] == "朝報"


class TestSkillLoader:
    """Tests for SkillLoader."""

    def test_available_skills(self) -> None:
        from src.skills import SkillLoader

        skills = SkillLoader.available()
        assert "garai-tone" in skills
        assert "dream-writing" in skills

    def test_load_existing_skill(self) -> None:
        from src.skills import SkillLoader

        content = SkillLoader.load("garai-tone")
        assert len(content) > 0

    def test_load_nonexistent_skill(self) -> None:
        from src.skills import SkillLoader

        content = SkillLoader.load("nonexistent-skill-xyz")
        assert "not found" in content.lower() or "Skill" in content


class TestFormatBrandDna:
    """Tests for format_brand_dna."""

    def test_format(self) -> None:
        from src.skills import format_brand_dna

        text = format_brand_dna(BRAND_DNA)
        assert "TestBrand" in text
        assert "プロフェッショナル" in text
        assert "絶対" in text
