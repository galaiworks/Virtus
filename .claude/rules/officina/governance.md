# Officina ガバナンス 3 層 — 設計の憲法

このファイルは Officina の全自律実行が必ず通る 3 層ガバナンスの全体像です。
各層の詳細は個別ファイルを参照してください。

- 第 1 層: [deterministic-gates.md](./deterministic-gates.md)(決定論ゲート)
- 第 1 層補足: [deliverability.md](./deliverability.md)(到達性=事業継続条件)
- 第 3 層: [human-gates.md](./human-gates.md)(人間 HITL ゲート 2 点)
- 品質検証: [../quality-95.md](../quality-95.md)(Guardian 95 点ループを継承)
- パイプライン: [pipeline.md](./pipeline.md)(11 ステージと合格ゲート)

---

## 基本原則(このプロジェクトの憲法)

第一に、**自律可能性 = 検証可能性 × 可逆性**。
機械で安く速く正しさを判定でき、かつ失敗が戻せる工程ほど自律化する。逆は人間ゲートに置く。

第二に、**テストスイート＝決定論的ゲートの一般化**。
Claude Code が無人マージできたのは「顧客のテスト」という機械判定可能な合格基準があったから。各工程に「テストスイート相当の合格基準」を必ず定義する。基準が作れない工程は自律化しない。

第三に、**オーケストレーター・ワーカー型**。
単一巨大プロンプトの "God Model" は禁止。スーパーバイザーが分解・委任し、専門ワーカーが独立コンテキストで実行する。

第四に、**検証は独立エージェントで**。
生成と検証を同一エージェントに兼務させない。発見 → 反証 → 収束(Guardian ＋ 敵対的レビュー)。

第五に、**決定論ゲートは LLM に判断させない**。
送信量上限・契約トリガー・課金・本番デプロイは if/then のハードロジックで強制。モデルの解釈に委ねない。実装は `src/officina/gates.py`。

第六に、**リジェクトログ＝リグレッションテスト**。
人間がゲートで弾いた事例を永続化し、回帰テスト化してドリフトを抑える。

---

## 3 層の構造

```
┌─────────────────────────────────────────────────────────┐
│ 第 1 層: 決定論ゲート(LLM に判断させない)               │
│   src/officina/gates.py のハードロジックが最終判断        │
│   - deliverability_gate / send_volume_gate(到達性・送信量)│
│   - price_floor_gate(価格下限・無断値引き禁止)          │
│   - contract_trigger_gate(契約は人間署名イベントのみ)    │
│   - billing_gate(課金は締結契約に紐づく場合のみ)        │
│   - prod_deploy_gate(全テスト通過 ＋ Guardian 合格)      │
│   - permission_scope_gate(ゼロトラスト最小権限)         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 第 2 層: Guardian 独立検証                                │
│   - 生成物を統合前に合格基準へ照合(顧客テスト/受入基準) │
│   - 発見 → 別エージェントが反証 → 収束まで反復           │
│   - 評価プローブ(faithfulness/completeness/sufficiency)  │
│   - ドリフト監視(launch 時の品質分布をベースライン化)    │
│   - 95 点ループ(quality-95.md を継承)                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 第 3 層: 人間 HITL ゲート(2 点のみ)                     │
│   🚩 ゲート A: 契約締結(署名・不可逆)                   │
│   🚩 ゲート B: 納品物 最終承認(出荷・不可逆)            │
│   ＋ Qualifier/Proposer からの例外エスカレーション       │
└─────────────────────────────────────────────────────────┘
```

---

## 実行時の順序(各ステージ共通)

```python
def run_stage(stage, output, context):
    # 1. ゼロトラスト権限チェック(決定論)
    permission_scope_gate(stage.agent, intended_action).raise_if_blocked()

    # 2. ステージ固有の決定論ゲート(送信量・価格・課金・デプロイ等)
    for gate_name in stage.deterministic_gates:
        result = call_gate(gate_name, context)
        if not result.allowed:
            block_and_log(result)        # LLM で覆さない
            if result.severity == "critical":
                escalate_to_human(result)
            return

    # 3. Guardian 独立検証(生成と分離)
    verdict = guardian.evaluate(output)  # 95 点ループ
    if verdict != "APPROVED":
        return revise_or_escalate(verdict)

    # 4. 人間ゲート(ステージ 7/9 のみ)
    if stage.human is REQUIRED_IRREVERSIBLE:
        return await_human_decision(stage)

    # 5. 合格 → 次ステージへ
    advance(stage)
```

ポイント: **決定論ゲート → Guardian → 人間ゲート の順**。安い・速い・確実な判定を先に置き、人間の時間を最後の不可逆点だけに使う。

---

## なぜこの構造か(失敗からの逆算)

- **撤退の主因は到達不全**(過剰送信でドメイン崩壊)。だから第 1 層に deliverability を最優先で置く。
- **純 AI はクロージングで約 22 ポイント劣後**。だから第 3 層に人間ゲートを残す(ハイブリッドが勝つ)。
- **成否の 80〜90% はデータ・ルーティング・ガードレール**(プロンプトは 10〜20%)。だからガードレール(本ファイル群)を最初に設計する。
- **"作って放置" が最大の死因**(本番 1 体あたり 0.25〜0.5 人月/継続)。だから第 2 層にドリフト監視を常設する。

---

## 監査

すべてのゲート判定(決定論・Guardian・人間)は監査ログに記録する。記録要件は各層のファイルおよび `compliance.md` の監査ログ要件に従う。リジェクトログは Guardian の評価セットに還流させ、回帰テスト化する。
