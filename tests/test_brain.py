"""Tests for Brain manager."""

import json
import tempfile
from pathlib import Path

import pytest

from src.brain.manager import BrainManager


class TestBrainManager:
    """Tests for BrainManager."""

    @pytest.fixture
    def brain_manager(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield BrainManager(Path(tmpdir), "test_customer")

    def test_init_creates_directories(self, brain_manager):
        expected_dirs = [
            brain_manager.brain_path / "customers" / "test_customer",
            brain_manager.brain_path / "content-history" / "test_customer",
            brain_manager.brain_path / "leads" / "test_customer",
            brain_manager.brain_path / "deals" / "test_customer",
            brain_manager.brain_path / "win-patterns" / "test_customer",
        ]
        for directory in expected_dirs:
            assert directory.exists()

    def test_save_and_get_content(self, brain_manager):
        content_id = brain_manager.save_content(
            content_type="note_article",
            content="Test article content",
            metadata={"topic": "AI"},
        )

        assert content_id.startswith("note_article_")

        retrieved = brain_manager.get_content(content_id)
        assert retrieved is not None
        assert retrieved["content"] == "Test article content"
        assert retrieved["metadata"]["topic"] == "AI"

    def test_save_and_get_lead(self, brain_manager):
        lead = {
            "company_name": "Test Corp",
            "decision_maker": "John Doe",
            "score": {"total": 85},
        }
        lead_id = brain_manager.save_lead(lead)

        leads = brain_manager.get_leads()
        assert len(leads) == 1
        assert leads[0]["company_name"] == "Test Corp"
        assert leads[0]["id"] == lead_id

    def test_save_and_get_deal(self, brain_manager):
        deal = {
            "company_name": "Client Corp",
            "value": 500000,
            "stage": "proposal",
        }
        deal_id = brain_manager.save_deal(deal)

        pipeline = brain_manager.get_pipeline()
        assert len(pipeline) == 1
        assert pipeline[0]["company_name"] == "Client Corp"
        assert pipeline[0]["id"] == deal_id

    def test_update_win_patterns(self, brain_manager):
        brain_manager.update_win_patterns({
            "pattern_name": "結論先出し",
            "description": "結論を最初に述べると反応が良い",
        })

        patterns = brain_manager.get_win_patterns()
        assert len(patterns["patterns"]) == 1
        assert patterns["patterns"][0]["pattern_name"] == "結論先出し"

    def test_get_today_performance(self, brain_manager):
        performance = brain_manager.get_today_performance()
        assert "date" in performance
        assert "content_published" in performance
        assert "leads_generated" in performance
