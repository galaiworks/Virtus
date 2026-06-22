"""§12 確定事項(v0.3)。"""

from __future__ import annotations

from src.officina.decisions import (
    CONFIRMED,
    AcvStrategy,
    DeliverabilityInfra,
    DeliverableScope,
    SignalLayerMode,
)
from src.officina.deliverables import (
    DeliverableType,
    build_acceptance_tests,
    is_in_scope,
)
from src.officina.signals import (
    InHouseSignalSource,
    IntegrationSignalSource,
    get_signal_source,
)


def test_confirmed_follows_winning_path():
    assert CONFIRMED.acv_strategy == AcvStrategy.LOW_VOLUME
    assert CONFIRMED.deliverable_scope == DeliverableScope.AGENT_BUILD_ONLY
    assert CONFIRMED.signal_layer == SignalLayerMode.INTEGRATION
    assert CONFIRMED.incorporate_corporate_scheme is True
    assert CONFIRMED.deliverability_infra == DeliverabilityInfra.IN_HOUSE
    # すべての決定に根拠が紐づく。
    assert len(CONFIRMED.rationale) == 5


def test_only_agent_build_in_scope():
    assert is_in_scope(DeliverableType.AGENT_BUILD)
    # 士業独占業務は自律納品の対象外(§8.4)。
    assert not is_in_scope(DeliverableType.LICENSED_PROFESSION)


def test_acceptance_tests_include_success_criteria():
    tests = build_acceptance_tests({"success_criteria": "月間商談 20 件"})
    assert any("月間商談 20 件" in t for t in tests)
    assert any("Guardian" in t for t in tests)


def test_signal_source_factory_and_verification():
    src = get_signal_source(SignalLayerMode.INTEGRATION, [
        {"company": "A", "email": "a@a.co.jp"},
        {"company": "B", "email": "invalid"},  # 実在性検証で除外
    ])
    assert isinstance(src, IntegrationSignalSource)
    verified = src.fetch_verified({})
    assert len(verified) == 1 and verified[0]["company"] == "A"


def test_in_house_source_selected():
    assert isinstance(get_signal_source(SignalLayerMode.IN_HOUSE), InHouseSignalSource)
