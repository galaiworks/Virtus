"""Integration tests for Virtus agent coordination."""

from unittest.mock import patch

import pytest

from src.agents.drafter import Drafter
from src.agents.guardian import Guardian
from src.brain import BrainLayer, BrandDNA, ContentRecord, generate_content_id
from src.orchestrator import Orchestrator


@pytest.fixture
def sample_brand_dna() -> dict:
    """Sample brand DNA for testing."""
    return {
        "identity": {
            "name": "TestBrand",
            "business": "AIコンサルティング",
            "primary_target_audience": "ひとり社長",
        },
        "voice": {
            "tone": "プロフェッショナル × 親近感",
            "preferred_phrases": ["率直に言うと", "本質は"],
            "avoid_phrases": ["絶対", "必ず"],
        },
        "forbidden": {
            "expressions": ["100%", "魔法のような"],
        },
    }


class TestDrafterGuardianLoop:
    """Test Drafter -> Guardian 95-point loop integration."""

    def test_write_and_review_success(self, sample_brand_dna: dict) -> None:
        """Test successful write and review workflow."""
        with (
            patch.object(Drafter, "call_llm") as mock_drafter_llm,
            patch.object(Guardian, "call_llm") as mock_guardian_llm,
        ):
            mock_drafter_llm.return_value = """
            # テスト記事

            これは高品質なテスト記事です。
            率直に言うと、AIの活用は重要です。
            """

            mock_guardian_llm.return_value = """
            {
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
            }
            """

            orchestrator = Orchestrator(
                api_key="test-key",
                brand_dna=sample_brand_dna,
            )

            result = orchestrator.write_and_review(
                content_type="note_article",
                context={"topic": "AI活用術", "target_audience": "ひとり社長"},
            )

            assert result["status"] == "approved"
            assert result["content"] is not None

    def test_write_and_review_needs_revision(self, sample_brand_dna: dict) -> None:
        """Test workflow when Guardian rejects and Drafter revises."""
        call_count = {"drafter": 0, "guardian": 0}

        def drafter_response(*args, **kwargs):
            call_count["drafter"] += 1
            if call_count["drafter"] == 1:
                return "初回ドラフト: 絶対に成功します！"
            return "改訂版: 高い確率で成功が期待できます。"

        def guardian_response(*args, **kwargs):
            call_count["guardian"] += 1
            if call_count["guardian"] == 1:
                return """
                {
                    "total_score": 78,
                    "brand_dna_compliance": 15,
                    "legal_compliance": 20,
                    "content_quality": 18,
                    "target_fit": 12,
                    "overpromise_check": 5,
                    "hallucination_check": 5,
                    "feedback": "過剰約束表現「絶対」を修正してください。",
                    "issues": ["過剰約束: 絶対"],
                    "verdict": "REJECTED"
                }
                """
            return """
            {
                "total_score": 95,
                "brand_dna_compliance": 24,
                "legal_compliance": 25,
                "content_quality": 18,
                "target_fit": 14,
                "overpromise_check": 9,
                "hallucination_check": 5,
                "feedback": "改善されました。",
                "issues": [],
                "verdict": "APPROVED"
            }
            """

        with (
            patch.object(Drafter, "call_llm", side_effect=drafter_response),
            patch.object(Guardian, "call_llm", side_effect=guardian_response),
        ):
            orchestrator = Orchestrator(
                api_key="test-key",
                brand_dna=sample_brand_dna,
            )

            result = orchestrator.write_and_review(
                content_type="note_article",
                context={"topic": "成功術"},
            )

            assert result["status"] == "approved"
            assert result["retry_count"] >= 1


class TestOrchestratorDelegation:
    """Test Orchestrator agent delegation."""

    def test_delegate_to_researcher(self, sample_brand_dna: dict) -> None:
        """Test delegating task to Researcher."""
        with patch("src.agents.researcher.Researcher.call_llm") as mock_llm:
            mock_llm.return_value = """
            {
                "trends": [
                    {"topic": "AI自動化", "score": 85, "source": "industry_report"}
                ],
                "insights": "AI自動化トレンドが上昇中"
            }
            """

            orchestrator = Orchestrator(
                api_key="test-key",
                brand_dna=sample_brand_dna,
            )

            result = orchestrator.delegate(
                "researcher",
                {
                    "task_type": "trend_research",
                    "context": {"industry": "AI"},
                },
            )

            assert result["success"] is True
            assert "output" in result

    def test_delegate_to_unknown_agent(self, sample_brand_dna: dict) -> None:
        """Test delegating to non-existent agent."""
        orchestrator = Orchestrator(
            api_key="test-key",
            brand_dna=sample_brand_dna,
        )

        result = orchestrator.delegate(
            "nonexistent_agent",
            {"task_type": "test"},
        )

        assert "error" in result


