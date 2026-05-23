"""End-to-End tests for Virtus daily workflow.

Simulates a complete day of Virtus operation:
1. Morning: Lead Strategist generates brief
2. Content: Drafter writes, Guardian reviews
3. Visual: Designer creates assets
4. Distribution: Distributor schedules (stub)
5. Evening: Analyst generates report
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.analyst import Analyst
from src.agents.drafter import Drafter
from src.agents.guardian import Guardian
from src.agents.lead_strategist import LeadStrategist
from src.agents.researcher import Researcher
from src.brain import BrainLayer, BrandDNA, ContentRecord, generate_content_id
from src.onboarding import OnboardingFlow
from src.orchestrator import Orchestrator
from src.scheduler import build_default_scheduler


@pytest.fixture
def brand_dna() -> dict:
    """Production-like brand DNA."""
    return {
        "identity": {
            "name": "TestCompany",
            "business": "AIコンサルティング",
            "primary_target_audience": "ひとり社長",
            "unique_value_proposition": "AI活用で業務自動化",
        },
        "voice": {
            "tone": "プロフェッショナル × 親近感",
            "personality": ["率直", "数字に強い"],
            "preferred_phrases": ["率直に言うと", "本質は", "具体的には"],
            "avoid_phrases": ["絶対", "必ず", "100%"],
            "signature_phrases": ["これが結論です"],
        },
        "content_strategy": {
            "pillar_topics": ["AI活用", "業務自動化", "生産性向上"],
            "primary_platforms": ["note", "x"],
            "publishing_frequency": {"note": "週2本", "x": "日5本"},
        },
        "forbidden": {
            "topics": ["政治", "宗教"],
            "expressions": ["絶対稼げる", "誰でも簡単"],
            "practices": ["スパム送信"],
        },
    }


@pytest.fixture
def brain(tmp_path: Path) -> BrainLayer:
    """Brain layer for test."""
    return BrainLayer(brain_root=tmp_path / "brain")


class TestDailyWorkflow:
    """Test complete daily workflow."""

    def test_morning_brief_to_content_pipeline(self, brand_dna: dict) -> None:
        """Test morning brief triggering content creation."""
        with (
            patch.object(LeadStrategist, "call_llm") as mock_ls,
            patch.object(Drafter, "call_llm") as mock_drafter,
            patch.object(Guardian, "call_llm") as mock_guardian,
        ):
            mock_ls.return_value = """{
                "priorities": [
                    {"task": "AI活用記事", "agent": "Drafter", "priority": "high"}
                ],
                "insights": "AIトレンド上昇中",
                "recommended_topics": ["AIエージェント活用法"]
            }"""

            mock_drafter.return_value = """# AIエージェント活用法

率直に言うと、AIエージェントは2026年の必須ツールです。

## 本質は自動化

具体的には、8体のエージェントが連携して業務を処理します。

