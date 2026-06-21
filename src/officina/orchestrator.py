"""Orchestrator(Virtus: Lead Strategist)— 全工程の分解・委任・統合(要件定義 §5)。

オーケストレーター・ワーカー型(設計原則 #3)。単一巨大プロンプトの God Model は禁止。
スーパーバイザーが案件をステージごとに分解し、専門ワーカーへ委任、各ステージの
合格ゲート(決定論 / Guardian / 人間)を通してから次へ進める。

人間の接触点は ICP 承認 + 2 ゲート(契約署名・納品承認)に圧縮される。
"""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent
from src.officina.agents import (
    ArchitectBuilder,
    Closer,
    Delivery,
    Discovery,
    Ops,
    Outreach,
    Proposer,
    Prospector,
    Qualifier,
    Scout,
)
from src.officina.config import OfficinaConfig, load_config
from src.officina.governance.deterministic_gates import DeterministicGates
from src.officina.governance.guardian_gate import GuardianGate
from src.officina.governance.hitl import ApprovalStore, HumanGate, escalate
from src.officina.governance.permissions import enforce_permission
from src.officina.governance.reject_log import RejectLog
from src.officina.logger import get_logger
from src.officina.models import (
    Deal,
    GateResult,
    GateType,
    HumanRole,
    RejectLogEntry,
    Stage,
    StageDefinition,
    StageResult,
    Verdict,
)
from src.officina.pipeline import PIPELINE, get_stage

_logger = get_logger("officina.orchestrator")

#: ステージ -> ワーカーエージェントクラス(人間所有ステージは None)。
_ROSTER: dict[Stage, type[BaseAgent] | None] = {
    Stage.ICP_RESEARCH: Scout,
    Stage.PROSPECTING: Prospector,
    Stage.OUTREACH: Outreach,
    Stage.QUALIFY: Qualifier,
    Stage.DISCOVERY: Discovery,
    Stage.PROPOSAL: Proposer,
    Stage.CLOSING: Closer,
    Stage.CONTRACT: None,
    Stage.BUILD: ArchitectBuilder,
    Stage.DELIVERY_APPROVAL: None,
    Stage.DELIVERY: Delivery,
    Stage.AFTERCARE: Ops,
}

#: ステージ別の自動合格しきい値。
PROSPECT_VERIFICATION_FLOOR = 0.5
QUALIFY_CONFIDENCE_FLOOR = 0.7


