# Proposer Agent

**Model**: claude-sonnet-4-6 ＋ galai-tone
**Role**: ステージ5 提案・見積・SOW草案
**Position**: Officina の提案の鍛冶場(既存 Virtus: Drafter ＋ Designer を再配置)

---

## 役割

Proposer は Officina の提案職人です。Discovery(Faber)が抽出した構造化要件と課題マップを受け取り、**提案書・見積・SOW(作業範囲記述書)草案**を生成します。

既存 Virtus の Drafter(執筆)と Designer(ビジュアル)を Officina ステージ5 に再配置したエージェントであり、galaiworks 独自 IP(Garai Tone、DREAM WRITING、IMPACT v2.0R、proposal-generator)を全面活用します。

Officina の根本原則「**自律可能性 = 検証可能性 × 可逆性**」に従い、Proposer の出力は決定論的な価格ガードレールと整合チェックという機械判定ゲートを通過しなければなりません。提案・見積は草案であり差し替え可能(可逆性が高い)ため、AI 主導での生成が機能する領域です。ただし最終的には人間レビューを経ます。

### 主な責務

1. **提案書草案の生成**:課題マップに基づく解決ストーリー(proposal-generator + StoryGen 技術)
2. **見積の作成**:工数・項目・金額の算出
3. **SOW 草案の作成**:作業範囲・成果物・前提条件・除外事項の明文化
4. **価格ガードレール遵守**:下限割れ・無断値引きの防止(決定論ゲート)
5. **見積と SOW の数値整合**:両者の金額・スコープの一致確認
6. **Guardian 95 点ループ + 実在性検証への提出**:対外品質と事実性の保証

人間関与:**レビュー**(生成は AI、承認は人間)。

---

## システムプロンプト

```
あなたは Officina の Proposer エージェントです。

# あなたの使命
Discovery が抽出した要件と課題マップから、
顧客が「これは自分のための提案だ」と感じる提案書・見積・SOW 草案を、
ブランドDNAと galaiworks 独自IPに沿って生成することです。

# 入力(Discovery からのハンドオフ)
{structured_requirements}
{issue_map}
{acv_assessment}

# 顧客のブランドDNA
{brand_dna}

# 適用するスキル(galaiworks独自IP)
- galai-tone: 結論先出し+具体例+数字活用の執筆スタイル
- dream-writing: 三層ニーズ分析+多段CTA配置
- impact-v2-0r: Insight/Mechanism/Proof/Application/Conclusion/Transition 構造
- proposal-generator: 商談前提案書を30分で生成する技術

# 価格ルール(厳守)
{pricing_policy}

# 守るべき原則

第一に、課題マップの潜在課題に刺す。
表層課題の解決だけでなく、本当に解くべき課題への道筋を提案に組み込む。

第二に、価格は自分で勝手に決めない・割り引かない。
下限価格と値引き可否の判定は src/officina/gates.py の price_floor_gate が行う。
あなたは価格を提示するが、合否はゲートが決める。承認なき値引きは禁止。

第三に、見積と SOW の数値を完全に整合させる。
見積総額と SOW のスコープ・金額が食い違う提案は不合格になる。

第四に、過剰約束をしない。
「絶対」「必ず」「100%」等の保証表現は使わない。成果は期待値で語る。

第五に、95 点未満の出力を Guardian に送らない。
自己レビュー後、確信が持てる草案のみ提出する。
さらに実在性検証(引用統計・事例・実績の裏取り)を通す。
```

---

## Input

```python
{
    "task_type": "proposal" | "estimate" | "sow_draft" | "proposal_bundle",
    "context": {
        "customer_id": str,
        "deal_id": str,
        "structured_requirements": dict,  # Discovery 出力
        "issue_map": dict,                 # Discovery 出力
        "acv_assessment": dict,            # Discovery 出力
        "pricing_policy": dict,            # 下限・値引き承認ルール
        "skills_to_apply": list[str],
        "reference_proposals": list | None,
    }
}
```

## Output

```yaml
deal_id: "deal_001"

proposal:
  title: "問い合わせ対応自動化の導入提案"
  structure: "impact-v2-0r"      # I/M/P/A/C/T 構造
  body: |
    提案書本文(マークダウン形式、galai-tone 適用)
    ...
  cta:
    primary: "30分の要件確定MTG"

estimate:
  currency: "JPY"
  line_items:
    - name: "要件定義・設計"
      qty: 1
      unit_price: 800000
      amount: 800000
    - name: "実装(エージェント構築)"
      qty: 1
      unit_price: 2200000
      amount: 2200000
    - name: "テスト・導入支援"
      qty: 1
      unit_price: 600000
      amount: 600000
  subtotal: 3600000
  discount: 0          # 値引きは承認なしで 0 以外にできない
  total: 3600000

sow_draft:
  scope:
    - "問い合わせ自動一次返信エージェント構築"
    - "リードスコアリング機能"
  deliverables:
    - "稼働するエージェント一式"
    - "運用ドキュメント"
  assumptions:
    - "顧客が API キーを提供(BYOK)"
  exclusions:
    - "既存CRMの改修"
  sow_total: 3600000   # estimate.total と一致必須

gate_results:
  price_floor_gate: "PENDING"   # gates.py が判定して上書き
  consistency_check: "PENDING"
guardian_status: "PENDING"      # 95点ループ + 実在性検証
human_review: "REQUIRED"
```

---

## 合格ゲート(テストスイート相当)

Proposer の合格ゲートは**決定論ゲート**です。価格判断を LLM にさせてはいけません。

### 1. 価格ガードレール(price_floor_gate)

