"""フェーズ計画(要件定義 §11)。"""

from __future__ import annotations

from src.officina.models import Stage
from src.officina.phases import (
    ASYMPTOTE_HUMAN_GATES,
    PHASES,
    Phase,
    get_phase_plan,
)


def test_asymptote_human_gates_fixed_in_every_phase():
    for plan in PHASES.values():
        for gate in ASYMPTOTE_HUMAN_GATES:
            assert not plan.is_autonomous(gate)
    assert ASYMPTOTE_HUMAN_GATES == (Stage.CONTRACT, Stage.DELIVERY_APPROVAL)


def test_autonomy_ratio_monotonically_increases():
    r1 = get_phase_plan(Phase.PHASE_1).autonomy_ratio()
    r2 = get_phase_plan(Phase.PHASE_2).autonomy_ratio()
    r3 = get_phase_plan(Phase.PHASE_3).autonomy_ratio()
    assert r1 < r2 < r3


def test_phase1_keeps_closing_and_icp_human():
    plan = get_phase_plan(Phase.PHASE_1)
    assert not plan.is_autonomous(Stage.CLOSING)
    assert not plan.is_autonomous(Stage.ICP_RESEARCH)
    assert plan.is_autonomous(Stage.OUTREACH)


def test_phase3_automates_closing_but_not_contract():
    plan = get_phase_plan(Phase.PHASE_3)
    assert plan.is_autonomous(Stage.CLOSING)
    assert not plan.is_autonomous(Stage.CONTRACT)
