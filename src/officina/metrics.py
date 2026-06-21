"""KPI と撤退基準(要件定義 §10)。

虚栄指標を排し、deliverability → 実施率 → クローズドウォンの実数で測る。
ゲート合格率・リジェクト再発率を監視し、撤退/見直しトリガーを機械判定する。
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from src.officina.config import OfficinaConfig
from src.officina.governance.reject_log import RejectLog
from src.officina.models import Deal, Stage, Verdict

# グローバル勝ち筋(要件定義 §3)。ハイブリッドのクローズドウォン基準。
HYBRID_WIN_RATE_BASELINE = 0.38
# ゲート合格率の下限(割ると該当工程の自律を一時停止し人間比率を上げる・§10.2)。
GATE_PASS_RATE_FLOOR = 0.7
# 本番保守コスト(1 体あたり 人月/継続・§3)。粗利計算に織り込む。
MAINTENANCE_PERSON_MONTHS_PER_AGENT = (0.25, 0.5)


@dataclass
class FunnelCounts:
    """ファネルの実数(予約数ではなく実施・成約で測る)。"""

    sent: int = 0
    replies: int = 0
    booked: int = 0  # 商談予約
    held: int = 0  # 商談実施
    qualified: int = 0
    proposals: int = 0
    closed_won: int = 0
    closed_lost: int = 0

    def reply_rate(self) -> float:
        return _ratio(self.replies, self.sent)

    def booked_to_held_rate(self) -> float:
        """商談実施率(booked → held)。予約数ではなく実施で測る。"""
        return _ratio(self.held, self.booked)

    def win_rate(self) -> float:
        """クローズドウォン率(成約 / 実施商談)。"""
        return _ratio(self.closed_won, self.held)


@dataclass
class KpiReport:
    """期間 KPI のスナップショット。"""

    funnel: FunnelCounts
    gate_pass_rates: dict[Stage, float]
    reject_count: int
    reject_recurrence_rate: float
    deliverability_complaint_rate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "funnel": {
                "reply_rate": round(self.funnel.reply_rate(), 4),
                "booked_to_held": round(self.funnel.booked_to_held_rate(), 4),
                "win_rate": round(self.funnel.win_rate(), 4),
            },
            "gate_pass_rates": {s.name: round(v, 4) for s, v in self.gate_pass_rates.items()},
            "reject_count": self.reject_count,
            "reject_recurrence_rate": round(self.reject_recurrence_rate, 4),
            "deliverability_complaint_rate": self.deliverability_complaint_rate,
        }


@dataclass
class WithdrawalTrigger:
    """撤退/見直しトリガー 1 件(§10.2)。"""

    level: int
    reason: str
    action: str
    details: dict = field(default_factory=dict)


def _ratio(num: int, den: int) -> float:
    return num / den if den else 0.0


def gate_pass_rates(deals: list[Deal]) -> dict[Stage, float]:
    """ステージ別のゲート合格率を算出する。"""
    passed: dict[Stage, int] = defaultdict(int)
    total: dict[Stage, int] = defaultdict(int)
    for deal in deals:
        for result in deal.history:
            total[result.stage] += 1
            if result.status == Verdict.PASS:
                passed[result.stage] += 1
    return {stage: _ratio(passed[stage], total[stage]) for stage in total}


def reject_recurrence_rate(reject_log: RejectLog) -> float:
    """リジェクト再発率。

    すでに出現済みのパターンタグが再び弾かれた割合。ドリフトの代理指標。
    """
    entries = reject_log.entries()
    seen: set[str] = set()
    recurring = 0
    counted = 0
    for e in entries:
        for tag in e.pattern_tags:
            counted += 1
            if tag in seen:
                recurring += 1
            seen.add(tag)
    return _ratio(recurring, counted)


class KpiTracker:
    """KPI 集計と撤退トリガー判定。"""

    def __init__(self, config: OfficinaConfig | None = None) -> None:
        from src.officina.config import load_config

        self.config = config or load_config()

    def report(
        self,
        funnel: FunnelCounts,
        deals: list[Deal],
        reject_log: RejectLog,
        complaint_rate: float = 0.0,
    ) -> KpiReport:
        """KPI レポートを生成する。"""
        return KpiReport(
            funnel=funnel,
            gate_pass_rates=gate_pass_rates(deals),
            reject_count=len(reject_log),
            reject_recurrence_rate=reject_recurrence_rate(reject_log),
            deliverability_complaint_rate=complaint_rate,
        )

    def withdrawal_triggers(self, report: KpiReport) -> list[WithdrawalTrigger]:
        """撤退/見直しトリガーを評価する(§10.2)。"""
        triggers: list[WithdrawalTrigger] = []

        # スパム苦情率の上昇 → 即アウトリーチ監査(最優先)。
        if report.deliverability_complaint_rate > self.config.complaint_rate_threshold:
            triggers.append(
                WithdrawalTrigger(
                    level=4,
                    reason="スパム苦情率が上限を超過",
                    action="即アウトリーチ監査(deliverability は事業継続条件)",
                    details={"complaint_rate": report.deliverability_complaint_rate},
                )
            )

        # クローズドウォン率がハイブリッド基準を継続下回る → クロージング設計見直し。
        win_rate = report.funnel.win_rate()
        if report.funnel.held > 0 and win_rate < HYBRID_WIN_RATE_BASELINE:
            triggers.append(
                WithdrawalTrigger(
                    level=3,
                    reason=f"クローズドウォン率 {win_rate:.0%} がハイブリッド基準 "
                    f"{HYBRID_WIN_RATE_BASELINE:.0%} を下回る",
                    action="クロージング設計の見直し",
                    details={"win_rate": win_rate},
                )
            )

        # ゲート合格率が閾値割れ → 該当工程の自律を一時停止し人間比率を上げる。
        for stage, rate in report.gate_pass_rates.items():
            if rate < GATE_PASS_RATE_FLOOR:
                triggers.append(
                    WithdrawalTrigger(
                        level=3,
                        reason=f"{stage.name} のゲート合格率 {rate:.0%} が下限割れ",
                        action=f"{stage.name} の自律を一時停止し人間比率を上げる",
                        details={"stage": stage.name, "pass_rate": rate},
                    )
                )

        return triggers
