"""納品物の標準型と受入基準(§12-2 / 設計原則 #2 / §8.4)。

成果物を「クライアント向けエージェント構築」に絞る。絞るほど合格基準
(テストスイート相当)が作りやすく自律度が上がる。士業の独占業務に当たる成果物は
別棚(§8.4)として自律サービス枠から外す。
"""

from __future__ import annotations

from enum import Enum


class DeliverableType(str, Enum):
    """受託しうる成果物の種別。"""

    AGENT_BUILD = "agent_build"  # クライアント向けエージェント構築(標準型)
    LICENSED_PROFESSION = "licensed_profession"  # 士業独占業務(§8.4・別棚)
    OTHER = "other"


#: エージェント構築納品物の標準受入基準(= 決定論ゲートの合格条件)。
AGENT_BUILD_ACCEPTANCE_TEMPLATE: tuple[str, ...] = (
    "要件定義の必須項目をすべて満たす",
    "受入テストが全ケース通過する",
    "Guardian 独立検証に合格する(95 点ループ)",
    "本番 DB 書込・本番デプロイ権限を持たないゼロトラスト構成である",
    "疎通テスト(エンドツーエンド)が通過する",
)


def is_in_scope(deliverable_type: DeliverableType) -> bool:
    """成果物が自律サービス枠(エージェント構築)の対象か。

    士業独占業務は有資格者の関与が必須のため自律納品の対象外(§8.4)。
    """
    return deliverable_type == DeliverableType.AGENT_BUILD


def build_acceptance_tests(requirements: dict, extra: list[str] | None = None) -> list[str]:
    """エージェント構築納品物の受入テスト一式を生成する。

    標準テンプレートに、要件の success_criteria を機械検証可能な受入条件として加える。
    """
    tests = list(AGENT_BUILD_ACCEPTANCE_TEMPLATE)
    success = requirements.get("success_criteria")
    if success:
        tests.append(f"成功基準を満たす: {success}")
    if extra:
        tests.extend(extra)
    return tests
