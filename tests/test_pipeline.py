"""パイプライン定義の不変条件(要件定義 §4)。"""

from __future__ import annotations

from src.officina.models import GateType, HumanRole, Stage
from src.officina.pipeline import PIPELINE, get_stage, human_gates, validate_pipeline


def test_pipeline_covers_all_stages_in_order():
    validate_pipeline()  # 例外を投げなければ合格
    assert [d.stage for d in PIPELINE] == list(Stage)
    assert len(PIPELINE) == 12


def test_exactly_two_mandatory_human_gates():
    gates = human_gates()
    assert [g.stage for g in gates] == [Stage.CONTRACT, Stage.DELIVERY_APPROVAL]
    assert all(g.human == HumanRole.MANDATORY for g in gates)


def test_human_gates_are_human_type():
    assert get_stage(Stage.CONTRACT).gate_type == GateType.HUMAN
    assert get_stage(Stage.DELIVERY_APPROVAL).gate_type == GateType.HUMAN


def test_outreach_gate_is_deterministic():
    # deliverability は前提。LLM ではなく決定論ゲートで守る。
    assert get_stage(Stage.OUTREACH).gate_type == GateType.DETERMINISTIC


def test_every_non_human_stage_has_a_pass_gate():
    # 設計原則 #2:基準が作れない工程は自律化しない。
    for d in PIPELINE:
        if d.owner == "human":
            continue
        if d.stage == Stage.CLOSING:
            continue  # クロージング補助は自動ゲートなし(意図的・人間判断)
        assert d.gate_type in (GateType.DETERMINISTIC, GateType.GUARDIAN)