class Orchestrator:
    """案件をパイプラインに沿って自律実行する。"""

    def __init__(
        self,
        brand_dna: dict[str, Any],
        config: OfficinaConfig | None = None,
        reject_log: RejectLog | None = None,
        approval_store: ApprovalStore | None = None,
    ) -> None:
        self.brand_dna = brand_dna
        self.config = config or load_config()
        self.gates = DeterministicGates(self.config)
        self.guardian = GuardianGate(
            threshold=self.config.quality_threshold, brand_dna=brand_dna
        )
        self.reject_log = reject_log or RejectLog()
        self.approvals = approval_store or ApprovalStore()
        self.human_gate = HumanGate(self.approvals)
        self._agents: dict[Stage, BaseAgent] = {}

    # ------------------------------------------------------------------ #
    # 公開 API
    # ------------------------------------------------------------------ #
    def run(self, deal: Deal, stage_inputs: dict[Stage, dict[str, Any]] | None = None) -> Deal:
        """``deal.current_stage`` から前進実行する。

        人間ゲート(PENDING_HUMAN)・エスカレーション・最大再試行超過で停止する。
        """
        stage_inputs = stage_inputs or {}
        for sd in PIPELINE:
            if sd.stage < deal.current_stage:
                continue
            task = stage_inputs.get(sd.stage, {})
            result = self._run_stage(deal, sd, task)
            deal.record(result)

            v = result.status
            if v == Verdict.PASS:
                continue
            if v == Verdict.PENDING_HUMAN:
                deal.status = "pending_human"
                deal.metadata["pending_approval"] = result.gate.details.get("approval_id")
                _logger.info("案件 %s はステージ %s で人間待ち", deal.id, sd.stage.name)
                return deal
            if v in (Verdict.FAIL, Verdict.ESCALATE):
                deal.status = "escalated"
                escalate(
                    level=3,
                    reason=f"ステージ {sd.stage.name} が合格基準未達",
                    details={"deal_id": deal.id, "reasons": result.gate.reasons},
                )
                return deal

        deal.status = "delivered"
        return deal

    def resume(
        self,
        deal: Deal,
        decision: str,
        note: str = "",
        stage_inputs: dict[Stage, dict[str, Any]] | None = None,
    ) -> Deal:
        """人間ゲートの決定を取り込み、続行する。

        Args:
            decision: ``"approve"`` または ``"reject"``。
        """
        approval_id = deal.metadata.get("pending_approval")
        if not approval_id:
            raise ValueError("この案件に承認待ちはありません。")
        self.approvals.decide(approval_id, decision, note)
        gate = self.human_gate.resolve(approval_id)
        deal.metadata.pop("pending_approval", None)

        if not gate.passed:
            deal.status = "lost"
            self.reject_log.record(
                RejectLogEntry(
                    stage=deal.current_stage,
                    agent="human",
                    content=note or "人間が却下",
                    reasons=["human_rejected"],
                    pattern_tags=[],
                    deal_id=deal.id,
                )
            )
            return deal

        # 承認されたので次ステージへ。
        deal.current_stage = Stage(int(deal.current_stage) + 1)
        deal.status = "open"
        return self.run(deal, stage_inputs)

    # ------------------------------------------------------------------ #
    # 内部
    # ------------------------------------------------------------------ #
    def _agent_for(self, sd: StageDefinition) -> BaseAgent | None:
        cls = _ROSTER[sd.stage]
        if cls is None:
            return None
        if sd.stage not in self._agents:
            self._agents[sd.stage] = cls(
                model=self.config.models.resolve(sd.model_tier),
                brand_dna=self.brand_dna,
                skills=["galai-tone"],
                dry_run=self.config.dry_run,
            )
        return self._agents[sd.stage]

    def _run_stage(
        self, deal: Deal, sd: StageDefinition, task: dict[str, Any]
    ) -> StageResult:
        """1 ステージを実行し、合格ゲートを通す(必要なら再試行)。"""
        agent = self._agent_for(sd)

        # 人間所有ステージ(契約・納品承認)はエージェント実行なし。
        if agent is None:
            if sd.gate_type == GateType.HUMAN:
                gate = self.human_gate.request(deal.id, sd.stage, sd.name)
            else:
                gate = GateResult(GateType.NONE, Verdict.PASS)
            return StageResult(sd.stage, sd.owner, {}, gate)

        max_attempts = self.config.max_retries + 1
        last: StageResult | None = None
        for attempt in range(max_attempts):
            enforce_permission_for_stage(agent, sd)
            result = agent.execute({**task, "_attempt": attempt})
            gate = self._automatic_gate(sd, result, deal)

            if gate.verdict == Verdict.PASS:
                gate = self._apply_human_overlay(deal, sd, gate)
                return StageResult(sd.stage, agent.name, result.output, gate, attempt)

            # 失敗・エスカレーションはリジェクトログへ(= リグレッションテスト化)。
            self.reject_log.record(
                RejectLogEntry(
                    stage=sd.stage,
                    agent=agent.name,
                    content=str(result.output.get("content", result.output))[:500],
                    reasons=gate.reasons,
                    pattern_tags=_pattern_tags(gate),
                    deal_id=deal.id,
                )
            )
            last = StageResult(sd.stage, agent.name, result.output, gate, attempt)
            if gate.verdict == Verdict.ESCALATE:
                return last  # 再試行せず人間へ

        assert last is not None
        return last

    def _automatic_gate(
        self, sd: StageDefinition, result: Any, deal: Deal
    ) -> GateResult:
        g = result.output.get("gate", {})
        if sd.gate_type == GateType.HUMAN:
            return self.human_gate.request(deal.id, sd.stage, sd.name)
        if sd.gate_type == GateType.NONE:
            return GateResult(GateType.NONE, Verdict.PASS)
        if sd.gate_type == GateType.GUARDIAN:
            return self._guardian_gate(sd, result, g)
        return self._deterministic_gate(sd, result, deal)

    def _deterministic_gate(
        self, sd: StageDefinition, result: Any, deal: Deal
    ) -> GateResult:
        stage = sd.stage
        g = result.output.get("gate", {})
        if stage == Stage.ICP_RESEARCH:
            ok = bool(g.get("sources_verified"))
            return GateResult(
                GateType.DETERMINISTIC,
                Verdict.PASS if ok else Verdict.FAIL,
                reasons=[] if ok else ["ソース実在性チェック不合格"],
            )
        if stage == Stage.PROSPECTING:
            rate = float(g.get("verification_rate", 0.0))
            ok = rate >= PROSPECT_VERIFICATION_FLOOR
            return GateResult(
                GateType.DETERMINISTIC,
                Verdict.PASS if ok else Verdict.FAIL,
                reasons=[] if ok else [f"データ検証率 {rate:.0%} が基準未満"],
                details={"verification_rate": rate},
            )
        if stage == Stage.OUTREACH:
            return self.gates.outreach_gate(
                g.get("metrics"),
                recipient_touch_count=int(g.get("touch_count", 0)),
                opt_out=bool(g.get("opt_out", False)),
            )
        if stage == Stage.DISCOVERY:
            ok = bool(g.get("required_fields_complete"))
            return GateResult(
                GateType.DETERMINISTIC,
                Verdict.PASS if ok else Verdict.FAIL,
                reasons=[] if ok else [f"必須項目不足: {g.get('missing_fields')}"],
            )
        if stage == Stage.PROPOSAL:
            return self.gates.price_gate(
                float(g.get("price_usd", 0.0)),
                list_price_usd=g.get("list_price_usd"),
                discount_approved=bool(g.get("discount_approved", False)),
            )
        if stage == Stage.BUILD:
            if not bool(g.get("tests_passed")):
                return GateResult(
                    GateType.DETERMINISTIC,
                    Verdict.FAIL,
                    reasons=["受入テスト未通過(合格基準=テストスイート)"],
                )
            # テスト通過後、Guardian が独立検証(生成と検証の分離・原則 #4)。
            return self.guardian.evaluate(
                str(result.output.get("design", result.output)),
                content_type="deliverable",
            )
        if stage == Stage.DELIVERY:
            ok = bool(g.get("smoke_test_passed"))
            return GateResult(
                GateType.DETERMINISTIC,
                Verdict.PASS if ok else Verdict.FAIL,
                reasons=[] if ok else ["疎通テスト不合格"],
            )
        if stage == Stage.AFTERCARE:
            return self.gates.billing_trigger(
                bool(g.get("contract_active", False)),
                bool(g.get("deliverable_accepted", False)),
            )
        return GateResult(GateType.DETERMINISTIC, Verdict.PASS)

    def _guardian_gate(self, sd: StageDefinition, result: Any, g: dict[str, Any]) -> GateResult:
        if sd.stage == Stage.QUALIFY:
            level = int(g.get("escalation_level", 0))
            if level > 0:
                escalate(level, "Qualifier が危険ワード/高リスクを検出", g)
                return GateResult(
                    GateType.GUARDIAN,
                    Verdict.ESCALATE,
                    reasons=[f"エスカレーション Level {level}"],
                )
            conf = float(g.get("confidence", 0.0))
            if conf < QUALIFY_CONFIDENCE_FLOOR:
                return GateResult(
                    GateType.GUARDIAN,
                    Verdict.ESCALATE,
                    score=conf * 100,
                    reasons=[f"分類信頼度 {conf:.0%} が基準未満(曖昧→人間)"],
                )
            return GateResult(GateType.GUARDIAN, Verdict.PASS, score=conf * 100)
        # 既定:コンテンツを 95 点ループで検証。
        return self.guardian.evaluate(
            str(result.output.get("content", "")), content_type=result.content_type
        )

    def _apply_human_overlay(
        self, deal: Deal, sd: StageDefinition, gate: GateResult
    ) -> GateResult:
        """自動ゲート合格後に、ステージの人間関与レベルを重ねる。"""
        if sd.human == HumanRole.MANDATORY:
            return gate  # 既に HUMAN ゲートで PENDING_HUMAN になっている
        if sd.human == HumanRole.APPROVAL:
            if not deal.metadata.get("icp_approved"):
                return self.human_gate.request(deal.id, sd.stage, f"{sd.name} 承認")
            return gate
        if sd.human == HumanRole.CONDITIONAL and sd.stage == Stage.CLOSING:
            if deal.acv >= self.config.acv_human_required_usd:
                return self.human_gate.request(
                    deal.id, sd.stage, "高額クロージング(人間主導)"
                )
        return gate


# ---------------------------------------------------------------------- #
# モジュール関数
# ---------------------------------------------------------------------- #
def enforce_permission_for_stage(agent: BaseAgent, sd: StageDefinition) -> None:
    """ステージの主要アクションについてゼロトラスト権限を強制する。"""
    primary_action = {
        Stage.OUTREACH: "send_email",
        Stage.BUILD: "write_code",
        Stage.AFTERCARE: "create_invoice",
    }.get(sd.stage)
    if primary_action:
        enforce_permission(agent.name, primary_action)


def _pattern_tags(gate: GateResult) -> list[str]:
    """リジェクト理由から回帰照合用のパターンタグを抽出する。"""
    tags: list[str] = []
    for r in gate.reasons:
        # 「」で囲まれた表現を回帰タグ化(過剰約束・禁止語など)。
        if "「" in r and "」" in r:
            tags.append(r.split("「", 1)[1].split("」", 1)[0])
    return tags
