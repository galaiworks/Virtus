# Escalation Rules - エスカレーション基準

このファイルは、Virtus がいつ人間の判断を仰ぐべきかを定義します。

---

## 基本原則

第一に、**疑わしきは人間に委ねる**。Virtus は提案、決断は人間。

第二に、**重大リスクは即時通知**。見過ごせば事業に影響する事項を確実にエスカレーション。

第三に、**通知頻度を最適化**。すべてエスカレーションすると顧客が疲弊する。

第四に、**通知チャネルを使い分ける**。緊急度に応じて Slack/LINE/メール/SMS。

---

## エスカレーション分類

### Level 1: 通常承認(エスカレーションではない)

```yaml
description: 日常の出力を顧客が承認するキュー
examples:
  - 通常の note 記事
  - 通常の SNS 投稿
  - 通常の DM 返信
  
notification: Slack(まとめて1日2回)
response_required: 24時間以内
```

### Level 2: 注意承認(優先確認推奨)

```yaml
description: 通常より慎重な確認が必要
examples:
  - 営業メール(初回アプローチ)
  - 提案書ドラフト
  - 法令ぎりぎりの表現
  - 競合言及のあるコンテンツ
  
notification: Slack(個別通知)
response_required: 24時間以内
```

### Level 3: 緊急判断(優先対応必要)

```yaml
description: 早めの判断が必要
examples:
  - 大型商談の提案書
  - 重要顧客からのクレーム返信
  - 法令違反の疑いがあるコンテンツ
  - Guardian が95点ループで3回失敗
  
notification: Slack + LINE
response_required: 4時間以内
```

### Level 4: 緊急対応(即時対応必須)

```yaml
description: 今すぐ判断必要
examples:
  - 重大法令違反検出
  - 個人情報漏洩の疑い
  - プラットフォームBANリスク
  - 詐欺・なりすまし対応
  
notification: Slack + LINE + メール + SMS
response_required: 1時間以内
```

---

## エスカレーション判断ロジック

### Researcher のエスカレーション

```python
def researcher_escalation_check(research_result):
    triggers = []
    
    # 異常なリードスコア
    if any(lead.score > 95 for lead in research_result.leads):
        triggers.append({
            "level": 2,
            "reason": "極めて高スコアのリード検出、優先対応推奨",
            "details": ...,
        })
    
    # 競合の重大動向
    if detected_major_competitor_event(research_result):
        triggers.append({
            "level": 3,
            "reason": "競合の重大動向検出",
            "details": ...,
        })
    
    # 業界の重大変化
    if detected_industry_disruption(research_result):
        triggers.append({
            "level": 3,
            "reason": "業界の重大変化",
            "details": ...,
        })
    
    return triggers
```

### Drafter のエスカレーション

```python
def drafter_escalation_check(content, quality_check):
    triggers = []
    
    # Guardian で3回連続95点未到達
    if quality_check.retry_count >= 3:
        triggers.append({
            "level": 3,
            "reason": "Drafter 3回再試行でも品質未達",
            "details": quality_check.history,
        })
    
    # 過剰約束の繰り返し
    if quality_check.overpromise_attempts >= 3:
        triggers.append({
            "level": 2,
            "reason": "過剰約束の繰り返し、ブランドDNA見直し必要",
            "details": ...,
        })
    
    return triggers
```

### Connector のエスカレーション

```python
ESCALATION_KEYWORDS = {
    "level_2": [
        "検討します",
        "後ほど",
        "他社も見ています",
    ],
    "level_3": [
        "クレーム",
        "返金",
        "解約したい",
        "問題があります",
    ],
    "level_4": [
        "弁護士",
        "訴訟",
        "報道",
        "詐欺",
        "個人情報",
    ],
}

def connector_escalation_check(incoming_message):
    triggers = []
    
    for level, keywords in ESCALATION_KEYWORDS.items():
        if any(kw in incoming_message.text for kw in keywords):
            triggers.append({
                "level": int(level.split("_")[1]),
                "reason": f"危険ワード検出",
                "details": incoming_message,
            })
    
    # 感情分析
    sentiment = analyze_sentiment(incoming_message)
    if sentiment.anger > 0.7:
        triggers.append({
            "level": 3,
            "reason": "強い怒り感情を検出",
            "details": sentiment,
        })
    
    return triggers
```

