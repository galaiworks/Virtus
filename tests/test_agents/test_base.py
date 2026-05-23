"""Tests for base agent."""

import pytest

from src.agents.base import AgentResult, BaseAgent


class ConcreteAgent(BaseAgent):
    """Concrete implementation for testing."""

    name = "test_agent"

    def execute(self, task):
        return AgentResult(success=True, content="test")


class TestAgentResult:
    """Tests for AgentResult."""

    def test_success_result(self):
        result = AgentResult(success=True, content="test content")
        assert result.success is True
        assert result.content == "test content"
        assert result.error is None

    def test_failure_result(self):
        result = AgentResult(success=False, content=None, error="test error")
        assert result.success is False
        assert result.content is None
        assert result.error == "test error"

    def test_with_metadata(self):
        result = AgentResult(
            success=True,
            content="test",
            metadata={"key": "value"},
        )
        assert result.metadata == {"key": "value"}


class TestBaseAgent:
    """Tests for BaseAgent."""

    @pytest.fixture
    def brand_dna(self):
        return {
            "identity": {
                "name": "Test Brand",
                "business": "Testing",
            },
            "voice": {
                "tone": "professional",
            },
            "forbidden": ["spam", "scam"],
        }

    def test_format_brand_dna(self, brand_dna):
        agent = ConcreteAgent(
            api_key="test",
            model="test-model",
            brand_dna=brand_dna,
        )
        formatted = agent.format_brand_dna()
        assert "Identity" in formatted
        assert "Test Brand" in formatted
        assert "Forbidden" in formatted

    def test_format_empty_brand_dna(self):
        agent = ConcreteAgent(
            api_key="test",
            model="test-model",
            brand_dna={},
        )
        formatted = agent.format_brand_dna()
        assert "No brand DNA configured" in formatted

    def test_get_system_prompt(self, brand_dna):
        agent = ConcreteAgent(
            api_key="test",
            model="test-model",
            brand_dna=brand_dna,
        )
        prompt = agent.get_system_prompt()
        assert "test_agent" in prompt
        assert "Test Brand" in prompt
