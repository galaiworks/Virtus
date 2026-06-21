# Deterministic Gates - 決定論ゲート(LLM に判断させない第1層)

このファイルは Officina(自律型 AI エージェンシー OS)のガバナンス第1層
「決定論ゲート」の詳細仕様です。

送信量上限・契約トリガー・課金・本番デプロイ・価格下限・権限スコープといった
**事業の生死に直結する判断は、絶対に LLM に委ねない**。
これらは `src/officina/gates.py` に if/then のハードロジックとして実装され、
モデルの解釈ではなく、機械的に強制されます。

---

## なぜ LLM に判断させてはいけないのか

第一に、**モデルは確率的に上限を破る**。
LLM は「だいたい守る」ことはできても「必ず守る」ことはできない。
温度・文脈・プロンプト注入により、1,000 回に数回は日次送信上限を超える判断を下す。
1 回の超過がドメイン評価を破壊し、事業全体を止める。確率的遵守は遵守ではない。

第二に、**モデルは値引きを「正当化」する**。
「この顧客は重要だから」「競合が安いから」と、価格下限を割る理由を流暢に生成する。
説得力ある言い訳は、ガバナンスにおいては最も危険な能力である。

第三に、**モデルは不可逆な行為のトリガーを幻覚する**。
「契約は締結済みと判断しました」と、署名イベントが存在しないのに課金を発火しうる。
契約・課金・本番デプロイは、事実(署名・テスト結果)の有無で機械的に決める。

第四に、**監査できない判断は存在しないのと同じ**。
LLM の内部判断は再現不能。決定論ゲートは入力と閾値が固定で、後から完全に再現・監査できる。

結論:**「判断の柔らかさ」が価値を生む領域(文章・戦略・対話)は LLM に。
「逸脱が許されない領域」(量・金・不可逆・権限)は決定論ゲートに。** この線引きを揺るがさない。

---

## GateResult の共通形式

すべてのゲートは以下の構造を返します。

```python
from dataclasses import dataclass

@dataclass
class GateResult:
    allowed: bool      # True=許可, False=ブロック
    reason: str        # 判断理由(ログ・通知に使用)
    severity: str      # "info" | "warning" | "block" | "critical"
    # block/critical の場合、呼び出し側は処理を必ず停止する
```

共通原則:

第一に、**ゲートはデフォルト deny**。判断不能・入力欠損時は `allowed=False`。

第二に、**ゲートは副作用を持たない**。検査だけを行い、送信・課金等の実行はしない。

第三に、**全ゲート呼び出しを監査ログに記録**(後述のログ要件)。

第四に、**ゲートは LLM を呼ばない**。純粋な if/then と数値比較のみ。

---

## 1. deliverability_gate(到達性ゲート)

到達性メトリクスを検査し、危険水準なら送信をブロックする。
詳細な到達性戦略は `deliverability.md` を参照。

### 入力

```yaml
metrics:
  bounce_rate: float            # 直近の総バウンス率(0.0-1.0)
  hard_bounce_rate: float       # ハードバウンス率
  spam_complaint_rate: float    # スパム苦情率(0.0-1.0)
  domain_reputation: str        # "high" | "medium" | "low" | "blacklisted"
  warmup_stage: int             # ウォームアップ段階(0=未開始 〜 N=完了)
  open_rate_7d: float           # 直近7日開封率(健全性の補助指標)
```

### 閾値の例

```python
DELIVERABILITY_THRESHOLDS = {
    "hard_bounce_rate_max": 0.02,        # 2% 超で即ブロック
    "bounce_rate_max": 0.05,             # 5% 超で即ブロック
    "spam_complaint_rate_max": 0.001,    # 0.1% 超で即ブロック(Gmail/Yahoo 基準)
    "spam_complaint_rate_warn": 0.0005,  # 0.05% 超で警告
    "min_reputation": "medium",          # low/blacklisted はブロック
}
```

### ロジック

```python
def deliverability_gate(metrics) -> GateResult:
    """到達性が危険水準なら送信をブロックする(決定論)。"""
    t = DELIVERABILITY_THRESHOLDS

    if metrics.domain_reputation == "blacklisted":
        return GateResult(False, "ドメインがブラックリスト入り", "critical")

    if metrics.hard_bounce_rate > t["hard_bounce_rate_max"]:
        return GateResult(
            False,
            f"ハードバウンス率 {metrics.hard_bounce_rate:.2%} > 2%",
            "block",
        )

    if metrics.spam_complaint_rate > t["spam_complaint_rate_max"]:
        return GateResult(
            False,
            f"スパム苦情率 {metrics.spam_complaint_rate:.3%} > 0.1%",
            "critical",  # 苦情率超過は最優先(deliverability.md の撤退トリガー)
        )

    if metrics.bounce_rate > t["bounce_rate_max"]:
        return GateResult(False, f"バウンス率 {metrics.bounce_rate:.2%} > 5%", "block")

    if metrics.domain_reputation == "low":
        return GateResult(False, "ドメイン評価 low、送信停止して監査", "block")

    if metrics.spam_complaint_rate > t["spam_complaint_rate_warn"]:
        # 送信は許可するが警告ログ + 監視強化
        return GateResult(True, "スパム苦情率が警告水準、監視強化", "warning")

    return GateResult(True, "到達性は健全", "info")
```

