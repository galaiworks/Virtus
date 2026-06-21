"""パイプライン全体図(要件定義 §4)。

各ステージ = 担当エージェント / 出力 / 合格ゲート(テストスイート相当)/ 人間の関与。
🚩 = 人間必須ゲート(契約署名・納品承認の 2 点のみ)。
"""

from __future__ import annotations

from src.officina.models import GateType, HumanRole, Stage, StageDefinition

PIPELINE: list[StageDefinition] = [
    StageDefinition(
        stage=Stage.ICP_RESEARCH,
        name="ICP・市場リサーチ",
        owner="scout",
        output="ICP 仮説・ターゲットリスト母集団",
        gate_type=GateType.DETERMINISTIC,  # ソース実在性チェック
        human=HumanRole.APPROVAL,  # 戦略承認
        model_tier="sonnet",
        description="誰に売るか・何を売るかの仮説と母集団を作る。",
    ),
    StageDefinition(
        stage=Stage.PROSPECTING,
        name="リスト構築・エンリッチ",
        owner="prospector",
        output="検証済みリード + シグナル",
        gate_type=GateType.DETERMINISTIC,  # データ検証率・重複/不達除去
        human=HumanRole.NONE,
        model_tier="haiku",
        description="シグナル層が本丸(成否の 80-90%)。",
    ),
    StageDefinition(
        stage=Stage.OUTREACH,
        name="アウトリーチ(多 ch・初回)",
        owner="outreach",
        output="送信済みシーケンス",
        gate_type=GateType.DETERMINISTIC,  # deliverability 健全性・送信量上限
        human=HumanRole.NONE,
        model_tier="haiku",
        description="deliverability は前提。決定論で送信量を強制。",
    ),
    StageDefinition(
        stage=Stage.QUALIFY,
        name="返信トリアージ・一次対応",
        owner="qualifier",
        output="意図分類・クオリファイ済み商談",
        gate_type=GateType.GUARDIAN,  # 分類信頼度しきい値・曖昧時は人間へ
        human=HumanRole.EXCEPTION,
        model_tier="sonnet",
        description="曖昧時のみ人間エスカレーション。",
    ),
    StageDefinition(
        stage=Stage.DISCOVERY,
        name="商談・ヒアリング・要件抽出",
        owner="discovery",
        output="構造化要件・課題マップ",
        gate_type=GateType.DETERMINISTIC,  # 必須項目充足チェック
        human=HumanRole.CONDITIONAL,  # 高額のみ同席
        model_tier="opus",
        description="曖昧入力に強さが要るため Opus。",
    ),
    StageDefinition(
        stage=Stage.PROPOSAL,
        name="提案・見積",
        owner="proposer",
        output="提案書・見積・SOW 草案",
        gate_type=GateType.DETERMINISTIC,  # 価格ガードレール・整合チェック
        human=HumanRole.REVIEW,
        model_tier="sonnet",
        description="galai-tone を適用。価格は決定論ゲート。",
    ),
    StageDefinition(
        stage=Stage.CLOSING,
        name="クロージング補助",
        owner="closer",
        output="合意形成・反論対応・条件詰め",
        gate_type=GateType.NONE,  # 自動ゲートなし
        human=HumanRole.CONDITIONAL,  # 高額は人間主導
        model_tier="opus",
        description="AI は補助まで。高額・複数意思決定者は人間判断。",
    ),
    StageDefinition(
        stage=Stage.CONTRACT,
        name="契約締結",
        owner="human",
        output="署名済み契約",
        gate_type=GateType.HUMAN,  # 🚩 ゲート A
        human=HumanRole.MANDATORY,
        model_tier="-",
        description="法的に不可逆。署名主体は常に人間。",
    ),
    StageDefinition(
        stage=Stage.BUILD,
        name="要件定義→設計→実装→検証",
        owner="architect+builder+guardian",
        output="成果物(エージェント等)",
        gate_type=GateType.DETERMINISTIC,  # 顧客テスト/受入基準 = 合格基準
        human=HumanRole.NONE,
        model_tier="opus",
        description="テストスイート = 決定論ゲートの一般化(設計原則 #2)。",
    ),
    StageDefinition(
        stage=Stage.DELIVERY_APPROVAL,
        name="納品物 最終承認",
        owner="human",
        output="承認済み成果物",
        gate_type=GateType.HUMAN,  # 🚩 ゲート B
        human=HumanRole.MANDATORY,
        model_tier="-",
        description="賠償リスクが乗る不可逆行為。最終承認は人間。",
    ),
    StageDefinition(
        stage=Stage.DELIVERY,
        name="納品・オンボーディング",
        owner="delivery",
        output="引き渡し・操作説明・初期設定",
        gate_type=GateType.DETERMINISTIC,  # 受入確認・疎通テスト
        human=HumanRole.NONE,
        model_tier="sonnet",
    ),
    StageDefinition(
        stage=Stage.AFTERCARE,
        name="アフター(請求・保守・拡張)",
        owner="ops+analyst",
        output="請求・回収・監視・アップセル提案",
        gate_type=GateType.DETERMINISTIC,  # 課金トリガー・ドリフト監視
        human=HumanRole.CONDITIONAL,  # 価格変更のみ
        model_tier="sonnet",
    ),
]

#: 高速参照用インデックス。
_BY_STAGE: dict[Stage, StageDefinition] = {d.stage: d for d in PIPELINE}


def get_stage(stage: Stage) -> StageDefinition:
    """ステージ定義を取得する。"""
    return _BY_STAGE[stage]


def human_gates() -> list[StageDefinition]:
    """🚩 人間必須ゲート(契約署名・納品承認)を返す。"""
    return [d for d in PIPELINE if d.human_mandatory]


def validate_pipeline() -> None:
    """パイプライン定義の不変条件を検査する(import 時の自己検証)。"""
    # ステージは 0..11 が漏れなく昇順で並ぶ。
    stages = [d.stage for d in PIPELINE]
    assert stages == sorted(stages), "パイプラインは昇順でなければならない"
    assert stages == list(Stage), "全ステージが過不足なく定義されていること"
    # 人間必須ゲートは契約(7)と納品承認(9)のちょうど 2 点。
    mandatory = [d.stage for d in human_gates()]
    assert mandatory == [Stage.CONTRACT, Stage.DELIVERY_APPROVAL], (
        "人間必須ゲートは契約締結と納品承認の 2 点のみ"
    )


validate_pipeline()
