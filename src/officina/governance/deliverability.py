"""Deliverability 防衛(要件定義 §3 / §8.1 / §10.1)。

「撤退の主因はクロージング不全ではなく到達不全」。過剰自動送信でドメイン評価が
崩壊すると事業全体が止まる。deliverability は "機能" ではなく "前提"。

ここはすべて決定論。LLM に判断させない。
"""

from __future__ import annotations

from dataclasses import dataclass

from src.officina.config import OfficinaConfig
from src.officina.models import GateResult, GateType, Verdict


@dataclass
class DeliverabilityMetrics:
    """日次で監視する deliverability 指標。"""

    bounce_rate: float = 0.0  # バウンス率
    complaint_rate: float = 0.0  # スパム苦情率
    domain_reputation: float = 100.0  # ドメイン評価スコア(0-100)
    sent_today: int = 0  # 当日の送信数
    domain_age_days: int = 999  # ドメイン稼働日数(ウォームアップ判定)


class DeliverabilityMonitor:
    """deliverability 健全性ゲート + ウォームアップ制御。"""

    def __init__(self, config: OfficinaConfig) -> None:
        self.config = config

    def warmup_limit(self, domain_age_days: int) -> int:
        """ウォームアップ中ドメインの当日送信上限を返す。

        新規ドメインは初日 ``warmup_initial_limit`` から
        ``warmup_daily_increment`` ずつ上限を引き上げ、最終的に
        ``daily_send_limit`` に到達する。
        """
        c = self.config
        if domain_age_days < 0:
            domain_age_days = 0
        limit = c.warmup_initial_limit + c.warmup_daily_increment * domain_age_days
        return min(limit, c.daily_send_limit)

    def health_check(self, metrics: DeliverabilityMetrics) -> GateResult:
        """送信を継続してよいかを判定する(事業継続条件)。

        いずれかの閾値を超えたら ``FAIL``(= 即アウトリーチ停止)。
        """
        c = self.config
        reasons: list[str] = []

        if metrics.bounce_rate > c.bounce_rate_threshold:
            reasons.append(
                f"バウンス率 {metrics.bounce_rate:.3f} > 上限 {c.bounce_rate_threshold:.3f}"
            )
        if metrics.complaint_rate > c.complaint_rate_threshold:
            reasons.append(
                f"スパム苦情率 {metrics.complaint_rate:.4f} > 上限 "
                f"{c.complaint_rate_threshold:.4f}"
            )
        if metrics.domain_reputation < c.domain_reputation_floor:
            reasons.append(
                f"ドメイン評価 {metrics.domain_reputation:.1f} < 下限 "
                f"{c.domain_reputation_floor:.1f}"
            )

        effective_limit = self.warmup_limit(metrics.domain_age_days)
        if metrics.sent_today >= effective_limit:
            reasons.append(
                f"当日送信数 {metrics.sent_today} が上限 {effective_limit} に到達"
            )

        verdict = Verdict.PASS if not reasons else Verdict.FAIL
        return GateResult(
            gate_type=GateType.DETERMINISTIC,
            verdict=verdict,
            reasons=reasons,
            details={
                "effective_daily_limit": effective_limit,
                "halt_outreach": bool(reasons),
            },
        )
