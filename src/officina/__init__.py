"""Officina — 自律型 AI エージェンシー OS。

営業リサーチ → アウトリーチ → 商談 → 提案 → クロージング補助 →【人間】契約 →
開発 →【人間】納品承認 → 納品 → アフター、を自律実行する。人間の接触点を
「ICP 承認 + 2 ゲート(契約署名・納品承認)」に圧縮する。

設計思想(要件定義 v0.1 §2):
1. 自律可能性 = 検証可能性 × 可逆性。
2. 各工程に「テストスイート相当の合格基準」を必ず定義する。
3. オーケストレーター・ワーカー型(God Model 禁止)。
4. 検証は独立エージェントで(生成と検証を分離)。
5. 決定論ゲートは LLM に判断させない。
6. リジェクトログ = リグレッションテスト。
"""

from src.officina.config import OfficinaConfig, load_config
from src.officina.metrics import (
    FunnelCounts,
    KpiReport,
    KpiTracker,
    WithdrawalTrigger,
)
from src.officina.models import (
    Deal,
    GateResult,
    GateType,
    Lead,
    Stage,
    StageDefinition,
    StageResult,
    Verdict,
)
from src.officina.orchestrator import Orchestrator
from src.officina.phases import PHASES, Phase, PhasePlan, get_phase_plan
from src.officina.pipeline import PIPELINE, get_stage, human_gates

__all__ = [
    "OfficinaConfig",
    "load_config",
    "Stage",
    "StageDefinition",
    "StageResult",
    "GateType",
    "GateResult",
    "Verdict",
    "Lead",
    "Deal",
    "PIPELINE",
    "get_stage",
    "human_gates",
    "Orchestrator",
    "Phase",
    "PhasePlan",
    "PHASES",
    "get_phase_plan",
    "FunnelCounts",
    "KpiReport",
    "KpiTracker",
    "WithdrawalTrigger",
]