### ブロック時の挙動

- 当該ドメイン/アカウントからの**全アウトリーチを即時停止**。
- `critical` の場合、Outreach エージェントのキューを凍結し人間にエスカレーション(`escalation.md` Level 4 相当)。
- アウトリーチ監査を自動起動(直近送信リスト・リスト取得元・文面を点検)。

---

## 2. send_volume_gate(送信量ゲート)

日次・ドメイン別・アカウント別の送信上限とウォームアップ曲線を強制する。

### 入力

```yaml
account_state:
  account_id: str
  domain: str
  warmup_day: int               # ウォームアップ開始からの経過日数
  sent_today_account: int       # 当該アカウントの本日送信済み数
  sent_today_domain: int        # 当該ドメインの本日送信済み数(全アカウント合算)
requested: int                  # これから送りたい件数
```

### 閾値の例(ウォームアップ曲線)

```python
# ウォームアップ曲線: 日次の許容送信数(アカウント単位)
WARMUP_CURVE = {
    1: 20, 2: 30, 3: 40, 5: 60, 7: 100,
    14: 200, 21: 350, 30: 500,    # 30日で定常 500/日/アカウント
}
DOMAIN_DAILY_CAP = 2000           # ドメイン単位の日次上限
ACCOUNT_STEADY_CAP = 500          # ウォームアップ完了後のアカウント上限

def warmup_cap(day: int) -> int:
    """その日の送信上限を曲線から線形補間で求める。"""
    if day >= 30:
        return ACCOUNT_STEADY_CAP
    keys = sorted(WARMUP_CURVE)
    lo = max(k for k in keys if k <= day)
    return WARMUP_CURVE[lo]
```

### ロジック

```python
def send_volume_gate(account_state, requested) -> GateResult:
    """日次/ドメイン/アカウント上限とウォームアップ曲線を強制する。"""
    acc_cap = warmup_cap(account_state.warmup_day)

    acc_remaining = acc_cap - account_state.sent_today_account
    dom_remaining = DOMAIN_DAILY_CAP - account_state.sent_today_domain

    if acc_remaining <= 0:
        return GateResult(
            False,
            f"アカウント日次上限 {acc_cap} 到達(warmup_day={account_state.warmup_day})",
            "block",
        )

    if dom_remaining <= 0:
        return GateResult(False, f"ドメイン日次上限 {DOMAIN_DAILY_CAP} 到達", "block")

    allowed_count = min(requested, acc_remaining, dom_remaining)
    if allowed_count < requested:
        # 超過分はブロック。許可分のみ通す(部分許可)。
        return GateResult(
            False,  # 要求全量は通らない → 呼び出し側は allowed_count だけ送る
            f"要求 {requested} 件中 {allowed_count} 件のみ送信可(超過分ブロック)",
            "warning",
        )

    return GateResult(True, f"{requested} 件 送信可", "info")
```

### ブロック時の挙動

- 超過分は送信せず、翌日のキューへ自動繰越。
- ウォームアップ違反(曲線を飛ばす要求)は `block` とし、Outreach エージェントに差し戻し。
- 上限到達はログに記録、頻発する場合はアカウント追加の運用提案。

---

## 3. price_floor_gate(価格下限ゲート)

見積が価格下限を下回る、または承認なしの値引きがある場合にブロックする。
値引きの「正当化」を LLM に許さないための決定論ゲート。

### 入力

```yaml
quote:
  service_code: str             # 提供サービスの識別子
  list_price: int               # 定価(円)
  quoted_price: int             # 提示価格(円)
  discount_rate: float          # 値引き率(0.0-1.0)
  discount_approved_by: str | None  # 値引き承認者(人間の ID)。None=未承認
```

### 閾値の例

```python
PRICE_FLOORS = {
    "consulting_basic": 300_000,
    "build_mvp": 1_500_000,
    "retainer_monthly": 200_000,
}
MAX_AUTO_DISCOUNT = 0.10   # 10% までは自動許容、超過は人間承認必須
```

