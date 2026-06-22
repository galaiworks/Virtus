"""§12 オープン決定事項の確定(v0.3)。

要件定義 v0.1 §12 で判断保留だった 5 点を、§3 が示す「勝ち筋」に沿って確定する。
すべて単一の真実源としてここに集約し、`OfficinaConfig` から参照する。
方針変更時はここを書き換えれば全体に波及する。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AcvStrategy(str, Enum):
    """§12-1 初期ターゲット ACV 帯。"""

    LOW_VOLUME = "low_acv_high_volume"  # $25k 未満・単純意思決定(勝ち筋)
    MID_HUMAN_HEAVY = "mid_acv_human_heavy"  # 中 ACV・人間厚め


class DeliverableScope(str, Enum):
    """§12-2 受託する成果物の標準型。"""

    AGENT_BUILD_ONLY = "agent_build_only"  # クライアント向けエージェント構築に絞る
    BROAD = "broad"  # 広く取る


class SignalLayerMode(str, Enum):
    """§12-3 シグナル層(成否の 80-90%)の構築方針。"""

    INTEGRATION = "integration"  # 外部データ連携
    IN_HOUSE = "in_house"  # 自前構築
    HYBRID = "hybrid"  # 連携で開始し段階的に自前へ


class DeliverabilityInfra(str, Enum):
    """§12-5 deliverability 基盤の方針。"""

    IN_HOUSE = "in_house"  # 決定論ゲートで内製制御
    EXTERNAL_TOOL = "external_tool"  # 専用ツールを噛ませる


@dataclass(frozen=True)
class OpenDecisions:
    """§12 の 5 決定。"""

    acv_strategy: AcvStrategy
    deliverable_scope: DeliverableScope
    signal_layer: SignalLayerMode
    incorporate_corporate_scheme: bool  # §12-4 法人スキームを前提に組み込むか
    deliverability_infra: DeliverabilityInfra
    rationale: dict[str, str] = field(default_factory=dict)


#: v0.3 確定値(勝ち筋)。
CONFIRMED = OpenDecisions(
    acv_strategy=AcvStrategy.LOW_VOLUME,
    deliverable_scope=DeliverableScope.AGENT_BUILD_ONLY,
    signal_layer=SignalLayerMode.INTEGRATION,
    incorporate_corporate_scheme=True,
    deliverability_infra=DeliverabilityInfra.IN_HOUSE,
    rationale={
        "acv_strategy": "§3: $25k 未満の単純意思決定なら AI 主導が機能。勝ち筋に振る。",
        "deliverable_scope": "§12-2: 絞るほど合格基準(テストスイート相当)が作りやすく自律度が上がる。",
        "signal_layer": "§12-3: 80-90% を占める投資。Phase 1 は外部連携で立ち上げ、段階的に自前化。",
        "incorporate_corporate_scheme": "§12-4: 契約締結ゲート=法人名義受注に直結。法人設立を前提に組み込む。",
        "deliverability_infra": "§12-5: 事業継続条件。決定論ゲートで内製制御(ドメイン分離・ウォームアップ)。",
    },
)
