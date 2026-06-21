"""決定論ゲートの単体テスト。

これらのテスト自体が「決定論ゲートの合格基準＝リグレッションテスト」である。
ゲートのドリフト(LLM 更新や仕様変更でハードロジックが緩む)を防ぐ。
"""

from __future__ import annotations

import pytest

from officina import gates
from officina.gates import GateError


# --------------------------- deliverability_gate --------------------------- #


def test_deliverability_healthy() -> None:
    result = gates.deliverability_gate(
        {"bounce_rate": 0.01, "spam_complaint_rate": 0.0005, "domain_reputation": 90}
    )
    assert result.allowed is True


def test_deliverability_high_bounce_blocks_critical() -> None:
    result = gates.deliverability_gate(
        {"bounce_rate": 0.05, "spam_complaint_rate": 0.0005, "domain_reputation": 90}
    )
    assert result.allowed is False
    assert result.severity == "critical"


def test_deliverability_low_reputation_blocks() -> None:
    result = gates.deliverability_gate(
        {"bounce_rate": 0.01, "spam_complaint_rate": 0.0005, "domain_reputation": 50}
    )
    assert result.allowed is False


def test_deliverability_missing_field_raises() -> None:
    with pytest.raises(GateError):
        gates.deliverability_gate({"bounce_rate": 0.01})


# ----------------------------- send_volume_gate ---------------------------- #


def test_send_volume_within_warmup_cap() -> None:
    result = gates.send_volume_gate({"domain_age_days": 3, "sent_today": 0}, requested=15)
    assert result.allowed is True
    assert result.details["cap"] == 20


def test_send_volume_exceeds_warmup_cap() -> None:
    result = gates.send_volume_gate({"domain_age_days": 3, "sent_today": 10}, requested=15)
    assert result.allowed is False
    assert result.details["remaining"] == 10


def test_send_volume_steady_state_cap() -> None:
    result = gates.send_volume_gate({"domain_age_days": 120, "sent_today": 0}, requested=1000)
    assert result.allowed is True


def test_send_volume_override_takes_min() -> None:
    result = gates.send_volume_gate(
        {"domain_age_days": 120, "sent_today": 0, "daily_cap_override": 100}, requested=150
    )
    assert result.allowed is False
    assert result.details["cap"] == 100


def test_send_volume_negative_requested_raises() -> None:
    with pytest.raises(GateError):
        gates.send_volume_gate({"domain_age_days": 3, "sent_today": 0}, requested=-1)


# ----------------------------- price_floor_gate ---------------------------- #


def test_price_above_floor_passes() -> None:
    assert gates.price_floor_gate({"amount": 300000, "floor": 250000}).allowed is True


def test_price_below_floor_blocks() -> None:
    assert gates.price_floor_gate({"amount": 200000, "floor": 250000}).allowed is False


def test_discount_without_human_approval_blocks() -> None:
    result = gates.price_floor_gate(
        {"amount": 300000, "floor": 250000, "discount_rate": 0.1, "human_approved": False}
    )
    assert result.allowed is False


def test_discount_with_human_approval_passes() -> None:
    result = gates.price_floor_gate(
        {"amount": 300000, "floor": 250000, "discount_rate": 0.1, "human_approved": True}
    )
    assert result.allowed is True


# -------------------------- contract_trigger_gate -------------------------- #


def test_contract_signed_by_human_passes() -> None:
    result = gates.contract_trigger_gate(
        {"signed": True, "signer_is_human": True, "provider": "stripe", "signature_id": "sig_1"}
    )
    assert result.allowed is True


def test_contract_unsigned_blocks_critical() -> None:
    result = gates.contract_trigger_gate(
        {"signed": False, "signer_is_human": True, "provider": "stripe"}
    )
    assert result.allowed is False
    assert result.severity == "critical"


def test_contract_ai_signer_blocks() -> None:
    result = gates.contract_trigger_gate(
        {"signed": True, "signer_is_human": False, "provider": "stripe"}
    )
    assert result.allowed is False


def test_contract_invalid_provider_blocks() -> None:
    result = gates.contract_trigger_gate(
        {"signed": True, "signer_is_human": True, "provider": "sketchy_tool"}
    )
    assert result.allowed is False


# ------------------------------- billing_gate ------------------------------ #


def test_billing_on_signed_contract_passes() -> None:
    assert gates.billing_gate({"contract_signed": True, "amount": 198000}).allowed is True


def test_billing_on_unsigned_contract_blocks() -> None:
    result = gates.billing_gate({"contract_signed": False, "amount": 198000})
    assert result.allowed is False
    assert result.severity == "critical"


def test_billing_double_charge_blocks() -> None:
    result = gates.billing_gate(
        {"contract_signed": True, "amount": 198000, "already_billed": True}
    )
    assert result.allowed is False


# ----------------------------- prod_deploy_gate ---------------------------- #


def test_deploy_all_pass_and_guardian_approved() -> None:
    result = gates.prod_deploy_gate({"total": 42, "passed": 42}, "APPROVED")
    assert result.allowed is True


def test_deploy_failing_tests_blocks() -> None:
    result = gates.prod_deploy_gate({"total": 42, "passed": 40}, "APPROVED")
    assert result.allowed is False


def test_deploy_guardian_not_approved_blocks() -> None:
    result = gates.prod_deploy_gate({"total": 42, "passed": 42}, "REJECTED")
    assert result.allowed is False


def test_deploy_zero_tests_blocks() -> None:
    result = gates.prod_deploy_gate({"total": 0, "passed": 0}, "APPROVED")
    assert result.allowed is False


# -------------------------- permission_scope_gate -------------------------- #


def test_outreach_can_send() -> None:
    assert gates.permission_scope_gate("outreach", "send").allowed is True


def test_outreach_cannot_deploy() -> None:
    result = gates.permission_scope_gate("outreach", "deploy_prod")
    assert result.allowed is False
    assert result.severity == "critical"


def test_builder_cannot_deploy_prod() -> None:
    assert gates.permission_scope_gate("builder", "deploy_prod").allowed is False


def test_unknown_agent_default_deny() -> None:
    result = gates.permission_scope_gate("rogue_agent", "send")
    assert result.allowed is False
    assert result.severity == "critical"


# ------------------------------ GateResult API ----------------------------- #


def test_raise_if_blocked() -> None:
    with pytest.raises(PermissionError):
        gates.permission_scope_gate("outreach", "deploy_prod").raise_if_blocked()
