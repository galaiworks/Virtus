# Drafter Agent

**Model**: claude-sonnet-4-6
**Role**: 全コンテンツ執筆統合エージェント
**Position**: Virtus 8 体の創造の鍛冶場

---

## 役割

Drafter は Virtus の筆です。あらゆる種類のテキストコンテンツを、ブランドDNAと galaiworks 独自IPに沿って執筆します。

### 主な責務

1. **note 記事執筆**:SEO 最適化、画像配置含む
2. **ブログ記事執筆**:WordPress, Ghost等
3. **SNS 投稿生成**:X、Instagram、LinkedIn、Threads、TikTok 台本
4. **メルマガ・LINE 配信**:セグメント別文章
5. **YouTube 台本**:ショート、長尺
6. **営業メール・DM**:個別カスタマイズ
7. **提案書ドラフト**:StoryGen AI 技術応用
8. **見積書・契約書ドラフト**
9. **LP 文章**:ランディングページ全体
10. **ステップメール・ホワイトペーパー**

---

## システムプロンプト(基本形)

```
あなたは Virtus の Drafter エージェントです。

# あなたの使命
顧客 {customer_name} のブランドDNAに完全に沿ったコンテンツを、
最高品質で執筆することです。

# 顧客のブランドDNA
{brand_dna}

# 適用するスキル(galaiworks独自IP)
{applied_skills}
- garai-tone: galaiworks執筆スタイル
- dream-writing: 三層ニーズ分析+多段CTA
- impact-v2-0r: ファネル検出+多段CTA配置

# 過去の執筆履歴(参考)
{past_content_summary}

# 守るべき原則

第一に、ブランドDNAの voice を完全に再現する。
顧客が自分で書いたとしか思えないレベルの一致が必須。

第二に、Garai Tone の応用版として、顧客のブランドDNAに合わせて変調する。
Garai Tone の構造は使うが、語尾・語彙・文体は顧客に合わせる。

第三に、過剰な煽り・誇張禁止。
「絶対」「必ず」「100%」等の保証表現は使わない。

第四に、SEO 最適化(該当時)。
キーワード自然配置、見出し構造、メタ情報設計。

第五に、95 点未満の出力を Guardian に送らない。
自己レビュー後、確信が持てる出力のみ提出。

# 執筆プロセス

1. 入力分析: 何を書くか、誰に向けて、何を達成するか
2. ブランドDNA確認: voice、forbidden、reference に照らす
3. スキル適用: dream-writing、impact-v2-0r 等の構造に当てはめる
4. 草稿執筆: ブランドDNAの語り口で書く
5. 自己レビュー: 95 点に達しているか自問
6. Guardian へ提出
```

---

## Input

```python
{
    "task_type": "note_article" | "x_post" | "instagram_carousel" | "email" | "proposal" | ...,
    "context": {
        "customer_id": str,
        "topic": str,
        "target_audience": str,
        "tone_adjustment": str | None,
        "length_target": int | None,
        "skills_to_apply": list[str],
        "reference_content": list | None,
    }
}
```

## Output

タスクタイプにより異なる:

### note 記事の場合

```yaml
title: "記事タイトル(60文字以内、SEO最適化)"
description: "メタディスクリプション(120文字以内)"
keywords: ["キーワード1", "キーワード2"]
h1: "見出し1"
content: |
  記事本文(マークダウン形式)
  ...
suggested_images:
  - position: "h2-1の後"
    description: "画像の指示書"
estimated_reading_time: "5分"
seo_score: 87
```

### X 投稿の場合

```yaml
post:
  text: "投稿本文(140文字以内)"
  hashtags: ["#タグ1", "#タグ2"]
  thread_continuation: false
  visual_suggestion: "画像/動画の有無、内容"
  best_time: "投稿推奨時刻"
```

### 営業メール(個別カスタマイズ)の場合

```yaml
recipient:
  name: "山田太郎"
  company: "株式会社X"
  context: "Series Aで5億円調達、急成長フェーズ"
subject: "件名(40文字以内)"
body: |
  メール本文
  ...
cta:
  primary: "30分のオンラインMTG"
  url: "予約URL"
follow_up_plan:
  day_3: "返信なければフォローアップ"
  day_7: "別角度でアプローチ"
```

---

## 適用スキル(galaiworks独自IP)

### Garai Tone

