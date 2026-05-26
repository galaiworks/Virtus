"""Tests for Onboarding Flow."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.brain import BrainLayer
from src.onboarding import (
    HEARING_QUESTIONS,
    HearingResponse,
    HearingSession,
    OnboardingFlow,
    analyze_past_content,
)


@pytest.fixture
def brain(tmp_path: Path) -> BrainLayer:
    """Create BrainLayer instance."""
    return BrainLayer(brain_root=tmp_path / "brain")


@pytest.fixture
def onboarding(brain: BrainLayer) -> OnboardingFlow:
    """Create OnboardingFlow instance."""
    return OnboardingFlow(api_key="test-key", brain=brain)


class TestHearingQuestions:
    """Tests for hearing question structure."""

    def test_question_count(self) -> None:
        """Test that we have 30 questions."""
        assert len(HEARING_QUESTIONS) == 30

    def test_question_categories(self) -> None:
        """Test question categories coverage."""
        categories = {q.category for q in HEARING_QUESTIONS}
        expected = {
            "Identity",
            "Voice",
            "Content Strategy",
            "Target Audience",
            "Forbidden",
            "Goal",
        }
        assert categories == expected

    def test_question_ids_unique(self) -> None:
        """Test that question IDs are unique."""
        ids = [q.id for q in HEARING_QUESTIONS]
        assert len(ids) == len(set(ids))


class TestHearingSession:
    """Tests for HearingSession dataclass."""

    def test_session_initialization(self) -> None:
        """Test session creation."""
        session = HearingSession(customer_id="test_001")

        assert session.customer_id == "test_001"
        assert session.responses == []
        assert session.current_index == 0
        assert session.completed is False


class TestOnboardingFlow:
    """Tests for OnboardingFlow."""

    def test_start_session(self, onboarding: OnboardingFlow) -> None:
        """Test starting a new session."""
        session = onboarding.start_session("customer_001")

        assert session.customer_id == "customer_001"
        assert session.current_index == 0

    def test_get_session(self, onboarding: OnboardingFlow) -> None:
        """Test retrieving session."""
        onboarding.start_session("customer_001")

        session = onboarding.get_session("customer_001")
        assert session is not None
        assert session.customer_id == "customer_001"

        assert onboarding.get_session("nonexistent") is None

    def test_get_current_question(self, onboarding: OnboardingFlow) -> None:
        """Test getting current question."""
        onboarding.start_session("customer_001")

        question = onboarding.get_current_question("customer_001")

        assert question is not None
        assert question.id == "identity_1"
        assert question.category == "Identity"

    def test_submit_answer(self, onboarding: OnboardingFlow) -> None:
        """Test submitting an answer."""
        onboarding.start_session("customer_001")

        result = onboarding.submit_answer("customer_001", "TestBrand株式会社")

        assert result["status"] == "continue"
        assert result["progress"] == "1/30"
        assert result["next_question"]["id"] == "identity_2"

    def test_submit_answer_no_session(self, onboarding: OnboardingFlow) -> None:
        """Test submitting without session."""
        result = onboarding.submit_answer("nonexistent", "answer")

        assert "error" in result

    def test_get_progress(self, onboarding: OnboardingFlow) -> None:
        """Test getting progress."""
        onboarding.start_session("customer_001")
        onboarding.submit_answer("customer_001", "Answer 1")
        onboarding.submit_answer("customer_001", "Answer 2")

        progress = onboarding.get_progress("customer_001")

        assert progress["current"] == 2
        assert progress["total"] == 30
        assert progress["percentage"] == 6

    def test_complete_all_questions(self, onboarding: OnboardingFlow) -> None:
        """Test completing all questions."""
        onboarding.start_session("customer_001")

        for i in range(30):
            result = onboarding.submit_answer("customer_001", f"Answer {i + 1}")

        assert result["status"] == "completed"

        session = onboarding.get_session("customer_001")
        assert session.completed is True

    def test_format_responses(self, onboarding: OnboardingFlow) -> None:
        """Test formatting responses for LLM."""
        responses = [
            HearingResponse(question_id="identity_1", answer="TestBrand"),
            HearingResponse(question_id="voice_1", answer="カジュアル", notes="フレンドリーに"),
        ]

        formatted = onboarding._format_responses(responses)

        assert "TestBrand" in formatted
        assert "カジュアル" in formatted
        assert "フレンドリーに" in formatted

    def test_extract_yaml(self, onboarding: OnboardingFlow) -> None:
        """Test YAML extraction from LLM response."""
        text_with_yaml = """
        Here's the brand DNA:
        ```yaml
        identity:
          name: TestBrand
        ```
        That's all.
        """

        yaml_content = onboarding._extract_yaml(text_with_yaml)

        assert "identity:" in yaml_content
        assert "name: TestBrand" in yaml_content

    def test_extract_yaml_no_markers(self, onboarding: OnboardingFlow) -> None:
        """Test YAML extraction without markers."""
        plain_yaml = "identity:\n  name: TestBrand"

        yaml_content = onboarding._extract_yaml(plain_yaml)

        assert "identity:" in yaml_content


class TestBrandDNAGeneration:
    """Tests for brand DNA generation."""

    def test_generate_brand_dna(self, onboarding: OnboardingFlow, brain: BrainLayer) -> None:
        """Test generating brand DNA from responses."""
        onboarding.start_session("customer_001")

        for i in range(30):
            onboarding.submit_answer("customer_001", f"Answer {i + 1}")

        yaml_response = """