これが結論です。
"""

            mock_guardian.return_value = """{
                "total_score": 96,
                "brand_dna_compliance": 24,
                "legal_compliance": 25,
                "content_quality": 19,
                "target_fit": 14,
                "overpromise_check": 9,
                "hallucination_check": 5,
                "feedback": "高品質なコンテンツです。",
                "issues": [],
                "verdict": "APPROVED"
            }"""

            orchestrator = Orchestrator(
                api_key="test-key",
                brand_dna=brand_dna,
            )

            morning_result = orchestrator.morning_brief(
                {
                    "current_date": "2026-05-23",
                }
            )
            assert morning_result["success"] is True

            content_result = orchestrator.write_and_review(
                content_type="note_article",
                context={
                    "topic": "AIエージェント活用法",
                    "target_audience": "ひとり社長",
                },
            )
            assert content_result["status"] == "approved"
            assert "AIエージェント" in content_result["content"]

    def test_full_day_simulation(self, brand_dna: dict, brain: BrainLayer) -> None:
        """Simulate a full day of operations."""
        customer_id = "e2e_test_customer"

        brain.save_brand_dna(customer_id, BrandDNA.from_dict(brand_dna))

        with (
            patch.object(LeadStrategist, "call_llm") as mock_ls,
            patch.object(Drafter, "call_llm") as mock_drafter,
            patch.object(Guardian, "call_llm") as mock_guardian,
            patch.object(Researcher, "call_llm") as mock_researcher,
            patch.object(Analyst, "call_llm") as mock_analyst,
        ):
            mock_ls.return_value = '{"priorities": [], "insights": "Test"}'

            def drafter_response(*args, **kwargs):
                messages = kwargs.get("messages", [])
                prompt = messages[0]["content"] if messages else ""
                if "X 投稿" in prompt:
                    return '[{"text": "Test post", "hashtags": []}]'
                return '{"title": "Test", "content": "Test content"}'

            mock_drafter.side_effect = drafter_response
            mock_guardian.return_value = """{
                "total_score": 95,
                "brand_dna_compliance": 24,
                "legal_compliance": 25,
                "content_quality": 18,
                "target_fit": 14,
                "overpromise_check": 9,
                "hallucination_check": 5,
                "feedback": "OK",
                "issues": [],
                "verdict": "APPROVED"
            }"""
            mock_researcher.return_value = '{"trends": [], "insights": "No trends"}'
            mock_analyst.return_value = '{"kpis": {}, "recommendations": []}'

            orchestrator = Orchestrator(
                api_key="test-key",
                brand_dna=brand_dna,
            )

            orchestrator.morning_brief({"current_date": "2026-05-23"})

            result1 = orchestrator.write_and_review(
                content_type="note_article",
                context={"topic": "Topic 1"},
            )
            assert result1["status"] == "approved"

            result2 = orchestrator.write_and_review(
                content_type="x_post",
                context={"topic": "Topic 2"},
            )
            assert result2["status"] == "approved"

            for i, result in enumerate([result1, result2]):
                evaluation = result.get("evaluation")
                score = 95
                if evaluation:
                    score = (
                        evaluation.get("total_score", 95)
                        if isinstance(evaluation, dict)
                        else getattr(evaluation, "total_score", 95)
                    )
                record = ContentRecord(
                    content_id=generate_content_id(),
                    content_type=result.get("draft_output", {}).get("content_type", "note_article"),
                    title=f"Content {i + 1}",
                    content=result.get("content", ""),
                    platform="note" if i == 0 else "x",
                    created_at=datetime.now().isoformat(),
                    guardian_score=score,
                )
                brain.save_content(customer_id, record)

            records = brain.list_content(customer_id)
            assert len(records) == 2

            analyst_result = orchestrator.delegate(
                "analyst",
                {
                    "task_type": "weekly_summary",
                    "context": {"period": "2026-05-17 to 2026-05-23"},
                },
            )
            assert analyst_result.get("success") is True or "output" in analyst_result


class TestSchedulerIntegration:
    """Test scheduler with orchestrator."""

    def test_scheduler_triggers_morning_brief(self, brand_dna: dict) -> None:
        """Test scheduler triggering morning brief at 7:00."""
        with patch.object(LeadStrategist, "call_llm") as mock_llm:
            mock_llm.return_value = '{"priorities": [], "insights": "Morning"}'

            orchestrator = Orchestrator(
                api_key="test-key",
                brand_dna=brand_dna,
            )

            scheduler = build_default_scheduler(orchestrator)

            tasks = scheduler.list_tasks()
            morning_task = next((t for t in tasks if t["name"] == "morning_brief"), None)

            assert morning_task is not None
            assert morning_task["schedule"] == "07:00"

            test_time = datetime(2026, 5, 23, 7, 30)
            due_tasks = scheduler.get_due_tasks(test_time)

            morning_due = [t for t in due_tasks if t.name == "morning_brief"]
            assert len(morning_due) == 1


class TestOnboardingToProduction:
    """Test customer journey from onboarding to production."""

    def test_new_customer_workflow(self, tmp_path: Path) -> None:
        """Test complete new customer onboarding and first content."""
        brain = BrainLayer(brain_root=tmp_path / "brain")
        customer_id = "new_customer_001"

        with patch("src.onboarding.Anthropic") as mock_anthropic:
            mock_client = mock_anthropic.return_value
            mock_client.messages.create.return_value.content = [
                MagicMock(
                    text="""```yaml
identity:
  name: NewCustomer
  business: コーチング
  primary_target_audience: 経営者
voice:
  tone: プロフェッショナル
  preferred_phrases:
    - 率直に
  avoid_phrases:
    - 絶対
content_strategy:
  pillar_topics:
    - リーダーシップ
  primary_platforms:
    - note
forbidden:
  topics: []
  expressions: []
  practices: []
reference: {}
```"""
                )
            ]

            onboarding = OnboardingFlow(api_key="test-key", brain=brain)
            onboarding.start_session(customer_id)

            for i in range(30):
                onboarding.submit_answer(customer_id, f"Answer {i + 1}")

            brand_dna = onboarding.generate_brand_dna(customer_id)

            assert brand_dna is not None
            assert brand_dna.identity["name"] == "NewCustomer"

        loaded_dna = brain.load_brand_dna_dict(customer_id)
        assert loaded_dna["identity"]["name"] == "NewCustomer"

        with (
            patch.object(Drafter, "call_llm") as mock_drafter,
            patch.object(Guardian, "call_llm") as mock_guardian,
        ):
            mock_drafter.return_value = "First content for NewCustomer"
            mock_guardian.return_value = """{
                "total_score": 95,
                "brand_dna_compliance": 24,
                "legal_compliance": 25,
                "content_quality": 18,
                "target_fit": 14,
                "overpromise_check": 9,
                "hallucination_check": 5,
                "feedback": "OK",
                "issues": [],
                "verdict": "APPROVED"
            }"""

            orchestrator = Orchestrator(
                api_key="test-key",
                brand_dna=loaded_dna,
            )

            result = orchestrator.write_and_review(
                content_type="note_article",
                context={"topic": "リーダーシップ"},
            )

            assert result["status"] == "approved"


class TestErrorRecovery:
    """Test error handling and recovery."""

    def test_guardian_rejection_recovery(self, brand_dna: dict) -> None:
        """Test recovery when Guardian rejects content."""
        call_count = {"drafter": 0, "guardian": 0}

        def drafter_response(*args, **kwargs):
            call_count["drafter"] += 1
            if call_count["drafter"] <= 2:
                return "Bad content with 絶対 and 100%"
            return "Good content without forbidden words"

        def guardian_response(*args, **kwargs):
            call_count["guardian"] += 1
            if call_count["guardian"] <= 2:
                return """{
                    "total_score": 70,
                    "brand_dna_compliance": 15,
                    "legal_compliance": 20,
                    "content_quality": 15,
                    "target_fit": 10,
                    "overpromise_check": 5,
                    "hallucination_check": 5,
                    "feedback": "過剰約束表現を削除してください",
                    "issues": ["過剰約束"],
                    "verdict": "REJECTED"
                }"""
            return """{
                "total_score": 95,
                "brand_dna_compliance": 24,
                "legal_compliance": 25,
                "content_quality": 18,
                "target_fit": 14,
                "overpromise_check": 9,
                "hallucination_check": 5,
                "feedback": "改善されました",
                "issues": [],
                "verdict": "APPROVED"
            }"""

        with (
            patch("src.agents.drafter.Drafter.call_llm", side_effect=drafter_response),
            patch("src.agents.guardian.Guardian.call_llm", side_effect=guardian_response),
        ):
            orchestrator = Orchestrator(
                api_key="test-key",
                brand_dna=brand_dna,
            )

            result = orchestrator.write_and_review(
                content_type="note_article",
                context={"topic": "Test"},
            )

            assert result["status"] == "approved"
            assert result["retry_count"] >= 2

    def test_escalation_on_max_retries(self, brand_dna: dict) -> None:
        """Test escalation when max retries exceeded."""
        with (
            patch.object(Drafter, "call_llm") as mock_drafter,
            patch.object(Guardian, "call_llm") as mock_guardian,
        ):
            mock_drafter.return_value = "Always bad content"
            mock_guardian.return_value = """{
                "total_score": 50,
                "brand_dna_compliance": 10,
                "legal_compliance": 10,
                "content_quality": 10,
                "target_fit": 10,
                "overpromise_check": 5,
                "hallucination_check": 5,
                "feedback": "重大な問題があります",
                "issues": ["多数の問題"],
                "verdict": "REJECTED"
            }"""

            orchestrator = Orchestrator(
                api_key="test-key",
                brand_dna=brand_dna,
            )

            result = orchestrator.write_and_review(
                content_type="note_article",
                context={"topic": "Test"},
                max_retries=3,
            )

            assert result["status"] == "escalated"
            assert (
                result["retry_count"] == 4
            )  # 4 iterations: 0, 1, 2, 3 then exits with retry_count=4


class TestMultiPlatformWorkflow:
    """Test multi-platform content generation."""

    def test_generate_for_multiple_platforms(self, brand_dna: dict) -> None:
        """Test generating content for note and X simultaneously."""

        def drafter_response(*args, **kwargs):
            messages = kwargs.get("messages", [])
            prompt = messages[0]["content"] if messages else ""
            if "X 投稿" in prompt:
                return '[{"text": "Test X post", "hashtags": []}]'
            return '{"title": "Test", "content": "Platform-specific content"}'

        with (
            patch.object(Drafter, "call_llm", side_effect=drafter_response),
            patch.object(Guardian, "call_llm") as mock_guardian,
        ):
            # removed mock_drafter.return_value - now using side_effect
            mock_guardian.return_value = """{
                "total_score": 96,
                "brand_dna_compliance": 24,
                "legal_compliance": 25,
                "content_quality": 19,
                "target_fit": 14,
                "overpromise_check": 9,
                "hallucination_check": 5,
                "feedback": "OK",
                "issues": [],
                "verdict": "APPROVED"
            }"""

            orchestrator = Orchestrator(
                api_key="test-key",
                brand_dna=brand_dna,
            )

            result = orchestrator.full_content_pipeline(
                topic="AI活用",
                target_audience="ひとり社長",
                platforms=["note_article", "x_post"],
            )

            assert "platforms" in result
            assert "note_article" in result["platforms"]
            assert "x_post" in result["platforms"]
            assert result["platforms"]["note_article"]["status"] == "approved"
            assert result["platforms"]["x_post"]["status"] == "approved"
