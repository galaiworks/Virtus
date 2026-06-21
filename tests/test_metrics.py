"""KPI と撤退基準(要件定義 §10)。"""

from __future__ import annotations

from src.officina.config import OfficinaConfig
from src.officina.governance.reject_log import RejectLog
from src.officina.metrics import (
    HYBRID_WIN_RATE_BASELINE,
    FunnelCounts,
    KpiTracker,
    gate_pass_rates,
    reject_recurrence_rate,
)
from src.officina.models import (
    Deal,
    GateResult,
    GateType,
    Lead,
    RejectLogEntry,
    Stage,
    StageResult,
    Verdict,
)


def _deal_with(stage: Stage, verdict: Verdict) -> Deal:
    d = Deal(lead=Lead(company="x"))
    d.record(StageResult(stage, "outreach", {}, GateResult(GateType.DETERMINISTIC, verdict)))
    return d


def test_funnel_uses_held_not_booked():
    f = FunnelCounts(sent=100, replies=20, booked=10, held=4, closed_won=2)
    assert f.reply_rate() == 0.2
    assert f.booked_to_held_rate() == 0.4  # 予約 10 のうち実施 4
    assert f.win_rate() == 0.5  # 実施 4 のうち成約 2


def test_gate_pass_rates():
    deals = [
        _deal_with(Stage.OUTREACH, Verdict.PASS),
        _deal_with(Stage.OUTREACH, Verdict.FAIL),
        _deal_with(Stage.OUTREACH, Verdict.PASS),
    ]
    rates = gate_pass_rates(deals)
    assert abs(rates[Stage.OUTREACH] - 2 / 3) < 1e-9


def test_reject_recurrence_rate():
    log = RejectLog()
    for tag in ["絶対", "絶対", "必ず"]:  # 「絶対」が再発
        log.record(
            RejectLogEntry(
                stage=Stage.PROPOSAL, agent="proposer", content="", reasons=[], pattern_tags=[tag]
            )
        )
    # 3 件中 1 件が再発。
    assert abs(reject_recurrence_rate(log) - 1 / 3) < 1e-9


def test_high_complaint_rate_triggers_level4_audit():
    cfg = OfficinaConfig()  # complaint threshold 0.001
    tracker = KpiTracker(cfg)
    report = tracker.report(FunnelCounts(), [], RejectLog(), complaint_rate=0.05)
    triggers = tracker.withdrawal_triggers(report)
    assert any(t.level == 4 and "監査" in t.action for t in triggers)


def test_low_win_rate_triggers_closing_review():
    tracker = KpiTracker(OfficinaConfig())
    funnel = FunnelCounts(held=10, closed_won=1)  # 10% < 38% 基準
    report = tracker.report(funnel, [], RejectLog())
    triggers = tracker.withdrawal_triggers(report)
    assert any("クロージング" in t.action for t in triggers)


def test_healthy_win_rate_no_closing_trigger():
    tracker = KpiTracker(OfficinaConfig())
    won = int(HYBRID_WIN_RATE_BASELINE * 10) + 1
    report = tracker.report(FunnelCounts(held=10, closed_won=won), [], RejectLog())
    assert not any("クロージング" in t.action for t in tracker.withdrawal_triggers(report))


def test_low_gate_pass_rate_pauses_stage_autonomy():
    tracker = KpiTracker(OfficinaConfig())
    deals = [
        _deal_with(Stage.QUALIFY, Verdict.FAIL),
        _deal_with(Stage.QUALIFY, Verdict.FAIL),
        _deal_with(Stage.QUALIFY, Verdict.PASS),
    ]
    report = tracker.report(FunnelCounts(), deals, RejectLog())
    triggers = tracker.withdrawal_triggers(report)
    assert any("自律を一時停止" in t.action for t in triggers)
