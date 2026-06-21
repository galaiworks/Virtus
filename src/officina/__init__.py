"""Officina — 自律型 AI エージェンシー OS。

営業リサーチ → アウトリーチ → 商談 → 提案 → クロージング補助 →
【人間】契約締結 → 開発 → 【人間】納品物承認 → 納品 → アフター を、
エージェントチームが自律実行する。人間の接触点は「2 つのゲート」に圧縮される。

設計原則(このパッケージの憲法):

第一に、**自律可能性 = 検証可能性 × 可逆性**。
    機械で安く速く正しさを判定でき、かつ失敗が戻せる工程ほど自律化する。
第二に、**テストスイート＝決定論的ゲートの一般化**。
    各工程に「テストスイート相当の合格基準」を必ず定義する。
第三に、**オーケストレーター・ワーカー型**(単一巨大プロンプト禁止)。
第四に、**検証は独立エージェントで**(生成と検証を兼務させない)。
第五に、**決定論ゲートは LLM に判断させない**。
    送信量上限・契約トリガー・課金・本番デプロイは if/then のハードロジックで強制する。
    その実装が :mod:`officina.gates` である。
第六に、**リジェクトログ＝リグレッションテスト**。
"""

from officina.gates import (
    GateResult,
    GateError,
    billing_gate,
    contract_trigger_gate,
    deliverability_gate,
    permission_scope_gate,
    price_floor_gate,
    prod_deploy_gate,
    send_volume_gate,
)

__all__ = [
    "GateResult",
    "GateError",
    "billing_gate",
    "contract_trigger_gate",
    "deliverability_gate",
    "permission_scope_gate",
    "price_floor_gate",
    "prod_deploy_gate",
    "send_volume_gate",
]

__version__ = "0.2.0"
