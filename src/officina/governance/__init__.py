"""ガバナンス 3 層(要件定義 §6)。

すべての自律実行はこの 3 層を通る。

- ``deterministic_gates`` / ``deliverability`` / ``permissions``: §6.1 決定論ゲート層
- ``guardian_gate``: §6.2 Guardian 独立検証層
- ``hitl``: §6.3 人間 HITL ゲート層(契約署名・納品承認の 2 点)
- ``reject_log``: 設計原則 #6 リジェクトログ = リグレッションテスト
"""

from src.officina.governance.deliverability import DeliverabilityMonitor
from src.officina.governance.deterministic_gates import DeterministicGates
from src.officina.governance.guardian_gate import GuardianGate
from src.officina.governance.hitl import ApprovalStore, HumanGate, escalate
from src.officina.governance.permissions import (
    PermissionDenied,
    check_permission,
    enforce_permission,
)
from src.officina.governance.reject_log import RejectLog

__all__ = [
    "DeterministicGates",
    "DeliverabilityMonitor",
    "GuardianGate",
    "HumanGate",
    "ApprovalStore",
    "escalate",
    "PermissionDenied",
    "check_permission",
    "enforce_permission",
    "RejectLog",
]