### ロジック

```python
def price_floor_gate(quote) -> GateResult:
    """価格下限割れ・無承認値引きをブロックする(決定論)。"""
    floor = PRICE_FLOORS.get(quote.service_code)
    if floor is None:
        return GateResult(False, f"未登録サービス {quote.service_code}", "block")

    if quote.quoted_price < floor:
        return GateResult(
            False,
            f"提示価格 {quote.quoted_price:,}円 < 下限 {floor:,}円",
            "block",
        )

    if quote.discount_rate > MAX_AUTO_DISCOUNT and not quote.discount_approved_by:
        return GateResult(
            False,
            f"値引き {quote.discount_rate:.0%} > 自動許容 10%、人間承認なし",
            "block",
        )

    return GateResult(True, "価格は下限以上・値引きは許容範囲", "info")
```

### ブロック時の挙動

- 見積の送付・提案書への価格反映をブロック。
- 下限割れ/承認なし値引きは Proposer に差し戻し、人間承認待ちキューへ(`escalation.md` Level 2-3)。
- 「なぜ下限を割ったか」の LLM 説明は**記録するが判断材料にしない**。

---

## 4. contract_trigger_gate(契約トリガーゲート)

契約締結は、**人間の署名イベントが事実として確認された場合のみ** true。
AI は契約を発火させられない(`human-gates.md` ゲートA と対応)。

### 入力

```yaml
event:
  contract_id: str
  signature_provider: str       # "stripe" | "docusign" | "cloudsign" 等
  signature_event_id: str | None   # プロバイダ発行の署名完了イベント ID
  signature_verified: bool      # Webhook 署名検証を通過したか
  signer_is_human: bool         # 署名主体が人間(ガライ)であるか
```

### ロジック

```python
def contract_trigger_gate(event) -> GateResult:
    """署名イベントの事実確認のみで契約成立を判定する(AI 発火不可)。"""
    if not event.signature_event_id:
        return GateResult(False, "署名イベントが存在しない", "block")

    if not event.signature_verified:
        return GateResult(False, "Webhook 署名検証に失敗(偽装の疑い)", "critical")

    if not event.signer_is_human:
        return GateResult(False, "署名主体が人間でない、契約成立不可", "critical")

    return GateResult(True, f"署名確認済み({event.signature_provider})", "info")
```

### ブロック時の挙動

- 契約 state を `signed` に遷移させない。後続の課金(`billing_gate`)も連鎖的に不許可。
- `critical`(検証失敗・非人間署名)は即時人間エスカレーション(Level 4)。

---

## 5. billing_gate(課金ゲート)

課金は、`contract_trigger_gate` を満たした契約に紐づく場合のみ実行を許可する。

### 入力

```yaml
contract_state:
  contract_id: str
  status: str                   # "draft"|"signed"|"active"|"void"
  contract_trigger_passed: bool # contract_trigger_gate の結果
  billing_amount: int           # 請求額(円)
  billing_schedule_id: str      # 請求スケジュールの識別子
  already_billed: bool          # 二重課金防止フラグ
```

### ロジック

```python
def billing_gate(contract_state) -> GateResult:
    """契約成立を前提とした課金のみ許可する(決定論)。"""
    if not contract_state.contract_trigger_passed:
        return GateResult(False, "契約トリガー未達、課金不可", "block")

    if contract_state.status not in ("signed", "active"):
        return GateResult(
            False, f"契約 status={contract_state.status} は課金不可", "block"
        )

    if contract_state.already_billed:
        return GateResult(False, "二重課金防止: 既に課金済み", "block")

    if contract_state.billing_amount <= 0:
        return GateResult(False, "請求額が不正(0以下)", "block")

    return GateResult(True, f"課金可 {contract_state.billing_amount:,}円", "info")
```

### ブロック時の挙動

- 決済 API を一切呼ばない。
- 二重課金検出・契約未成立課金は `critical` 級として記録、人間に通知。

---

## 6. prod_deploy_gate(本番デプロイゲート)

全テスト通過 **かつ** Guardian 合格の両方が満たされた場合のみ本番デプロイを許可する。

### 入力

```yaml
test_results:
  all_passed: bool
  total: int
  failed: int
  coverage: float               # 0.0-1.0
guardian_verdict:
  verdict: str                  # "APPROVED" | "REJECTED" | "ESCALATED"
  score: int                    # 0-100(quality-95.md の総合点)
```

### ロジック

