"""Deliverability 防衛(要件定義 §3 / §8.1)。事業継続条件。"""

from __future__ import annotations

from src.officina.config import OfficinaConfig
from src.officina.governance.deliverability import (
    DeliverabilityMetrics,
    DeliverabilityMonitor,
)
from src.officina.models import Verdict


def _monitor() -> DeliverabilityMonitor:
    return DeliverabilityMonitor(OfficinaConfig())


def test_healthy_metrics_pass():
    m = DeliverabilityMetrics(bounce_rate=0.01, complaint_rate=0.0001, domain_reputation=95)
    assert _monitor().health_check(m).verdict == Verdict.PASS


def test_high_bounce_rate_halts():
    m = DeliverabilityMetrics(bounce_rate=0.1)
    r = _monitor().health_check(m)
    assert r.verdict == Verdict.FAIL
    assert r.details["halt_outreach"] is True


def test_high_complaint_rate_halts():
    m = DeliverabilityMetrics(complaint_rate=0.05)
    assert _monitor().health_check(m).verdict == Verdict.FAIL


def test_low_reputation_halts():
    m = DeliverabilityMetrics(domain_reputation=50)
    assert _monitor().health_check(m).verdict == Verdict.FAIL


def test_warmup_ramps_then_caps():
    mon = _monitor()  # initial=20, increment=20, cap=200
    assert mon.warmup_limit(0) == 20
    assert mon.warmup_limit(3) == 80
    assert mon.warmup_limit(100) == 200  # 上限で頭打ち


def test_volume_cap_during_warmup():
    mon = _monitor()
    # 稼働 1 日目(上限 40)で 50 通送信済み → 停止。
    m = DeliverabilityMetrics(sent_today=50, domain_age_days=1)
    assert mon.health_check(m).verdict == Verdict.FAIL