class TestConnectorEscalation:
    """Test Connector escalation detection integration."""

    def test_handle_normal_message(self, sample_brand_dna: dict) -> None:
        """Test handling normal incoming message."""
        with (
            patch("src.agents.connector.Connector.call_llm") as mock_connector,
            patch("src.agents.guardian.Guardian.call_llm") as mock_guardian,
        ):
            mock_connector.return_value = """
            {
                "escalation_required": false,
                "escalation_level": 0,
                "reply_draft": {
                    "message": "お問い合わせありがとうございます。詳細をお伺いできますか？",
                    "tone": "professional",
                    "urgency": "normal"
                }
            }
            """

            mock_guardian.return_value = """
            {
                "total_score": 96,
                "brand_dna_compliance": 24,
                "legal_compliance": 25,
                "content_quality": 19,
                "target_fit": 14,
                "overpromise_check": 9,
                "hallucination_check": 5,
                "feedback": "適切な返信です。",
                "issues": [],
                "verdict": "APPROVED"
            }
            """

            orchestrator = Orchestrator(
                api_key="test-key",
                brand_dna=sample_brand_dna,
            )

            result = orchestrator.handle_incoming_message(
                {
                    "sender": "prospect@example.com",
                    "platform": "email",
                    "message": "サービスについて教えてください",
                }
            )

            assert result["status"] == "ready_for_approval"
            assert "reply" in result

    def test_handle_escalation_message(self, sample_brand_dna: dict) -> None:
        """Test handling message that requires escalation."""
        with patch("src.agents.connector.Connector.call_llm") as mock_connector:
            mock_connector.return_value = """
            {
                "escalation_required": true,
                "escalation_level": 3,
                "escalation_reason": "クレーム対応が必要",
                "reply_draft": null
            }
            """

            orchestrator = Orchestrator(
                api_key="test-key",
                brand_dna=sample_brand_dna,
            )

            result = orchestrator.handle_incoming_message(
                {
                    "sender": "customer@example.com",
                    "platform": "email",
                    "message": "返金してください。クレームです。",
                }
            )

            assert result["status"] == "escalated"


class TestBrainIntegration:
    """Test Brain layer integration with agents."""

    def test_save_and_retrieve_content_workflow(self, tmp_path, sample_brand_dna: dict) -> None:
        """Test saving content through workflow and retrieving from Brain."""
        brain = BrainLayer(brain_root=tmp_path / "brain")
        customer_id = "test_customer"

        brand_dna = BrandDNA.from_dict(sample_brand_dna)
        brain.save_brand_dna(customer_id, brand_dna)

        loaded_dna = brain.load_brand_dna_dict(customer_id)
        assert loaded_dna["identity"]["name"] == "TestBrand"

        content_record = ContentRecord(
            content_id=generate_content_id(),
            content_type="note_article",
            title="AI活用術",
            content="これは高品質な記事です。",
            platform="note",
            created_at="2026-05-23T10:00:00",
            guardian_score=96,
        )
        brain.save_content(customer_id, content_record)

        records = brain.list_content(customer_id)
        assert len(records) == 1
        assert records[0].guardian_score == 96

    def test_audit_log_workflow(self, tmp_path, sample_brand_dna: dict) -> None:
        """Test audit logging during workflow."""
        brain = BrainLayer(brain_root=tmp_path / "brain")
        customer_id = "test_customer"

        brain.append_log(
            customer_id,
            "evaluations",
            {
                "content_id": "content_001",
                "agent": "Guardian",
                "score": 96,
                "verdict": "approved",
            },
        )

        brain.append_log(
            customer_id,
            "evaluations",
            {
                "content_id": "content_002",
                "agent": "Guardian",
                "score": 82,
                "verdict": "rejected",
            },
        )

        logs = brain.read_logs(customer_id, "evaluations")
        assert len(logs) == 2
        assert logs[0]["score"] == 82  # Most recent first


class TestFullContentPipeline:
    """Test full multi-platform content pipeline."""

    def test_multi_platform_generation(self, sample_brand_dna: dict) -> None:
        """Test generating content for multiple platforms."""
        with (
            patch.object(Drafter, "call_llm") as mock_drafter,
            patch.object(Guardian, "call_llm") as mock_guardian,
        ):
            mock_drafter.return_value = "高品質なコンテンツです。"

            mock_guardian.return_value = """
            {
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
            }
            """

            orchestrator = Orchestrator(
                api_key="test-key",
                brand_dna=sample_brand_dna,
            )

            result = orchestrator.full_content_pipeline(
                topic="AI活用",
                target_audience="ひとり社長",
                platforms=["note_article", "x_post"],
            )

            assert "platforms" in result
            assert "note_article" in result["platforms"]
            assert "x_post" in result["platforms"]