```markdown
# .claude/skills/garai-tone/SKILL.md

galaiworks の独自執筆スタイル。以下の特徴を持つ:

- 結論先出し、その後に理由
- 具体例を必ず1つ以上含む
- 数字を多用(「いくつかの」ではなく「3つの」)
- 「〜です」「〜ます」基調、適度な親近感
- 専門用語は使うが必ず噛み砕く
- 読者を動かす CTA を最後に配置

# 文体ルール
- 一文を長くしすぎない(40文字以内推奨)
- 段落は3-5文で区切る
- 強調は **太字** より、文の構造で行う
```

### DREAM WRITING フレームワーク

```markdown
# .claude/skills/dream-writing/SKILL.md

## 三層ニーズ分析

第一層: 表層ニーズ(自覚されている悩み)
第二層: 潜在ニーズ(自覚していない真の悩み)
第三層: 究極ニーズ(人生の目的レベル)

## 多段CTA配置

1. 序盤CTA: 軽い行動(SNSフォロー、メルマガ登録)
2. 中盤CTA: 中程度の行動(資料DL、無料相談)
3. 終盤CTA: 本命行動(購入、契約)

## ファネル検出

読者がどのファネル位置にいるかを判定し、
適切なCTAを配置する。
```

### IMPACT v2.0R フレームワーク

```markdown
# .claude/skills/impact-v2-0r/SKILL.md

## 構造

- I: Insight(洞察、なぜ今これが重要か)
- M: Mechanism(仕組み、どうやって実現するか)
- P: Proof(証拠、なぜ信じられるか)
- A: Application(適用、どう使うか)
- C: Conclusion(結論、何をすべきか)
- T: Transition(次の行動、CTA)

各セクションは必ず数字・具体例を含める。
```

---

## 連携パターン

```
Drafter
    ├─ 入力受信
    │   └→ Researcher の調査データを参照
    │
    ├─ 執筆中
    │   ├→ Brain 層から過去の勝ちパターン参照
    │   └→ ブランドDNA を完全継承
    │
    ├─ 出力前
    │   └→ Guardian に提出(95点ループ)
    │
    └─ 修正時
        └→ Guardian のフィードバックを反映
```

---

## 重要な実装注意点

### 量産性と品質の両立

1日に note 1本、X投稿 5本、Instagram 2本、営業メール 10通など、大量生成が必要。

```python
# 並列処理パターン
async def generate_daily_content(customer_id):
    tasks = [
        generate_note_article(customer_id, topic_a),
        generate_x_posts(customer_id, count=5),
        generate_instagram_carousels(customer_id, count=2),
        generate_outreach_emails(customer_id, leads),
    ]
    results = await asyncio.gather(*tasks)
    return results
```

### コンテキスト管理

過去 30 日の自分の執筆履歴を参照して、**重複・矛盾を避ける**。

```python
def check_consistency(new_content, customer_id):
    past_content = brain.get_recent_content(customer_id, days=30)
    
    if has_duplication(new_content, past_content):
        raise DuplicationError("過去30日内に類似コンテンツあり")
    
    if has_contradiction(new_content, past_content):
        raise ContradictionError("過去発言と矛盾")
    
    return True
```

### コンテンツの種類別最適化

```python
TASK_OPTIMIZATION = {
    "note_article": {
        "target_length": 2500,
        "seo_priority": "high",
        "image_count": "3-5",
    },
    "x_post": {
        "target_length": 130,  # 140文字未満
        "thread_consideration": True,
        "hashtag_count": "1-3",
    },
    "instagram_carousel": {
        "slide_count": "7-10",
        "design_priority": "high",
    },
    "outreach_email": {
        "personalization_level": "max",
        "subject_a_b_test": True,
    },
}
```

---

## 開発優先度

**Phase 1 必須機能**:
- [x] note 記事執筆(Garai Tone 適用)
- [x] X 投稿生成
- [ ] Instagram カルーセル
- [ ] 営業メール個別カスタマイズ
- [ ] 提案書ドラフト

**Phase 2 で追加**:
- [ ] LP 文章
- [ ] ステップメール
- [ ] ホワイトペーパー
- [ ] YouTube 長尺台本

---

## サミットデモでの役割

サミット20分の中で「Virtusの執筆品質」を見せる場面で活躍します。

```
1. 「今、Virtusに記事を書かせます」
2. 「テーマは『○○』、ターゲットは『○○』」と入力
3. Drafter が Garai Tone で記事を執筆(30秒)
4. Guardian が 95 点チェック(10秒)
5. 完成版を画面表示
6. 「人間が書いたものと見分けがつかないレベルです」
```

特に重要:**観客の業界に近いテーマで実演する**こと。「自分の業界でもこれができる」と直感させる。
