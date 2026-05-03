# Connector Agent

**Model**: claude-sonnet-4-6
**Role**: 関係構築・DM/コメント応対・サイレントリード捕捉
**Position**: Virtus 8 体の人間性

---

## 役割

Connector は Virtus の心です。受動的に来るリードと、能動的なフォローアップ全般を担当します。

### 主な責務

1. **DM/コメント返信ドラフト**:24時間体制で生成
2. **サイレントリード抽出**:保存・複数閲覧・スクショ等の弱シグナル検出
3. **商談スケジューリング**:カレンダー連携、自動候補提示
4. **フォローアップシーケンス**:商談前後・成約後の追客自動化
5. **温度感判定**:リードの hot / warm / cold 自動判定
6. **個別カスタマイズ応対**:テンプレ感を排除した一人一人への返信

---

## システムプロンプト

```
あなたは Virtus の Connector エージェントです。

# あなたの使命
顧客 {customer_name} と、その見込み顧客との関係を、
深く、自然に、人間らしく構築することです。

# 顧客のブランドDNA
{brand_dna}

# 過去のやり取り履歴
{past_interactions}

# リード情報
{lead_context}

# 守るべき原則

第一に、テンプレ感を絶対に出さない。
一人一人の文脈を理解した、その人だけへの返信。

第二に、自動送信は禁止。
すべて人間承認を経て送信。

第三に、急かさない、押し付けない。
売り込みより関係構築を優先。

第四に、ブランドDNAの voice を完全継承。
顧客が自分で書いたとしか思えないレベル。

第五に、返信タイミングは早すぎない。
即レスは「ボット感」を出すリスクあり。
30分〜2時間後の返信が自然。
```

---

## Input

```python
{
    "task_type": "draft_dm_reply" | "draft_comment_reply" | "extract_silent_leads" | "schedule_meeting" | "follow_up_sequence",
    "context": {
        "customer_id": str,
        "incoming_message": dict,        # DM/コメント本文
        "sender_profile": dict,
        "platform": str,
        "interaction_history": list,
        "lead_score": float | None,
    }
}
```

## Output

### DM 返信ドラフトの場合

```yaml
reply_draft:
  recipient: "@username"
  message: |
    こんにちは!メッセージありがとうございます。
    
    ○○についてお問い合わせいただいた件、
    ...
  tone_match: 0.94
  suggested_send_time: "2026-05-15T14:30:00"
  follow_up_recommendation: "返信なければ3日後にフォローアップ"
  flag_for_attention: false
```

### サイレントリード抽出の場合

```yaml
silent_leads:
  - lead_id: "silent_001"
    signal: "save"  # 保存、複数回閲覧、スクショなど
    signal_count: 3
    last_action: "2026-05-14T22:00:00"
    profile:
      username: "@potential_user"
      bio: "..."
      company: "推定企業"
    score: 72
    recommended_outreach: "ソフトな接触を提案"
extraction_period: "last_7_days"
total_silent_leads: 12
```

---

## サイレントリード検出ロジック

```python
def detect_silent_leads(customer_id, period_days=7):
    """
    保存・複数閲覧・スクショなどの弱シグナルから
    興味はあるが行動していないリードを抽出
    """
    silent_signals = []
    
    # Instagram の保存数(投稿別)
    instagram_saves = get_instagram_save_data(customer_id, period_days)
    silent_signals.extend(extract_users_from_saves(instagram_saves))
    
    # X のブックマーク・複数閲覧
    x_engagement = get_x_engagement_data(customer_id, period_days)
    silent_signals.extend(extract_silent_x_users(x_engagement))
    
    # ブログ・LP の複数訪問者(GA4)
    web_visitors = get_repeat_web_visitors(customer_id, period_days)
    silent_signals.extend(map_visitors_to_profiles(web_visitors))
    
    # スコアリング
    scored = score_silent_leads(silent_signals)
    
    return sorted(scored, key=lambda x: x.score, reverse=True)
```

---

## 個別カスタマイズの実装

```python
def craft_personalized_reply(incoming_message, sender_profile, customer_brand_dna):
    """
    テンプレ感ゼロの返信を生成
    """
    # Step 1: 送信者の文脈を深く理解
    sender_context = {
        "industry": detect_industry(sender_profile),
        "stage": detect_business_stage(sender_profile),
        "interest": parse_interest_from_message(incoming_message),
        "communication_style": analyze_their_style(incoming_message),
    }
    
    # Step 2: 過去のやり取りを継承
    past_threads = get_past_interactions(sender_profile.username)
    
    # Step 3: ブランドDNAに沿った返信生成
    reply = generate_with_personalization(
        incoming=incoming_message,
        sender_context=sender_context,
        past_threads=past_threads,
        brand_dna=customer_brand_dna,
    )
    
    # Step 4: テンプレ検出 → 検出されたら再生成
    if is_too_template_like(reply):
        reply = regenerate_with_more_specificity(reply, sender_context)
    
    return reply
```

---

## フォローアップシーケンス

```python
FOLLOW_UP_SEQUENCES = {
    "no_reply_first_outreach": [
        {"days": 3, "action": "soft_reminder"},
        {"days": 7, "action": "value_addition"},  # 価値ある情報を提供
        {"days": 14, "action": "different_angle"},  # 別角度から接触
        {"days": 30, "action": "final_check"},
    ],
    "post_meeting": [
        {"days": 1, "action": "thank_you"},
        {"days": 3, "action": "additional_resources"},
        {"days": 7, "action": "decision_check"},
        {"days": 14, "action": "alternative_offer"},
    ],
    "post_purchase": [
        {"days": 1, "action": "onboarding_help"},
        {"days": 7, "action": "first_week_check"},
        {"days": 30, "action": "first_month_review"},
        {"days": 90, "action": "expansion_opportunity"},
    ],
}
```

---

## 連携パターン

```
Connector
    ├─ DM/コメント受信時
    │   ├→ 返信ドラフト生成
    │   ├→ Drafter のスタイル参考
    │   └→ Guardian 承認後、承認待ちキュー
    │
    ├─ サイレントリード検出時
    │   └→ Researcher へのプロファイル追加依頼
    │
    ├─ 商談スケジューリング時
    │   ├→ Google Calendar / Calendly 連携
    │   └→ Lead Strategist にスケジュール共有
    │
    └─ フォローアップ時
        └→ Distributor で配信
```

---

## 重要な実装注意点

第一に、**24時間体制**。深夜・休日でも DM が来たらドラフトを生成。

第二に、**返信タイミングの自然さ**。即レス避けて、30分〜2時間後に承認待ち通知。

第三に、**プライバシー配慮**。個人情報を不必要に保存しない。

第四に、**エスカレーション判断**。怒り・クレーム・法的問題の予兆を検出したら人間に即通知。

```python
ESCALATION_TRIGGERS = [
    "complaint",
    "legal_threat",
    "anger",
    "refund_demand",
    "complex_negotiation",
    "press_inquiry",
]
```

---

## 開発優先度

**Phase 1 必須機能**:
- [x] DM 返信ドラフト(X、Instagram)
- [x] コメント返信ドラフト
- [ ] サイレントリード抽出
- [ ] フォローアップシーケンス
- [ ] エスカレーション検出

**Phase 2 で追加**:
- [ ] 商談スケジューリング自動化
- [ ] LinkedIn DM
- [ ] LINE 個別応対
- [ ] 感情分析の高度化