```yaml
identity:
  name: TestBrand
  business: AIコンサルティング
  primary_target_audience: ひとり社長
  unique_value_proposition: AI活用支援

voice:
  tone: プロフェッショナル
  personality:
    - 率直
  preferred_phrases:
    - 率直に言うと
  avoid_phrases:
    - 絶対

content_strategy:
  pillar_topics:
    - AI活用
  primary_platforms:
    - note
  publishing_frequency:
    note: 週2本

forbidden:
  topics:
    - 政治
  expressions:
    - 100%
  practices: []

reference:
  past_winning_content: []
  competitor_examples: []
  inspiration_sources: []
```
"""

        with patch.object(onboarding.client.messages, "create") as mock_create:
            mock_create.return_value.content = [type("Content", (), {"text": yaml_response})()]

            brand_dna = onboarding.generate_brand_dna("customer_001")

            assert brand_dna is not None
            assert brand_dna.identity["name"] == "TestBrand"
            assert "率直" in brand_dna.voice.get("personality", [])

            saved = brain.load_brand_dna("customer_001")
            assert saved is not None
            assert saved.identity["name"] == "TestBrand"

    def test_generate_brand_dna_incomplete_session(self, onboarding: OnboardingFlow) -> None:
        """Test generating DNA from incomplete session."""
        onboarding.start_session("customer_001")
        onboarding.submit_answer("customer_001", "Answer 1")

        brand_dna = onboarding.generate_brand_dna("customer_001")

        assert brand_dna is None


class TestContentAnalysis:
    """Tests for past content analysis."""

    def test_analyze_past_content(self) -> None:
        """Test content analysis."""
        samples = [
            "率直に言うと、AI活用は重要です。",
            "本質を見極めることが大切です。",
        ]

        json_response = """
```json
{
  "tone_analysis": {
    "formality": 0.7,
    "warmth": 0.6,
    "expertise": 0.8
  },
  "common_phrases": ["率直に言うと", "本質を見極める"],
  "structure_patterns": ["結論先出し"],
  "unique_expressions": ["重要です"],
  "avoided_expressions": []
}
```
"""

        with patch("src.onboarding.Anthropic") as mock_anthropic:
            mock_client = mock_anthropic.return_value
            mock_client.messages.create.return_value.content = [
                type("Content", (), {"text": json_response})()
            ]

            result = analyze_past_content("test-key", samples)

            assert "tone_analysis" in result
            assert result["tone_analysis"]["expertise"] == 0.8
            assert "率直に言うと" in result["common_phrases"]
