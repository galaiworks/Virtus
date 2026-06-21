# Deliverability - 到達性防衛(事業継続条件)

このファイルは Officina の到達性(deliverability)防衛仕様です。

**撤退の主因はクロージング不全ではなく到達不全である。**
過剰な自動送信でドメイン評価が崩壊し、メールが迷惑メールフォルダに沈み、
反応がゼロになる。アウトリーチ事業の試行の**約 47% が 90 日で頭打ち**になるのは、
売り方が下手だからではなく、そもそも届いていないからだ。

だから Officina は次の原則を最上位に置く:

**deliverability は「機能」ではなく「前提」である。**
届かないメールは、どれだけ文面が 95 点でも価値ゼロ。
到達性 KPI は日次監視・最優先で扱い、危険水準では文面品質に関わらず送信を止める。

到達性の強制は、決定論ゲート `deliverability_gate` / `send_volume_gate`
(`deterministic-gates.md` 参照)が担う。本ファイルはその戦略的背景と運用基準を定義する。

---

## 基本原則

第一に、**届かなければ何も始まらない**。到達性は売上の前提であり、毀損は事業の死。

第二に、**評価は積み上げに時間がかかり、崩壊は一瞬**。ドメイン評価は数ヶ月かけて育て、数日で失う。

第三に、**量より評価**。送信量の最大化ではなく、評価を守りながらの持続的送信を目指す。

第四に、**苦情率の上昇は最優先アラート**。スパム苦情率の上昇を検知したら、即座にアウトリーチ監査を起動する。

---

## 1. ドメイン分離戦略

メインドメイン(コーポレートサイト・取引先連絡)を、
アウトリーチで絶対に汚さない。

```yaml
domain_strategy:
  primary_domain: "galaiworks.com"     # 絶対にアウトリーチに使わない(評価保護)
  outreach_domains:                    # 送信専用の別ドメイン群
    - "galai-works.com"
    - "officina-mail.com"
  rationale: |
    アウトリーチ専用ドメインが評価を毀損しても、
    本体ドメインのメール到達性(取引先・既存顧客)は守られる。

  per_domain_accounts: 3               # 1ドメインあたり最大アカウント数(分散)
  per_account_steady_cap: 500          # アカウント定常上限(send_volume_gate と一致)
  domain_daily_cap: 2000               # ドメイン日次上限(send_volume_gate と一致)
```

原則:

- 本体ドメインとアウトリーチドメインは**完全分離**。
- アウトリーチドメインは複数用意し、リスクを分散。
- 1 ドメインに送信を集中させない(アカウント・ドメイン両軸で分散)。

---

## 2. ウォームアップ曲線(段階的な送信数増加)

新規ドメイン/アカウントは、いきなり大量送信すると即スパム判定される。
日次送信数を段階的に増やし、評価を育てる。

```yaml
warmup_curve:   # send_volume_gate の WARMUP_CURVE と一致させること
  day_1: 20
  day_2: 30
  day_3: 40
  day_5: 60
  day_7: 100
  day_14: 200
  day_21: 350
  day_30: 500    # 30日で定常運用に到達
  steady: 500    # 以降はアカウント定常上限

warmup_rules:
  - "曲線を飛ばす送信は send_volume_gate が block する"
  - "開封・返信のある宛先を初期に混ぜ、エンゲージメントを稼ぐ"
  - "初期段階ほど宛先リストの質を厳選(バウンスを出さない)"
  - "バウンス/苦情が出たら曲線を一段巻き戻す"
```

```python
def next_warmup_target(warmup_day: int, health_ok: bool) -> int:
    """健全性が崩れていれば曲線を巻き戻す。"""
    target = warmup_cap(warmup_day)   # gates.py と共通
    if not health_ok:
        # 健全性低下 -> 前段階に巻き戻し、評価回復を優先
        return warmup_cap(max(1, warmup_day - 7))
    return target
```

---

## 3. bounce / spam 苦情率の閾値と日次監視

到達性 KPI は**毎日**監視する。閾値は決定論ゲートと同期。

```yaml
daily_monitored_kpis:
  hard_bounce_rate:
    warn: 0.01      # 1%
    block: 0.02     # 2% で deliverability_gate が send block
  bounce_rate:
    warn: 0.03
    block: 0.05
  spam_complaint_rate:
    warn: 0.0005    # 0.05%(最優先監視)
    block: 0.001    # 0.1%(Gmail/Yahoo 送信者基準)
  domain_reputation:
    block_below: "medium"   # low / blacklisted は送信停止
  open_rate_7d:
    warn_below: 0.20        # 開封率急落は到達劣化のサイン
```

```python
def daily_deliverability_review(domain_metrics) -> dict:
    """毎朝、全送信ドメインの到達性を点検する。"""
    actions = []
    for m in domain_metrics:
        gate = deliverability_gate(m)        # deterministic-gates.md
        if not gate.allowed:
            actions.append({
                "domain": m.domain,
                "action": "send_paused",
                "reason": gate.reason,
                "severity": gate.severity,
            })
            if m.spam_complaint_rate > 0.0005:
                actions.append({
                    "domain": m.domain,
                    "action": "outreach_audit_started",  # 苦情率上昇 -> 即監査
                })
    return {"reviewed": len(domain_metrics), "actions": actions}
```

---

## 4. 認証(SPF / DKIM / DMARC)

