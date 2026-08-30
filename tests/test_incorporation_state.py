"""IncorporationState のテスト(設計レビュー B-7)。"""

from __future__ import annotations

import pytest

from src.officina.incorporation.state import (
    Decision,
    IncorporationState,
    ValueEntry,
)


def test_set_and_pending_decisions() -> None:
    state = IncorporationState(customer_id="c1")
    state.set_decision("D-2", "インボイス登録", "登録しない", rationale="B2C のため")
    state.set_decision("D-7", "役員報酬", "", confirmed=False)

    assert state.decisions["D-2"].confirmed is True
    pending = state.pending_decisions()
    assert [d.key for d in pending] == ["D-7"]


def test_value_recovered_separates_confirmed_and_potential() -> None:
    """見込みを実績に混ぜないこと(北極星指標の信頼性)。"""
    state = IncorporationState(customer_id="c1")
    state.add_value(
        ValueEntry("tax_saving", "登録免許税の軽減", 75_000, status="confirmed")
    )
    state.add_value(ValueEntry("grant", "起業チャレンジ応援事業", 2_000_000))

    assert state.value_recovered("confirmed") == 75_000
    assert state.value_recovered("potential") == 2_000_000
    assert state.value_breakdown("confirmed")["tax_saving"] == 75_000
    assert state.value_breakdown("confirmed")["grant"] == 0


def test_confirm_value_promotes_entry() -> None:
    state = IncorporationState(customer_id="c1")
    state.add_value(ValueEntry("grant", "持続化補助金", 500_000))

    promoted = state.confirm_value("持続化補助金")

    assert promoted is not None
    assert state.value_recovered("confirmed") == 500_000
    assert state.value_recovered("potential") == 0


def test_confirm_value_returns_none_for_unknown_label() -> None:
    state = IncorporationState(customer_id="c1")
    assert state.confirm_value("存在しない") is None


def test_value_entry_rejects_invalid_category_and_status() -> None:
    with pytest.raises(ValueError):
        ValueEntry("unknown", "x", 1)
    with pytest.raises(ValueError):
        ValueEntry("grant", "x", 1, status="maybe")


def test_round_trip_json(tmp_path) -> None:
    state = IncorporationState(customer_id="founding_001", profile={"region": "新潟市"})
    state.set_decision("D-4", "資本金", "1 万円")
    state.add_value(ValueEntry("tax_saving", "消費税免税", 600_000))
    state.watchlist["jizokuka"] = {"name": "持続化補助金", "status": "eligible"}

    path = state.save(tmp_path / "incorporation-state.json")
    restored = IncorporationState.load(path)

    assert restored.customer_id == "founding_001"
    assert restored.profile["region"] == "新潟市"
    assert isinstance(restored.decisions["D-4"], Decision)
    assert restored.decisions["D-4"].value == "1 万円"
    assert restored.value_recovered("potential") == 600_000
    assert restored.watchlist["jizokuka"]["status"] == "eligible"


def test_round_trip_yaml(tmp_path) -> None:
    pytest.importorskip("yaml")
    state = IncorporationState(customer_id="c1")
    state.set_decision("D-3", "会社形態", "株式会社")

    path = state.save(tmp_path / "state.yaml")
    restored = IncorporationState.load(path)

    assert restored.decisions["D-3"].value == "株式会社"