```python
def prod_deploy_gate(test_results, guardian_verdict) -> GateResult:
    """テスト全通過 AND Guardian 合格 でのみ本番デプロイを許可する。"""
    if not test_results.all_passed or test_results.failed > 0:
        return GateResult(
            False,
            f"テスト未通過({test_results.failed}/{test_results.total} 失敗)",
            "block",
        )

    if test_results.coverage < 0.80:
        return GateResult(False, f"カバレッジ {test_results.coverage:.0%} < 80%", "block")

    if guardian_verdict.verdict != "APPROVED" or guardian_verdict.score < 95:
        return GateResult(
            False,
            f"Guardian 不合格(verdict={guardian_verdict.verdict}, "
            f"score={guardian_verdict.score})",
            "block",
        )

    return GateResult(True, "テスト全通過 + Guardian 合格、デプロイ可", "info")
```

### ブロック時の挙動

- デプロイパイプラインを停止。Builder に差し戻し。
- ステージング環境への反映は許可するが、本番反映は両条件成立まで不可。

---

## 7. permission_scope_gate(権限スコープゲート)

ゼロトラスト最小権限。各エージェントは許可されたアクションしか実行できない。
許可スコープ外はブロックする。

### 権限マトリクスの例

```python
# agent -> 許可アクションの集合(これ以外はすべて拒否)
PERMISSION_MATRIX = {
    "Researcher":  {"web.read", "crm.read"},
    "Qualifier":   {"crm.read", "crm.write_lead_score"},
    "Proposer":    {"crm.read", "doc.draft", "quote.draft"},
    "Outreach":    {"email.send", "crm.read"},          # 送信のみ。リスト改変不可
    "Builder":     {"repo.write", "staging.deploy"},    # 本番 DB 書込・本番デプロイ不可
    "Guardian":    {"content.read", "verdict.write"},
    "Closer":      {"crm.read", "contract.draft"},      # 契約は草案まで。署名不可
}

# 明示的に「どのエージェントにも与えない」高リスクアクション(人間専用)
HUMAN_ONLY_ACTIONS = {
    "contract.sign",       # 契約署名(不可逆) -> human-gates.md ゲートA
    "deliverable.release", # 納品物出荷(不可逆) -> human-gates.md ゲートB
    "prod.db.write",       # 本番 DB 直接書込
    "billing.execute",     # 課金実行(billing_gate 経由のみ)
}
```

### ロジック

```python
def permission_scope_gate(agent, action) -> GateResult:
    """エージェントの許可スコープ外のアクションをブロックする(ゼロトラスト)。"""
    if action in HUMAN_ONLY_ACTIONS:
        return GateResult(
            False, f"{action} は人間専用、エージェント実行不可", "critical"
        )

    allowed = PERMISSION_MATRIX.get(agent, set())
    if action not in allowed:
        return GateResult(
            False,
            f"{agent} に {action} の権限なし(許可: {sorted(allowed)})",
            "block",
        )

    return GateResult(True, f"{agent} は {action} を許可", "info")
```

### ブロック時の挙動

- アクションを実行せず即停止。
- `HUMAN_ONLY_ACTIONS` への試行は**権限昇格の試み**として `critical` 記録・人間通知。
- 権限マトリクスはコードで一元管理。LLM のプロンプトでは変更不能。

---

## ログ要件(全ゲート共通)

すべてのゲート呼び出しは、許可・ブロックを問わず記録します。

```yaml
gate_log_entry:
  timestamp: "2026-06-21T10:23:45+09:00"
  gate: "send_volume_gate"
  agent: "Outreach"
  customer_id: "founding_001"
  input_snapshot: { ... }        # 入力の完全スナップショット(再現性のため)
  result:
    allowed: false
    reason: "アカウント日次上限 500 到達"
    severity: "block"
  thresholds_version: "gates-2026-06"   # 閾値のバージョン
  downstream_action: "blocked"   # "executed" | "blocked" | "partial"
```

監査原則:

第一に、**入力スナップショットを必ず残す**。後から同じ入力で再現・検証できること。

第二に、**閾値のバージョンを記録**。閾値変更の前後で判断を比較できること。

第三に、**`critical` は即時通知**。`escalation.md` の Level 4 チャネルへ。

第四に、**ゲートログは改竄不能なストレージへ**(追記専用)。法的監査に耐えること。

---

## まとめ:決定論ゲートの不可侵性

これらのゲートは Officina の**憲法**です。

- LLM はゲートを呼び出せるが、ゲートの判断を覆せない。
- ゲートの閾値変更はコードレビュー + 人間承認が必須(プロンプトでは変えられない)。
- 「上限を超えてもいいか」を AI に聞いてはならない。答えは常にコードが持つ。

判断の柔らかさが価値を生む領域は LLM に委ね、
逸脱が事業を殺す領域は決定論ゲートが守る。この境界線を、絶対に揺るがせない。