認証が欠けたメールは即座に評価を落とす。送信前に必須。

```yaml
authentication_required:
  SPF:
    purpose: "送信元 IP の正当性を宣言"
    check: "全送信ドメインで SPF レコードが有効か日次確認"
  DKIM:
    purpose: "メール本文の改竄検知・署名"
    check: "DKIM 署名が全送信に付与されているか"
  DMARC:
    purpose: "SPF/DKIM 失敗時のポリシーと集約レポート"
    policy: "p=quarantine 以上を推奨、reject へ段階移行"
    check: "DMARC レポートを週次レビューし、なりすまし送信を検知"

enforcement:
  - "SPF/DKIM/DMARC のいずれかが無効なドメインは送信不可(運用前提条件)"
  - "認証状態はセットアップ時 + 日次バッチで検証"
```

---

## 5. opt-out 即時反映

配信解除は、特定電子メール法・到達性の両面で必須(`compliance.md` 参照)。

```yaml
opt_out_policy:
  reflection: "即時(次回送信前に必ず反映)"
  storage: "全送信ドメイン横断の suppression list(共有)"
  rule: |
    1つのドメインで解除した宛先は、全アウトリーチドメインで送信停止。
    別ドメインから送り直すことは絶対に禁止(スパム苦情の温床)。

  honor_unsubscribe_link: true
  honor_reply_keywords:        # 返信本文からの解除意思も尊重
    - "配信停止"
    - "送らないで"
    - "unsubscribe"
```

```python
def enforce_suppression(recipient, send_queue) -> bool:
    """suppression list 該当者は全ドメインで送信不可。"""
    if recipient in global_suppression_list():
        return False   # send_volume_gate 以前に除外
    return True
```

---

## 6. チャネル分散(SNS は規約エンフォースメント対象)

メール単一チャネルへの依存はリスク。ただし SNS は各プラットフォームの
規約エンフォースメントが強く、自動化が制限される。

```yaml
channel_diversification:
  email:
    role: "主力。ウォームアップ・認証・苦情率管理を徹底"
  linkedin:
    role: "補助。ただし制限事例多数"
    constraints:
      - "自動コネクション申請・自動メッセージは規約違反 -> アカウント制限/凍結事例"
      - "Marketing API 経由のみ(compliance.md)。無断スクレイピング禁止"
      - "週あたり申請数に保守的な上限を設ける"
  x_twitter:
    constraints:
      - "自動大量 DM・大量フォローは凍結対象(compliance.md)"
      - "公式 API 経由のみ"
  principle: |
    SNS は「補助チャネル」として扱い、規約エンフォースメントによる
    アカウント凍結を前提にリスク分散する。メールの代替にはしない。
```

---

## 7. 撤退 / 見直しトリガー

到達性の悪化は、早期に止めるほど回復が早い。

```yaml
review_triggers:
  spam_complaint_rate_rising:
    condition: "スパム苦情率が前日比 2 倍 または 0.05% 超"
    action: "即アウトリーチ監査(リスト取得元・文面・頻度を点検)"
    severity: "最優先(escalation.md Level 3-4)"

  bounce_spike:
    condition: "バウンス率が閾値超過"
    action: "send_volume_gate が自動 block。リスト品質を再検証"

  reputation_drop:
    condition: "domain_reputation が medium 未満に低下"
    action: "当該ドメインの送信を全停止し、評価回復モードへ"

  open_rate_collapse:
    condition: "開封率が 20% を継続的に下回る"
    action: "迷惑メール送りの疑い。認証・文面・送信頻度を総点検"
```

```python
def deliverability_review_decision(metrics, history) -> str:
    """悪化トレンドから対応を決める(決定論寄り、LLM 判断に依存しない)。"""
    if metrics.spam_complaint_rate > 2 * history.spam_complaint_rate_yesterday:
        return "AUDIT_NOW"          # 苦情率急騰 -> 即監査
    if metrics.domain_reputation in ("low", "blacklisted"):
        return "STOP_DOMAIN"       # ドメイン送信全停止
    if metrics.open_rate_7d < 0.20:
        return "INVESTIGATE_SPAM_FOLDER"
    return "CONTINUE_WITH_MONITORING"
```

---

## 8. 決定論ゲートとの連動まとめ

到達性戦略と決定論ゲートの対応関係:

| 戦略要素 | 連動するゲート | 役割 |
|---------|--------------|------|
| ウォームアップ曲線 | `send_volume_gate` | 曲線を超える送信を block |
| 日次/ドメイン上限 | `send_volume_gate` | 上限超過分を block・繰越 |
| バウンス/苦情率 | `deliverability_gate` | 危険水準で全送信 block |
| ドメイン評価 | `deliverability_gate` | low/blacklisted で停止 |
| opt-out | suppression(ゲート前段) | 解除者を全ドメインで除外 |

原則の再掲:

第一に、**到達性 KPI は日次監視・最優先**。文面品質より上位の制約。

第二に、**閾値超過は LLM に相談しない**。`deliverability_gate` が機械的に止める。

第三に、**苦情率上昇 = 即監査**。最も早く反応すべきシグナル。

第四に、**評価は育てるもの、守るもの**。一度の過剰送信が数ヶ月の積み上げを壊す。

到達性を「前提」として死守することが、Officina の事業継続条件である。