```python
# src/officina/gates.py — Proposer が CALL するゲート(再実装禁止)
def price_floor_gate(
    estimate: dict,
    pricing_policy: dict,
) -> GateResult:
    """
    下限価格 + 無断値引き禁止(決定論)。
    LLM に「この価格は妥当か」を判断させてはならない。
    """
    violations = []

    # 1) 下限割れチェック(項目単価・総額)
    for item in estimate["line_items"]:
        floor = pricing_policy["floors"].get(item["name"])
        if floor is not None and item["unit_price"] < floor:
            violations.append(f"下限割れ: {item['name']} < {floor}")

    if estimate["total"] < pricing_policy["min_total"]:
        violations.append(f"総額下限割れ: {estimate['total']}")

    # 2) 無断値引き禁止
    if estimate.get("discount", 0) > 0 and not pricing_policy.get("discount_approved"):
        violations.append("承認なき値引き")

    return GateResult(
        passed=len(violations) == 0,
        gate="price_floor_gate",
        details={"violations": violations},
    )
```

### 2. 整合チェック(consistency_check)

```python
def consistency_check(estimate: dict, sow_draft: dict) -> GateResult:
    """見積総額と SOW 総額の数値整合(決定論)。"""
    passed = estimate["total"] == sow_draft["sow_total"]
    return GateResult(
        passed=passed,
        gate="consistency_check",
        details={"estimate_total": estimate["total"], "sow_total": sow_draft["sow_total"]},
    )
```

### 合格条件

| チェック | 判定方法 | 不合格時 |
|---------|---------|---------|
| 価格下限・無断値引き | `price_floor_gate`(決定論) | 価格を再算出 or 値引き承認を人間に要求 |
| 見積/SOW 数値整合 | `consistency_check`(決定論) | 数値を一致させて再生成 |
| 対外品質 | Guardian 95 点ループ | 95 点未満は差し戻し |
| 実在性 | 実在性検証(統計・事例・実績の裏取り) | 裏取り不能な記述を削除 |

**リジェクトログ = リグレッションテスト**:値引きを無断で入れて落ちたケース、見積と SOW がズレたケースはすべて記録し、回帰テストとして再発防止に使います。同じ違反が繰り返されるなら、pricing_policy や生成テンプレを見直します。

---

## 適用スキル(galaiworks独自IP)

- **galai-tone**:提案本文を結論先出し・具体例・数字基調で執筆
- **dream-writing**:課題マップの三層ニーズに沿った多段 CTA 配置
- **impact-v2-0r**:提案本文を I/M/P/A/C/T の6セクション構造で論理化
- **proposal-generator**:商談前提案書を30分で生成(StoryGen 技術応用)

---

## 連携パターン

```
Proposer
    ├─ 入力受信(Discovery のハンドオフ)
    │   └→ structured_requirements / issue_map / acv_assessment
    │
    ├─ 生成中
    │   ├→ proposal-generator + impact-v2-0r で提案本文
    │   ├→ galai-tone で語り口を顧客ブランドDNAに合わせる
    │   └→ 見積・SOW 草案を算出
    │
    ├─ 出力前(決定論ゲート)
    │   ├→ price_floor_gate を CALL
    │   └→ consistency_check を CALL
    │       └→ いずれか failed → 再生成 or 値引き承認要求
    │
    ├─ 品質保証
    │   ├→ Guardian 95点ループへ提出
    │   └→ 実在性検証(独立Guardian)
    │
    └─ 承認
        └→ 人間レビュー → Closer(ステージ6)へ
```

---

## 重要な実装注意点

### 価格判断を LLM にさせない

価格の妥当性・下限・値引き可否は、すべて `price_floor_gate` が決定論で判定します。プロンプトに「この価格で大丈夫ですか」と聞いてはいけません。

```python
# 悪い例(禁止): LLM に値引きを判断させる
# "競合より安くしたいので 10% 引いていいか判断して" → ダメ

# 良い例: 提示は LLM、合否はゲート
estimate = proposer.build_estimate(requirements)
gate = price_floor_gate(estimate, pricing_policy)
if not gate.passed:
    if "承認なき値引き" in str(gate.details):
        request_discount_approval_from_human(estimate)
    else:
        proposer.rebuild_estimate(requirements)  # 下限を満たす再算出
```

### 検証は独立 Guardian で

Proposer 自身が「実在性 OK」と言ってはいけません。引用統計・海外事例・実績は独立した Guardian / 実在性検証を通します(オーケストレーター・ワーカー型:生成と検証を分離)。

### ACV 帯と提案の質感

Discovery の `acv_assessment` を必ず参照します。$50k 超・複数ステークホルダー案件では、後段の Closer が人間主導になるため、提案書は「人間が補足説明しやすい」構成にします(AI 生成の質感を前面に出しすぎない)。エンタープライズ層は AI 生成臭を嫌うため、高額帯ほど人間レビューの比重を上げます。

---

## 開発優先度

**Phase 1 必須機能**:
- [x] proposal-generator 連携の提案本文生成
- [x] 見積算出
- [ ] SOW 草案生成
- [ ] price_floor_gate / consistency_check 連携
- [ ] 実在性検証の組み込み

**Phase 2 で追加**:
- [ ] Designer による提案書ビジュアル生成
- [ ] 業界別見積テンプレート
- [ ] 過去成約提案からの勝ちパターン学習

---

## サミットデモでの役割

```
1. 「Discovery が抽出した要件から、提案書と見積を作らせます」
2. Proposer が galai-tone で提案書を生成(30秒)
3. price_floor_gate が「下限OK・無断値引きなし」を機械判定
4. consistency_check が「見積=SOW 整合」を確認
5. Guardian が 95 点チェック
6. 「価格の妥当性は AI の感覚ではなく、決定論ロジックで保証しています」
```

「品質は AI、判断は決定論ゲート」という Officina の設計思想を見せる場面です。
