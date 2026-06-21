"""パイプライン構造の単体テスト。

人間ゲートが契約締結(7)と納品物承認(9)の 2 点のみに固定されていることを
保証する(逆ピラミッドの不変条件)。
"""

from __future__ import annotations

from officina import pipeline
from officina.pipeline import HumanInvolvement


def test_pipeline_is_0_to_11_contiguous() -> None:
    assert [s.number for s in pipeline.PIPELINE] == list(range(12))


def test_only_two_human_gates() -> None:
    assert pipeline.HUMAN_GATES == (7, 9)


def test_contract_and_delivery_are_human_required() -> None:
    assert pipeline.requires_human_gate(7) is True
    assert pipeline.requires_human_gate(9) is True


def test_autonomous_stages_are_not_human_gates() -> None:
    for n in (1, 2, 8, 10):
        assert pipeline.requires_human_gate(n) is False


def test_outreach_stage_declares_deliverability_gates() -> None:
    s = pipeline.stage(2)
    assert "deliverability_gate" in s.deterministic_gates
    assert "send_volume_gate" in s.deterministic_gates


def test_human_gate_stages_have_no_agent() -> None:
    assert pipeline.stage(7).agent is None
    assert pipeline.stage(9).agent is None


def test_closer_is_human_decision() -> None:
    assert pipeline.stage(6).human is HumanInvolvement.DECISION


def test_integrity_assertion_passes() -> None:
    pipeline.assert_pipeline_integrity()
