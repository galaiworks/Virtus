"""人間 HITL ゲート層(要件定義 §6.3 / §7 / escalation.md)。

人間が所有するのは 2 つの不可逆ゲートのみ:
- ゲート A:契約締結(署名)
- ゲート B:納品物 最終承認

加えて Qualifier/Proposer 等からの例外エスカレーションを受ける。
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from src.officina.logger import get_logger
from src.officina.models import GateResult, GateType, Stage, Verdict

_logger = get_logger("officina.hitl")

#: escalation.md の Level -> 通知チャネル。
ESCALATION_CHANNELS: dict[int, list[str]] = {
    1: ["slack"],
    2: ["slack"],
    3: ["slack", "line"],
    4: ["slack", "line", "email", "sms"],
}


@dataclass
class ApprovalRequest:
    """人間の承認待ち 1 件。"""

    deal_id: str
    stage: Stage
    summary: str
    payload: dict[str, Any] = field(default_factory=dict)
    decision: str | None = None  # None=pending | approve | reject
    note: str = ""
    created_at: float = field(default_factory=time.time)
    decided_at: float | None = None
    id: str = field(default_factory=lambda: f"appr_{uuid.uuid4().hex[:8]}")


class ApprovalStore:
    """承認リクエストの保管(Phase 1 はインメモリ。Phase 2+ で Supabase へ)。"""

    def __init__(self) -> None:
        self._items: dict[str, ApprovalRequest] = {}

    def submit(
        self, deal_id: str, stage: Stage, summary: str, payload: dict[str, Any] | None = None
    ) -> ApprovalRequest:
        req = ApprovalRequest(
            deal_id=deal_id, stage=stage, summary=summary, payload=payload or {}
        )
        self._items[req.id] = req
        _logger.info("HITL 承認依頼 %s: deal=%s stage=%s", req.id, deal_id, stage.name)
        return req

    def decide(self, request_id: str, decision: str, note: str = "") -> ApprovalRequest:
        if decision not in {"approve", "reject"}:
            raise ValueError("decision は 'approve' か 'reject'")
        req = self._items[request_id]
        req.decision = decision
        req.note = note
        req.decided_at = time.time()
        _logger.info("HITL 決定 %s: %s", request_id, decision)
        return req

    def pending(self) -> list[ApprovalRequest]:
        return [r for r in self._items.values() if r.decision is None]

    def get(self, request_id: str) -> ApprovalRequest:
        return self._items[request_id]


class HumanGate:
    """🚩 人間必須ゲート(契約署名・納品承認)。

    自律実行を必ず停止し、承認依頼を起票して ``PENDING_HUMAN`` を返す。
    """

    def __init__(self, store: ApprovalStore | None = None) -> None:
        self.store = store or ApprovalStore()

    def request(self, deal_id: str, stage: Stage, summary: str, **payload: Any) -> GateResult:
        req = self.store.submit(deal_id, stage, summary, payload)
        return GateResult(
            gate_type=GateType.HUMAN,
            verdict=Verdict.PENDING_HUMAN,
            reasons=[f"人間ゲート({stage.name})の承認待ち"],
            details={"approval_id": req.id, "summary": summary},
        )

    def resolve(self, approval_id: str) -> GateResult:
        """人間の決定を取り込み、最終ゲート結果へ変換する。"""
        req = self.store.get(approval_id)
        if req.decision is None:
            return GateResult(
                gate_type=GateType.HUMAN,
                verdict=Verdict.PENDING_HUMAN,
                details={"approval_id": approval_id},
            )
        verdict = Verdict.PASS if req.decision == "approve" else Verdict.FAIL
        return GateResult(
            gate_type=GateType.HUMAN,
            verdict=verdict,
            reasons=[req.note] if req.note else [],
            details={"approval_id": approval_id, "decision": req.decision},
        )


def escalate(level: int, reason: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """例外エスカレーション(escalation.md の Level 1-4)。

    実通知は Distributor/通知層が行う。ここでは監査ログと通知計画を返す。
    """
    level = max(1, min(4, level))
    channels = ESCALATION_CHANNELS[level]
    record = {
        "level": level,
        "reason": reason,
        "channels": channels,
        "details": details or {},
        "timestamp": time.time(),
    }
    _logger.warning("ESCALATION L%d: %s -> %s", level, reason, channels)
    return record
