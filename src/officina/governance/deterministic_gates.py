"""決定論ゲート層(要件定義 §6.1)。

送信量上限・価格ガードレール・契約トリガー・課金・本番デプロイは
if/then のハードロジックで強制する。モデルの解釈に委ねない(設計原則 #5)。
"""

from __future__ import annotations

from src.officina.config import OfficinaConfig
from src.officina.governance.deliverability import (
    DeliverabilityMetrics,
    DeliverabilityMonitor,
)
from src.officina.models import GateResult, GateType, Verdict


class DeterministicGates:
    """LLM を介さない機械判定ゲート群。"""

    def __init__(self, config: OfficinaConfig) -> None:
        self.config = config
        self.deliverability = DeliverabilityMonitor(config)

    # --- ステージ 2: アウトリーチ ---
    def outreach_gate(
        self,
        metrics: DeliverabilityMetrics,
        recipient_touch_count: int = 0,
        opt_out: bool = False,
    ) -> GateResult:
        """送信可否を判定する。

        opt-out は即時反映(最優先)。次に deliverability 健全性、接触回数上限。
        """
        if opt_out:
            return GateResult(
                gate_type=GateType.DETERMINISTIC,
                verdict=Verdict.FAIL,
                reasons=["宛先が opt-out 済み(送信禁止・即時反映)"],
                details={"opt_out": True},
            )

        if recipient_touch_count >= self.config.per_recipient_touch_limit:
            return GateResult(
                gate_type=GateType.DETERMINISTIC,
                verdict=Verdict.FAIL,
                reasons=[
                    f"同一宛先への接触 {recipient_touch_count} 回が上限 "
                    f"{self.config.per_recipient_touch_limit} に到達"
                ],
            )

        return self.deliverability.health_check(metrics)

    # --- ステージ 5: 提案・見積 ---
    def price_gate(
        self,
        price_usd: float,
        list_price_usd: float | None = None,
        discount_approved: bool = False,
    ) -> GateResult:
        """価格ガードレール。下限割れと未承認値引きを禁止する。"""
        reasons: list[str] = []
        c = self.config

        if price_usd < c.price_floor_usd:
            reasons.append(
                f"提示価格 ${price_usd:,.0f} が下限 ${c.price_floor_usd:,.0f} を下回る"
            )

        if list_price_usd and list_price_usd > 0:
            discount = (list_price_usd - price_usd) / list_price_usd
            if discount > c.max_discount_pct and not discount_approved:
                reasons.append(
                    f"値引き {discount:.0%} が承認なし上限 {c.max_discount_pct:.0%} を超過"
                )

        verdict = Verdict.PASS if not reasons else Verdict.ESCALATE
        return GateResult(
            gate_type=GateType.DETERMINISTIC,
            verdict=verdict,
            reasons=reasons,
            details={"price_usd": price_usd},
        )

    # --- ステージ 7: 契約トリガー ---
    def contract_trigger(self, signed: bool, signer_is_human: bool) -> GateResult:
        """契約成立条件。署名主体は必ず人間(§8.3)。"""
        reasons: list[str] = []
        if not signer_is_human:
            reasons.append("署名主体が人間ではない(契約署名はゲート A・人間必須)")
        if not signed:
            reasons.append("未署名")
        verdict = Verdict.PASS if not reasons else Verdict.PENDING_HUMAN
        return GateResult(
            gate_type=GateType.DETERMINISTIC, verdict=verdict, reasons=reasons
        )

    # --- ステージ 8: 本番デプロイ ---
    def prod_deploy_gate(
        self, all_tests_passed: bool, guardian_approved: bool, human_approved: bool
    ) -> GateResult:
        """本番デプロイ条件。全テスト通過 + Guardian 合格 + 人間承認(ゲート B)。"""
        reasons: list[str] = []
        if not all_tests_passed:
            reasons.append("全テスト未通過")
        if not guardian_approved:
            reasons.append("Guardian 未承認")
        if not human_approved:
            reasons.append("納品物 最終承認(ゲート B)未取得")
        verdict = Verdict.PASS if not reasons else Verdict.FAIL
        return GateResult(
            gate_type=GateType.DETERMINISTIC, verdict=verdict, reasons=reasons
        )

    # --- ステージ 11: 課金トリガー ---
    def billing_trigger(
        self, contract_active: bool, deliverable_accepted: bool
    ) -> GateResult:
        """課金実行条件。契約有効かつ納品受入済みであること。"""
        reasons: list[str] = []
        if not contract_active:
            reasons.append("有効な契約がない")
        if not deliverable_accepted:
            reasons.append("納品受入が未確認")
        verdict = Verdict.PASS if not reasons else Verdict.FAIL
        return GateResult(
            gate_type=GateType.DETERMINISTIC, verdict=verdict, reasons=reasons
        )
