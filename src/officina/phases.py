"""フェーズ計画(要件定義 §11)。

自律比率を "稼いで" 上げる。各フェーズで、どのステージを自律化し、どこを人間が
持つかを定義する。漸近線(asymptote)= 人間ゲートは契約署名と納品承認の 2 点に固定。
ここは恒久的に人間(自律の上限を正しく認める)。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from src.officina.models import Stage


class Phase(IntEnum):
    """展開フェーズ。"""

    PHASE_1 = 1  # ハイブリッド前提。低 ACV・単純意思決定から。1 案件で全工程を通す。
    PHASE_2 = 2  # 各ゲートの合格データが溜まり、人間の関与を例外のみに。
    PHASE_3 = 3  # 低額・単純クロージングを AI 主導へ拡張。契約署名は人間維持。


#: 恒久的に人間が持つステージ(漸近線)。どのフェーズでも自律化しない。
ASYMPTOTE_HUMAN_GATES: tuple[Stage, ...] = (Stage.CONTRACT, Stage.DELIVERY_APPROVAL)


@dataclass(frozen=True)
class PhasePlan:
    """1 フェーズの自律設計。"""

    phase: Phase
    #: このフェーズで人間が(恒常的に)関与するステージ。
    human_owned: frozenset[Stage]
    description: str

    def is_autonomous(self, stage: Stage) -> bool:
        """``stage`` がこのフェーズで自律実行されるか。"""
        return stage not in self.human_owned

    def autonomy_ratio(self) -> float:
        """全 12 ステージ中、自律実行されるステージの割合。"""
        autonomous = sum(1 for s in Stage if self.is_autonomous(s))
        return autonomous / len(Stage)


#: フェーズ定義。Phase をまたいでも漸近線(2 ゲート)は必ず人間が持つ。
PHASES: dict[Phase, PhasePlan] = {
    Phase.PHASE_1: PhasePlan(
        phase=Phase.PHASE_1,
        # ステージ 0-5・8-11 を自律、6(高額クロージング)・7・9 を人間。
        human_owned=frozenset(
            {Stage.ICP_RESEARCH, Stage.CLOSING, Stage.CONTRACT, Stage.DELIVERY_APPROVAL}
        ),
        description="ハイブリッド前提。低 ACV・単純意思決定の案件から 1 案件で全工程を通す。",
    ),
    Phase.PHASE_2: PhasePlan(
        phase=Phase.PHASE_2,
        # ICP 承認は残しつつ、Qualifier/Proposer 等の人間関与を例外のみに。
        human_owned=frozenset(
            {Stage.ICP_RESEARCH, Stage.CONTRACT, Stage.DELIVERY_APPROVAL}
        ),
        description="合格データが蓄積。例外エスカレーション率を下げ、人間の関与を例外のみに。",
    ),
    Phase.PHASE_3: PhasePlan(
        phase=Phase.PHASE_3,
        # クロージングの一部(低額・単純)を AI 主導へ。契約署名・納品承認は人間維持。
        human_owned=frozenset(ASYMPTOTE_HUMAN_GATES),
        description="低額・単純クロージングを AI 主導に拡張。契約署名は人間維持。",
    ),
}


def get_phase_plan(phase: Phase) -> PhasePlan:
    """フェーズ計画を取得する。"""
    return PHASES[phase]


def _validate_phases() -> None:
    """漸近線の不変条件:全フェーズで 2 つの人間ゲートを必ず人間が持つ。"""
    for plan in PHASES.values():
        for gate in ASYMPTOTE_HUMAN_GATES:
            assert gate in plan.human_owned, (
                f"{plan.phase.name}: 漸近線ゲート {gate.name} は恒久的に人間が持つ必要がある"
            )
    # 自律比率はフェーズが進むほど単調増加する。
    ratios = [PHASES[p].autonomy_ratio() for p in (Phase.PHASE_1, Phase.PHASE_2, Phase.PHASE_3)]
    assert ratios == sorted(ratios), "自律比率はフェーズ進行で単調増加すること"


_validate_phases()
