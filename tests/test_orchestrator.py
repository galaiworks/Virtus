"""Orchestrator の 95 点ループ統合テスト."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from src.agents.drafter import Drafter
from src.agents.guardian import Guardian
from src.agents.lead_strategist import LeadStrategist
from src.orchestrator import Orchestrator


def _make_client(responses: list[str]) -> MagicMock:
    """順番に応答を返すモッククライアントを構築."""
    client = MagicMock()

    def side_effect(*args, **kwargs):
        text = responses.pop(0)
        msg = MagicMock()
        msg.content = [MagicMock(text=text)]
        return msg

    client.messages.create.side_effect = side_effect
    return client


def test_orchestrator_approves_on_first_try(galaiworks_brand_dna):
    """1 回目で 95 点超なら 1 回で承認."""
    high_score = json.dumps(
        {
            "brand_dna": {"score": 25, "issues": []},
            "legal": {"score": 25, "issues": []},
            "quality": {"score": 19, "issues": []},
            "target_fit": {"score": 15, "issues": []},
            "overpromise": {"score": 10, "issues": []},
            "hallucination": {"score": 5, "issues": []},
            "total": 99,
            "verdict": "APPROVED",
            "self_reflection_passed": True,
            "feedback": "",
        }
    )

    drafter_client = _make_client(["健全な初稿"])
    guardian_client = _make_client([high_score])

    drafter = Drafter(
        api_key="x",
        model="claude-sonnet-4-6",
        brand_dna=galaiworks_brand_dna,
        client=drafter_client,
    )
    guardian = Guardian(
        api_key="x",
        model="claude-opus-4-7",
        brand_dna=galaiworks_brand_dna,
        client=guardian_client,
    )
    lead = LeadStrategist(
        api_key="x",
        model="claude-opus-4-7",
        brand_dna=galaiworks_brand_dna,
        client=_make_client([]),
    )

    orch = Orchestrator(lead, drafter, guardian)
    result = orch.run_write_with_guardian_loop("write", "短いブログ記事")

    assert result.approved
    assert result.retry_count == 0
    assert result.final_content == "健全な初稿"
    assert len(result.verdicts) == 1


def test_orchestrator_escalates_after_max_retries(galaiworks_brand_dna):
    """3 回再試行しても 95 点未到達 → escalate."""
    low_score = json.dumps(
        {
            "brand_dna": {"score": 15, "issues": ["voice 不一致"]},
            "legal": {"score": 20, "issues": []},
            "quality": {"score": 10, "issues": []},
            "target_fit": {"score": 10, "issues": []},
            "overpromise": {"score": 10, "issues": []},
            "hallucination": {"score": 5, "issues": []},
            "total": 70,
            "verdict": "REJECTED",
            "self_reflection_passed": False,
            "feedback": "voice をブランド DNA に合わせ直す",
        }
    )

    drafter_client = _make_client(
        ["初稿", "改稿 1", "改稿 2", "改稿 3"]
    )
    guardian_client = _make_client([low_score] * 4)

    drafter = Drafter(
        api_key="x",
        model="claude-sonnet-4-6",
        brand_dna=galaiworks_brand_dna,
        client=drafter_client,
    )
    guardian = Guardian(
        api_key="x",
        model="claude-opus-4-7",
        brand_dna=galaiworks_brand_dna,
        client=guardian_client,
    )
    lead = LeadStrategist(
        api_key="x",
        model="claude-opus-4-7",
        brand_dna=galaiworks_brand_dna,
        client=_make_client([]),
    )

    orch = Orchestrator(lead, drafter, guardian)
    result = orch.run_write_with_guardian_loop("write", "難しい題材")

    assert not result.approved
    assert result.retry_count == 3
    assert result.escalation_reason == "max_retries_exceeded"
    assert len(result.verdicts) == 4  # 初回 + 3 回再試行


def test_orchestrator_short_circuits_on_critical_violation(galaiworks_brand_dna):
    """Drafter 出力に過剰約束 → 即時 escalation."""
    drafter_client = _make_client(["このサービスで 100% 稼げます"])
    guardian_client = _make_client([])  # 呼ばれない想定

    drafter = Drafter(
        api_key="x",
        model="claude-sonnet-4-6",
        brand_dna=galaiworks_brand_dna,
        client=drafter_client,
    )
    guardian = Guardian(
        api_key="x",
        model="claude-opus-4-7",
        brand_dna=galaiworks_brand_dna,
        client=guardian_client,
    )
    lead = LeadStrategist(
        api_key="x",
        model="claude-opus-4-7",
        brand_dna=galaiworks_brand_dna,
        client=_make_client([]),
    )

    orch = Orchestrator(lead, drafter, guardian)
    result = orch.run_write_with_guardian_loop("write", "煽り気味の題材")

    assert not result.approved
    assert result.escalation_reason == "critical_violation"
    guardian_client.messages.create.assert_not_called()
