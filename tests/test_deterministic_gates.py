"""決定論ゲート(要件定義 §6.1)。LLM に判断させない if/then。"""

from __future__ import annotations

from src.officina.governance.deterministic_gates import DeterministicGates
from src.officina.models import Verdict


def test_price_floor_blocks_below_floor(config):
    gates = DeterministicGates(config)  # floor=1000
    r = gates.price_gate(500.0)
    assert r.verdict == Verdict.ESCALATE
    assert any("下限" in x for x in r.reasons)


def test_unapproved_discount_escalates(config):
    gates = DeterministicGates(config)
    r = gates.price_gate(5000.0, list_price_usd=10000.0, discount_approved=False)
    assert r.verdict == Verdict.ESCALATE


def test_approved_discount_passes(config):
    gates = DeterministicGates(config)
    r = gates.price_gate(5000.0, list_price_usd=10000.0, discount_approved=True)
    assert r.verdict == Verdict.PASS


def test_contract_requires_human_signer(config):
    gates = DeterministicGates(config)
    assert gates.contract_trigger(True, signer_is_human=False).verdict == Verdict.PENDING_HUMAN
    assert gates.contract_trigger(True, signer_is_human=True).verdict == Verdict.PASS


def test_prod_deploy_needs_tests_guardian_and_human(config):
    gates = DeterministicGates(config)
    assert gates.prod_deploy_gate(True, True, True).verdict == Verdict.PASS
    assert gates.prod_deploy_gate(True, True, False).verdict == Verdict.FAIL
    assert gates.prod_deploy_gate(False, True, True).verdict == Verdict.FAIL


def test_billing_requires_contract_and_acceptance(config):
    gates = DeterministicGates(config)
    assert gates.billing_trigger(True, True).verdict == Verdict.PASS
    assert gates.billing_trigger(True, False).verdict == Verdict.FAIL