### Distributor のエスカレーション

```python
def distributor_escalation_check(distribution_result):
    triggers = []
    
    # API エラー連発
    if distribution_result.consecutive_errors >= 5:
        triggers.append({
            "level": 4,
            "reason": "API エラー連発、プラットフォーム異常の可能性",
            "details": ...,
        })
    
    # レート制限超過
    if distribution_result.rate_limited:
        triggers.append({
            "level": 3,
            "reason": "プラットフォームレート制限超過",
            "details": ...,
        })
    
    # 配信失敗の累積
    if distribution_result.failure_rate_today > 0.2:
        triggers.append({
            "level": 3,
            "reason": "配信失敗率20%超",
            "details": ...,
        })
    
    return triggers
```

### Guardian のエスカレーション

```python
def guardian_escalation_check(evaluation):
    triggers = []
    
    # 重大違反検出
    if evaluation.has_critical_violation():
        triggers.append({
            "level": 4,
            "reason": "重大法令違反検出",
            "details": evaluation.violations,
        })
    
    # 95点ループで3回失敗
    if evaluation.retry_count >= 3:
        triggers.append({
            "level": 3,
            "reason": "95点ループ3回失敗",
            "details": evaluation.history,
        })
    
    # 自己反省で却下
    if evaluation.self_reflection_rejected:
        triggers.append({
            "level": 2,
            "reason": "Guardian の自己反省で却下、人間判断推奨",
            "details": evaluation,
        })
    
    return triggers
```

---

## 通知フォーマット

### Slack 通知例(Level 3)

```
🟡 [Virtus] 緊急判断依頼: 株式会社X様への提案書

理由: 大型商談(契約規模 500 万円以上)

提案書ドラフト: https://drive.google.com/...
推奨される対応: 4時間以内に確認・承認

------
[ 承認 ] [ 修正依頼 ] [ 詳細を見る ]
```

### LINE 通知例(Level 4)

```
🔴 【緊急】Virtus からの即時対応要請

▼内容
Connector が、〇〇様からのメッセージで「弁護士」のキーワードを検出しました。

▼推奨対応
即時(1時間以内)に内容確認をお願いします。

▼確認方法
Slack: #virtus-alerts チャンネル
ダッシュボード: https://...
```

---

## エスカレーション後のフロー

```
人間が確認
    ├─ 承認 → 処理続行
    │
    ├─ 修正指示 → エージェントに差し戻し
    │
    ├─ 却下 → アーカイブ、学習データに反映
    │
    └─ エスカレーション拡大 → 専門家相談(弁護士、税理士等)
```

---

## ログ・監査

すべてのエスカレーションは記録:

```yaml
escalation_log:
  timestamp: "2026-05-15T14:23:45+09:00"
  customer_id: "founding_001"
  level: 3
  trigger_agent: "Connector"
  reason: "強い怒り感情を検出"
  details: { ... }
  notification_channels: ["slack", "line"]
  
  human_response:
    response_time: "00:42:15"  # 42分後に対応
    decision: "human_handled"
    notes: "顧客と直接対話、解決済み"
  
  learning:
    pattern_recognized: true
    brand_dna_update: false
    skill_update: true
```

---

## 改善ループ

月次で:
- エスカレーション頻度の分析
- 同じパターンの繰り返しがないかチェック
- スキル・ブランドDNAの更新でエスカレーション削減

```python
def monthly_escalation_review(customer_id, month):
    escalations = get_escalations(customer_id, month)
    
    # パターン分析
    patterns = analyze_escalation_patterns(escalations)
    
    # 自動化可能なものを抽出
    automatable = identify_automatable_patterns(patterns)
    
    # スキル更新提案
    skill_updates = propose_skill_updates(automatable)
    
    # ブランドDNA更新提案
    dna_updates = propose_dna_updates(patterns)
    
    return {
        "patterns": patterns,
        "skill_updates": skill_updates,
        "dna_updates": dna_updates,
    }
```

これにより、Virtus は使うほど顧客に最適化され、エスカレーション頻度が減っていきます。
