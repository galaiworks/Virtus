"""Guardian の 95 点ループテスト."""

from __future__ import annotations

import json

import pytest

from src.agents.guardian import THRESHOLD, Guardian
from tests.conftest import set_client_response


def _llm_verdict_json(
    *,
    brand_dna: int = 25,
    legal: int = 25,
    quality: int = 19,
    target_fit: int = 15,
    overpromise: int = 10,
    hallucination: int = 5,
    self_reflection_passed: bool = True,
    feedback: str = "",
    verdict: str | None = None,
) -> str:
    """LLM の評価応答 JSON を組み立てるヘルパー."""
    total = brand_dna + legal + quality + target_fit + overpromise + hallucination
    chosen_verdict = verdict or ("APPROVED" if total >= THRESHOLD else "REJECTED")
    return json.dumps(
        {
            "brand_dna": {"score": brand_dna, "issues": []},
            "legal": {"score": legal, "issues": []},
            "quality": {"score": quality, "issues": []},
            "target_fit": {"score": target_fit, "issues": []},
            "overpromise": {"score": overpromise, "issues": []},
            "hallucination": {"score": hallucination, "issues": []},
            "total": total,
            "verdict": chosen_verdict,
            "self_reflection_passed": self_reflection_passed,
            "feedback": feedback,
        },
        ensure_ascii=False,
    )


def test_evaluate_approves_high_score(galaiworks_brand_dna, fake_anthropic_client):
    """99 点 + 自己反省通過なら APPROVED."""
    set_client_response(fake_anthropic_client, _llm_verdict_json())
    guardian = Guardian(
        api_key="test",
        model="claude-opus-4-7",
        brand_dna=galaiworks_brand_dna,
        client=fake_anthropic_client,
    )

    verdict = guardian.evaluate("健全なコンテンツです。")
    assert verdict.total_score == 99
    assert verdict.approved
    assert verdict.verdict == "APPROVED"


def test_rule_based_short_circuit_on_excessive_claim(
    galaiworks_brand_dna, fake_anthropic_client
):
    """「100%」を含むコンテンツは LLM 呼び出し前に CRITICAL_VIOLATION."""
    guardian = Guardian(
        api_key="test",
        model="claude-opus-4-7",
        brand_dna=galaiworks_brand_dna,
        client=fake_anthropic_client,
    )

    verdict = guardian.evaluate("このサービスで 100% 稼げます。")
    assert verdict.verdict == "CRITICAL_VIOLATION"
    assert verdict.force_reject
    assert not verdict.approved
    # LLM は呼ばれない (ショートサーキット)
    fake_anthropic_client.messages.create.assert_not_called()


def test_self_reflection_failure_blocks_approval(
    galaiworks_brand_dna, fake_anthropic_client
):
    """スコアが 95 点超でも自己反省で false なら approved=False."""
    set_client_response(
        fake_anthropic_client,
        _llm_verdict_json(self_reflection_passed=False),
    )
    guardian = Guardian(
        api_key="test",
        model="claude-opus-4-7",
        brand_dna=galaiworks_brand_dna,
        client=fake_anthropic_client,
    )
    verdict = guardian.evaluate("一見良いが微妙なコンテンツ")
    assert verdict.total_score == 99
    assert not verdict.approved


def test_below_threshold_is_rejected(galaiworks_brand_dna, fake_anthropic_client):
    """95 点未満は approved=False."""
    set_client_response(
        fake_anthropic_client,
        _llm_verdict_json(quality=10, target_fit=10, feedback="具体例不足"),
    )
    guardian = Guardian(
        api_key="test",
        model="claude-opus-4-7",
        brand_dna=galaiworks_brand_dna,
        client=fake_anthropic_client,
    )
    verdict = guardian.evaluate("内容が薄いコンテンツ")
    assert verdict.total_score == 85
    assert not verdict.approved
    assert "具体例不足" in verdict.feedback


def test_malformed_json_raises(galaiworks_brand_dna, fake_anthropic_client):
    """LLM 出力に JSON が含まれない場合 ValueError."""
    set_client_response(fake_anthropic_client, "JSON ではないテキスト")
    guardian = Guardian(
        api_key="test",
        model="claude-opus-4-7",
        brand_dna=galaiworks_brand_dna,
        client=fake_anthropic_client,
    )
    with pytest.raises(ValueError, match="JSON が見つかりません"):
        guardian.evaluate("...")
