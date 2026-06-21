"""Officina パイプライン定義 — 11 ステージ ＋ 2 つの人間ゲート。

各ステージは「担当エージェント / 合格ゲート(テストスイート相当)/ 人間の関与」を
宣言的に持つ。これは要件定義 §4 のパイプライン全体図をコードに落としたもの。

ここでは「どのステージがどの種類のゲートを通るか」という骨格を定義する。
決定論ゲートの実体は :mod:`officina.gates` にある。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class HumanInvolvement(Enum):
    """各ステージにおける人間の関与レベル。"""

    NONE = "none"  # 自律。人間はタッチしない
    APPROVAL = "approval"  # 戦略承認(ICP 等)
    REVIEW = "review"  # レビュー(差し戻し可)
    EXCEPTION_ONLY = "exception_only"  # 例外時のみエスカレーション
    OPTIONAL = "optional"  # 高額のみ同席等
    DECISION = "decision"  # 人間主導の判断(高額クロージング)
    REQUIRED_IRREVERSIBLE = "required_irreversible"  # 🚩 人間必須・不可逆ゲート


@dataclass(frozen=True)
class Stage:
    """パイプラインの 1 ステージ。

    Attributes:
        number: ステージ番号(0-11)。
        name: ステージ名。
        agent: 担当エージェント名(``None`` は人間ゲート)。
        acceptance_gate: 合格基準の説明(テストスイート相当)。
        deterministic_gates: 通過すべき決定論ゲート関数名のリスト。
        human: 人間の関与レベル。
    """

    number: int
    name: str
    agent: str | None
    acceptance_gate: str
    deterministic_gates: tuple[str, ...]
    human: HumanInvolvement


#: 要件定義 §4 のパイプライン全体図。順序がそのまま実行順。
PIPELINE: tuple[Stage, ...] = (
    Stage(0, "ICP・市場リサーチ", "scout", "ソース実在性チェック", (), HumanInvolvement.APPROVAL),
    Stage(1, "リスト構築・エンリッチ", "prospector", "データ検証率・重複/不達除去", (), HumanInvolvement.NONE),
    Stage(
        2,
        "アウトリーチ(多ch・初回)",
        "outreach",
        "deliverability 健全性・送信量上限(決定論)",
        ("deliverability_gate", "send_volume_gate", "permission_scope_gate"),
        HumanInvolvement.NONE,
    ),
    Stage(
        3,
        "返信トリアージ・一次対応",
        "qualifier",
        "分類信頼度しきい値・曖昧時は人間エスカレーション",
        (),
        HumanInvolvement.EXCEPTION_ONLY,
    ),
    Stage(4, "商談・ヒアリング・要件抽出", "discovery", "必須項目充足チェック", (), HumanInvolvement.OPTIONAL),
    Stage(
        5,
        "提案・見積",
        "proposer",
        "価格ガードレール(決定論)・整合チェック",
        ("price_floor_gate",),
        HumanInvolvement.REVIEW,
    ),
    Stage(6, "クロージング補助", "closer", "(人間判断ステージ)", (), HumanInvolvement.DECISION),
    Stage(
        7,
        "契約締結",
        None,
        "電子契約フロー(Stripe/署名)",
        ("contract_trigger_gate",),
        HumanInvolvement.REQUIRED_IRREVERSIBLE,  # 🚩 ゲート A
    ),
    Stage(
        8,
        "要件定義→設計→実装→検証",
        "builder",
        "顧客テスト/受入基準＝合格基準(決定論)",
        ("prod_deploy_gate", "permission_scope_gate"),
        HumanInvolvement.NONE,
    ),
    Stage(
        9,
        "納品物 最終承認",
        None,
        "全テスト通過＋Guardian 合格",
        (),
        HumanInvolvement.REQUIRED_IRREVERSIBLE,  # 🚩 ゲート B
    ),
    Stage(10, "納品・オンボーディング", "delivery", "受入確認・疎通テスト", (), HumanInvolvement.NONE),
    Stage(
        11,
        "アフター(請求・保守・拡張)",
        "ops_analyst",
        "課金トリガー(決定論)・ドリフト監視",
        ("billing_gate",),
        HumanInvolvement.OPTIONAL,
    ),
)

#: 🚩 人間必須・不可逆ゲート(この 2 点のみが人間必須)。
HUMAN_GATES: tuple[int, ...] = tuple(
    s.number for s in PIPELINE if s.human is HumanInvolvement.REQUIRED_IRREVERSIBLE
)


def stage(number: int) -> Stage:
    """ステージ番号から :class:`Stage` を返す。"""
    for s in PIPELINE:
        if s.number == number:
            return s
    raise KeyError(f"unknown stage: {number}")


def requires_human_gate(number: int) -> bool:
    """指定ステージが人間必須・不可逆ゲートかを返す。"""
    return stage(number).human is HumanInvolvement.REQUIRED_IRREVERSIBLE


def assert_pipeline_integrity() -> None:
    """パイプライン不変条件を検査する(起動時のサニティチェック)。

    - 人間必須ゲートは契約締結(7)と納品物承認(9)の 2 点のみ。
    - ステージ番号は 0-11 の連番で重複しない。
    """
    numbers = [s.number for s in PIPELINE]
    if numbers != list(range(12)):
        raise AssertionError(f"pipeline stages must be 0-11 contiguous, got {numbers}")
    if HUMAN_GATES != (7, 9):
        raise AssertionError(
            f"人間ゲートは契約締結(7)と納品承認(9)の 2 点のみであるべき: {HUMAN_GATES}"
        )
