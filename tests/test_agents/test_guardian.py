"""Tests for Guardian agent."""

import pytest

from src.agents.guardian import Guardian, QualityEvaluation, Violation


class TestViolation:
    """Tests for Violation dataclass."""

    def test_create_violation(self):
        violation = Violation(
            severity="MAJOR",
            category="brand_dna",
            description="Test violation",
            suggestion="Fix it",
        )
        assert violation.severity == "MAJOR"
        assert violation.category == "brand_dna"
        assert violation.description == "Test violation"
        assert violation.suggestion == "Fix it"


class TestQualityEvaluation:
    """Tests for QualityEvaluation dataclass."""

    def test_create_evaluation(self):
        evaluation = QualityEvaluation(
            total_score=95,
            axis_scores={"brand_dna": 25, "legal": 25},
            approved=True,
        )
        assert evaluation.total_score == 95
        assert evaluation.approved is True
        assert len(evaluation.violations) == 0


class TestGuardian:
    """Tests for Guardian agent."""

    @pytest.fixture
    def guardian(self):
        return Guardian(
            api_key="test",
            model="test-model",
            brand_dna={
                "forbidden": ["絶対", "必ず"],
            },
        )

    def test_evaluate_overpromise(self, guardian):
        content = "このサービスで絶対に成功できます！"
        result = guardian.execute({
            "type": "evaluate",
            "content": content,
            "content_type": "general",
        })

        assert result.success is True
        violations = result.content.get("violations", [])
        overpromise_violations = [
            v for v in violations if v.get("category") == "overpromise"
        ]
        assert len(overpromise_violations) > 0

    def test_evaluate_compliance_email(self, guardian):
        content = "新サービスのお知らせです。ぜひご検討ください。"
        result = guardian.execute({
            "type": "compliance_check",
            "content": content,
            "content_type": "email",
        })

        assert result.success is False
        assert result.content.get("critical_violations", 0) > 0

    def test_evaluate_compliance_with_unsubscribe(self, guardian):
        content = """
新サービスのお知らせです。

ぜひご検討ください。

---
配信解除はこちら: https://example.com/unsubscribe
"""
        result = guardian.execute({
            "type": "compliance_check",
            "content": content,
            "content_type": "email",
        })

        assert result.content.get("critical_violations", 0) == 0

    def test_brand_check(self, guardian):
        content = "このサービスは絶対におすすめです。"
        result = guardian.execute({
            "type": "brand_check",
            "content": content,
        })

        assert result.success is False
        violations = result.content.get("violations", [])
        assert len(violations) > 0
