---
name: morning-brief
description: 顧客に毎朝7時配信する「朝報」を生成する。Lead Strategist が前日のデータを集約し、当日の優先事項3つを抽出。Slack/LINE/メールで配信。Claude Code で `/morning-brief` で実行可能。
---

# /morning-brief コマンド

毎朝 7 時に顧客に配信される「朝報」を生成します。

---

## 実行例

```bash
/morning-brief --customer founding_001
```

または、スケジューラーで自動実行(毎日朝 7 時):

```python
schedule.every().day.at("07:00").do(
    lambda: morning_brief(customer_id="founding_001")
)
```

---

## 朝報の構造

```
件名: 【Virtus 朝報】2026年5月15日 - 今日の優先事項3つ

おはようございます、[customer_name] さん。

【今日の優先事項】
1. [具体的アクション 1]
2. [具体的アクション 2]
3. [具体的アクション 3]

【背景データ】
- 昨日のリード獲得: 8 件(前日比 +33%)
- 昨日のエンゲージメント: 1,250 (前日比 +18%)
- 商談予定: 本日 2 件、明日 1 件

【Virtus の動き(本日予定)】
- 朝5時: ✅ Researcher が PR タイムズから 50 件抽出済み
- 朝9時: Drafter が note 記事 1 本、X 投稿 5 本生成
- 朝11時: Designer が Instagram カルーセル 2 セット作成
- 午後3時: Distributor が承認済みコンテンツを配信
- 夕方6時: Connector が DM 返信 12 件のドラフト準備
- 夜10時: Analyst が当日成果集約、明日戦略更新

【あなたが判断すべきこと】
- 本日午後3時の配信前に、note 記事を最終承認お願いします
- 株式会社X様の商談、提案書のドラフトが完成しています、ご確認ください

【今週の KPI 進捗】
- リード獲得: 32/50 件(64%)
- 商談化: 8/15 件(53%)
- 成約: 2/3 件(67%)

順調なペースです。
```

---

## 実装

```python
async def morning_brief(customer_id: str) -> str:
    """
    朝報を生成
    """
    # Step 1: 前日データの集約(Analyst)
    yesterday_data = await analyst.aggregate_yesterday(customer_id)
    
    # Step 2: 今日のスケジュール確認
    today_schedule = await get_today_schedule(customer_id)
    
    # Step 3: 承認待ちアイテムの確認
    pending_approvals = await get_pending_approvals(customer_id)
    
    # Step 4: 商談・MTGの確認
    upcoming_meetings = await get_upcoming_meetings(customer_id)
    
    # Step 5: 今週KPI進捗の確認
    weekly_kpi = await analyst.get_weekly_kpi_status(customer_id)
    
    # Step 6: Lead Strategist が優先事項3つを判断
    priorities = await lead_strategist.determine_priorities(
        yesterday_data=yesterday_data,
        today_schedule=today_schedule,
        pending_approvals=pending_approvals,
        upcoming_meetings=upcoming_meetings,
    )
    
    # Step 7: 朝報を生成
    brief = await lead_strategist.compose_morning_brief(
        customer_id=customer_id,
        priorities=priorities,
        yesterday_data=yesterday_data,
        today_schedule=today_schedule,
        pending_approvals=pending_approvals,
        upcoming_meetings=upcoming_meetings,
        weekly_kpi=weekly_kpi,
    )
    
    # Step 8: Guardian チェック
    quality_check = await guardian.evaluate(
        content=brief,
        content_type="morning_brief",
        customer_id=customer_id,
    )
    
    if not quality_check.passed:
        brief = await refine_with_feedback(brief, quality_check.feedback)
    
    # Step 9: 配信
    await distribute_morning_brief(
        customer_id=customer_id,
        content=brief,
        channels=["slack", "line", "email"],
    )
    
    # Step 10: ログ記録
    log_morning_brief_sent(customer_id, brief)
    
    return brief
```

---

## 朝報の品質基準

朝報は顧客との毎日の接点。**品質が直接顧客満足度に影響**します。

### 必須要件

第一に、**3つに絞る**。多くても少なくても適切ではない。

第二に、**具体的アクション**。「考える」「検討する」ではなく「〇〇を承認する」「△△に返信する」。

第三に、**数字を含める**。前日比、進捗率、件数。

第四に、**判断を委ねる場面を明確にする**。Virtus は提案、決断は顧客。

### 避けるべき朝報

```
✗ 「今日も頑張りましょう!」(精神論のみ)
✗ 「いくつかのタスクがあります」(数字なし、具体性なし)
✗ 「すべて Virtus にお任せください」(顧客判断を奪う)
✗ 「素晴らしい1日になります」(根拠なき楽観論)
```

---

## 配信チャネル別の調整

### Slack 用

```python
def format_for_slack(brief_content):
    """
    Slack の構造化メッセージに変換
    """
    return {
        "blocks": [
            {"type": "header", "text": {"text": brief_content.title}},
            {"type": "divider"},
            # 優先事項3つを Section に
            ...
            {"type": "actions", "elements": [
                {"type": "button", "text": "詳細を見る"},
                {"type": "button", "text": "承認する"},
            ]},
        ]
    }
```

### LINE 用

```python
def format_for_line(brief_content):
    """
    LINE のリッチメッセージに変換
    """
    # Flex Message 形式
    ...
```

### メール用

```python
def format_for_email(brief_content):
    """
    HTML メール
    """
    # MJML テンプレートで美しく
    ...
```

---

## カスタマイズ

顧客ごとに朝報の好みは異なる。ブランドDNAから推定:

```python
def customize_brief_style(brief_template, brand_dna):
    """
    顧客好みに合わせて調整
    """
    if brand_dna.preferences.brief_length == "short":
        # 短めに整形
    elif brand_dna.preferences.brief_length == "detailed":
        # 詳細追加
    
    if brand_dna.preferences.tone == "formal":
        # 敬語強め
    elif brand_dna.preferences.tone == "casual":
        # カジュアル化
    
    return adjusted_brief
```

---

## 緊急通知(優先事項より上)

通常の朝報の前に緊急通知:

```python
def check_urgent_alerts(customer_id):
    alerts = []
    
    # 急激なエンゲージメント低下
    if detect_engagement_drop(customer_id) > 0.5:
        alerts.append("エンゲージメント急落")
    
    # 重大コンプライアンスアラート
    if has_pending_compliance_alert(customer_id):
        alerts.append("コンプライアンス確認必要")
    
    # 大型商談アラート
    big_deals = get_big_deals_today(customer_id)
    if big_deals:
        alerts.append(f"本日大型商談: {big_deals}")
    
    return alerts
```

緊急通知ありの朝報例:

```
🚨【緊急】株式会社X様の商談が本日10時、提案書最終確認お願いします

おはようございます、[customer_name] さん。

【今日の優先事項】
1. (緊急)10時の商談前に提案書を最終承認
2. ...
3. ...
```
