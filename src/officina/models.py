"""Officina の中核データ構造。

パイプライン・ゲート・リード・案件・リジェクトログを表すデータクラス群。
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any


class Stage(IntEnum):
    """パイプラインのステージ番号(要件定義 §4)。"""

    ICP_RESEARCH = 0  # Scout: ICP・市場リサーチ
    PROSPECTING = 1  # Prospector: リスト構築・エンリッチ
    OUTREACH = 2  # Outreach: 多 ch ファーストタッチ
    QUALIFY = 3  # Qualifier: 返信トリアージ・一次対応
    DISCOVERY = 4  # Discovery: 商談・要件抽出
    PROPOSAL = 5  # Proposer: 提案・見積
    CLOSING = 6  # Closer: クロージング補助
    CONTRACT = 7  # 【人間】契約締結(ゲート A)
    BUILD = 8  # Architect+Builder+Guardian: 設計〜実装〜検証
    DELIVERY_APPROVAL = 9  # 【人間】納品物 最終承認(ゲート B)
    DELIVERY = 10  # Delivery: 納品・オンボーディング
    AFTERCARE = 11  # Ops+Analyst: 請求・保守・拡張


class GateType(str, Enum):
    """合格ゲートの種別(ガバナンス 3 層・要件定義 §6)。"""

    DETERMINISTIC = "deterministic"  # §6.1 LLM に判断させない if/then
    GUARDIAN = "guardian"  # §6.2 独立検証エージェント
    HUMAN = "human"  # §6.3 HITL ゲート(不可逆)
    NONE = "none"  # 自動ゲートなし(後続ゲートで担保)


class Verdict(str, Enum):
    """ゲート判定。"""

    PASS = "pass"
    FAIL = "fail"  # 再試行(リジェクトログへ)
    ESCALATE = "escalate"  # 人間エスカレーション
    PENDING_HUMAN = "pending_human"  # 人間ゲートで停止


class HumanRole(str, Enum):
    """各ステージにおける人間の関与レベル(要件定義 §4 の「人間」列)。"""

    NONE = "none"
    APPROVAL = "approval"  # ステージ0 戦略承認
    EXCEPTION = "exception"  # 例外のみ
    REVIEW = "review"  # レビュー
    CONDITIONAL = "conditional"  # 高額のみ(ACV 閾値で発火)
    MANDATORY = "mandatory"  # 🚩 必須・不可逆(契約署名・納品承認)


@dataclass
class GateResult:
    """ゲート 1 回の判定結果。"""

    gate_type: GateType
    verdict: Verdict
    score: float | None = None
    reasons: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.verdict == Verdict.PASS


@dataclass
class StageDefinition:
    """パイプライン 1 ステージの定義(要件定義 §4 の 1 行)。"""

    stage: Stage
    name: str
    owner: str  # 担当エージェント名
    output: str  # 主な出力
    gate_type: GateType  # 自動合格ゲートの種別
    human: HumanRole  # 人間の関与レベル
    model_tier: str  # コスト最適化のためのモデル階層(§5)
    description: str = ""

    @property
    def human_mandatory(self) -> bool:
        """🚩 人間必須ゲート(契約署名・納品承認)か。"""
        return self.human == HumanRole.MANDATORY


@dataclass
class Lead:
    """検証済みリード。"""

    company: str
    contact: str = ""
    email: str = ""
    source: str = ""
    signals: list[str] = field(default_factory=list)
    score: float = 0.0
    verified: bool = False
    id: str = field(default_factory=lambda: f"lead_{uuid.uuid4().hex[:8]}")


@dataclass
class StageResult:
    """1 ステージの実行+ゲート結果。"""

    stage: Stage
    agent: str
    output: dict[str, Any]
    gate: GateResult
    retries: int = 0
    timestamp: float = field(default_factory=time.time)

    @property
    def status(self) -> Verdict:
        return self.gate.verdict


@dataclass
class Deal:
    """1 案件。パイプラインを流れる単位。"""

    lead: Lead
    acv: float = 0.0  # 想定契約額(USD)。クロージング・契約ゲートの判断に使う
    history: list[StageResult] = field(default_factory=list)
    current_stage: Stage = Stage.ICP_RESEARCH
    status: str = "open"  # open | pending_human | escalated | won | lost | delivered
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"deal_{uuid.uuid4().hex[:8]}")

    def record(self, result: StageResult) -> None:
        self.history.append(result)
        self.current_stage = result.stage


@dataclass
class RejectLogEntry:
    """リジェクトログ 1 件(= リグレッションテスト 1 件・設計原則 #6)。"""

    stage: Stage
    agent: str
    content: str
    reasons: list[str]
    pattern_tags: list[str] = field(default_factory=list)
    deal_id: str = ""
    timestamp: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: f"reject_{uuid.uuid4().hex[:8]}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "stage": int(self.stage),
            "agent": self.agent,
            "content": self.content,
            "reasons": self.reasons,
            "pattern_tags": self.pattern_tags,
            "deal_id": self.deal_id,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RejectLogEntry:
        return cls(
            stage=Stage(data["stage"]),
            agent=data["agent"],
            content=data["content"],
            reasons=list(data.get("reasons", [])),
            pattern_tags=list(data.get("pattern_tags", [])),
            deal_id=data.get("deal_id", ""),
            timestamp=data.get("timestamp", time.time()),
            id=data.get("id", f"reject_{uuid.uuid4().hex[:8]}"),
        )
