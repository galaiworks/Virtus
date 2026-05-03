---
name: proposal-generator
description: 商談前に提案書ドラフトを 30 分で生成するスキル。StoryGen AI の技術を応用し、顧客の業界・課題・推定ニーズを統合した提案書を自動生成。Drafter エージェントが商談前に呼び出される。
---

# Proposal Generator スキル

galaiworks の StoryGen AI 技術を応用した、商談前の提案書自動生成スキル。

---

## 機能概要

商談相手の情報を入力すると、30 分以内に以下の提案書を生成:

1. **エグゼクティブサマリー**(1 ページ)
2. **顧客の課題分析**(2 ページ)
3. **解決策の提示**(3-5 ページ)
4. **導入スケジュール**(1 ページ)
5. **投資対効果**(2 ページ)
6. **次のステップ**(1 ページ)

合計 10-12 ページの提案書を、業界・課題・ブランドDNA に合わせて自動生成。

---

## 入力情報

```yaml
prospect:
  company_name: "株式会社ABC"
  industry: "SaaS"
  size: "従業員 50 名"
  recent_news: "Series A で 5 億円調達"
  
meeting_info:
  meeting_date: "2026-05-20"
  meeting_purpose: "Virtus導入検討"
  decision_makers:
    - name: "山田太郎"
      title: "代表取締役"
      concerns: ["業務効率化", "営業自動化"]
  
prospect_pain_estimate:
  - "急成長で人手不足"
  - "営業活動が属人化"
  - "コンテンツ発信が回らない"
  
proposal_focus:
  - "Tier 2 Virtus Box Pro の導入"
  - "Founding Member 優先枠の活用"
```

---

## 出力構造

### Section 1: エグゼクティブサマリー

```markdown
# 株式会社ABC 様向け Virtus 導入ご提案

## エグゼクティブサマリー

貴社の Series A 完了に伴う事業拡大フェーズにおいて、
以下の 3 つの課題に対する解決策をご提案いたします。

1. 業務効率化ニーズへの対応(8 体 AI エージェントチームによる)
2. 営業活動の体系化(能動営業 + 商談クロージング自動化)
3. コンテンツ発信の継続性(月 30 本以上のコンテンツ自動生成)

ご提案内容: Virtus Box Pro(Tier 2)
初期費用: 698,000 円
月額: 198,000 円
想定 ROI: 6 ヶ月で投資回収、12 ヶ月で 3 倍リターン
```

### Section 2: 顧客の課題分析

```markdown
## 1. 貴社の現状理解

### Series A 後の急成長フェーズ
プレスリリースで拝見した通り、
貴社は今、〇〇という挑戦に取り組まれています。

### 推定される課題

#### 課題 1: 業務効率化
従業員 50 名規模での急成長は、
属人化と業務負荷の課題を生みやすい段階です。

[業界データを根拠に記述]

#### 課題 2: 営業活動の体系化
[具体的に記述]

#### 課題 3: コンテンツ発信の継続性
[具体的に記述]
```

### Section 3: 解決策

```markdown
## 2. Virtus による解決策

### 2.1 Virtus とは
[Virtus の本質を 3 段落で説明]

### 2.2 8 体エージェント構成
[各エージェントの役割を貴社の課題に紐付けて説明]

### 2.3 貴社への適用シナリオ

#### シナリオ A: 営業自動化
朝 5 時に Researcher が同業界の資金調達企業を抽出。
9 時までに Drafter が個別カスタマイズ営業メール 50 通を生成。
貴社営業チームは承認のみで、月 1,500 件の能動営業が可能に。

#### シナリオ B: コンテンツ発信
[具体的なシナリオ]

#### シナリオ C: 商談クロージング
[具体的なシナリオ]
```

### Section 4: 導入スケジュール

```markdown
## 3. 導入スケジュール

### Week 1: 環境構築(完全代行)
- Anthropic API キー取得サポート
- Claude Code セットアップ
- MCP 接続(Notion, Drive, X, Instagram)

### Week 2: ブランドDNA 構築
- 30 問ヒアリング(60 分 MTG)
- 過去コンテンツ分析
- ブランドDNA 初版作成

### Week 3: 試運転
- サンプルコンテンツ生成
- 品質確認・微調整

### Week 4: 本格運用開始
- 1 日のスケジュール自動実行開始
- 朝報配信開始
```

### Section 5: 投資対効果

```markdown
## 4. 投資対効果(ROI)

### 月次コスト
| 項目 | 金額 |
|------|------|
| Virtus Box Pro 月額 | 198,000 円 |
| Anthropic API 実費(上限) | 18,000 円 |
| 合計 | 216,000 円 |

### 期待効果(月次)
| 項目 | 試算根拠 | 金額換算 |
|------|---------|---------|
| 営業時間削減 | 月 80 時間削減 × 5,000 円/時 | 400,000 円 |
| コンテンツ制作コスト削減 | 月 30 本 × 外注時 30,000 円 | 900,000 円 |
| 新規リード獲得増 | +月 50 件 × 商談化 30% × 平均単価 50,000 円 | 750,000 円 |
| 合計効果 | | 2,050,000 円 |

### ROI
- 月次純効果: 2,050,000 - 216,000 = 1,834,000 円
- 投資回収期間: 698,000 ÷ 1,834,000 = 約 0.4 ヶ月
- 12 ヶ月リターン: 1,834,000 × 12 - (216,000 × 12 + 698,000) = 約 2,000 万円
```

### Section 6: 次のステップ

```markdown
## 5. 次のステップ

### 推奨される次のアクション

1. **本提案へのご質問・ご相談**
   ご不明点がございましたら、いつでもお問い合わせください。

2. **無料 Virtus 診断(60 分)**
   貴社専用の Virtus 設計図を作成いたします。
   費用: 無料

3. **Founding Member 枠の確保**
   2026 年 8 月末までに 30 名で締切となります。
   現在の残り枠: X 名

### お打ち合わせ日程

ご都合のよろしい日時をお知らせください。
こちらからの候補日時:
- 2026/5/22 (木) 14:00-15:00
- 2026/5/23 (金) 10:00-11:00
- 2026/5/26 (月) 16:00-17:00
```

---

## 実装フロー

```python
async def generate_proposal(prospect_info, customer_id):
    """
    30 分で提案書を自動生成
    """
    # Step 1: 顧客の業界・最新動向リサーチ(Researcher 連携)
    industry_context = await researcher.research_industry(
        prospect_info.industry
    )
    
    # Step 2: 推定課題の深掘り(Lead Strategist 連携)
    pain_analysis = await lead_strategist.analyze_pain(
        prospect_info,
        industry_context,
    )
    
    # Step 3: 適用シナリオの生成
    scenarios = generate_application_scenarios(
        prospect_info,
        pain_analysis,
    )
    
    # Step 4: ROI 試算
    roi_analysis = calculate_roi(
        prospect_info.size,
        proposed_tier="tier_2",
    )
    
    # Step 5: 提案書本体の執筆(Drafter 連携)
    proposal_content = await drafter.write_proposal(
        prospect=prospect_info,
        industry_context=industry_context,
        pain_analysis=pain_analysis,
        scenarios=scenarios,
        roi=roi_analysis,
        skills=["impact-v2-0r", "garai-tone"],
    )
    
    # Step 6: ビジュアル化(Designer 連携)
    visual_elements = await designer.create_proposal_visuals(
        proposal_content,
    )
    
    # Step 7: PowerPoint または PDF として出力
    final_proposal = await render_proposal(
        content=proposal_content,
        visuals=visual_elements,
        format="pdf",
    )
    
    # Step 8: Guardian チェック
    quality_check = await guardian.evaluate(final_proposal)
    if quality_check.score < 95:
        final_proposal = await refine_with_feedback(
            final_proposal,
            quality_check.feedback,
        )
    
    return final_proposal
```

---

## 商談前ブリーフィング

提案書とは別に、商談 5 分前に渡される簡潔なブリーフィングも生成:

```yaml
briefing:
  prospect_summary: "Series A 完了直後、急成長フェーズ"
  
  key_pain_points:
    - "業務効率化"
    - "営業の属人化"
    - "コンテンツ発信"
  
  conversation_starters:
    - "資金調達おめでとうございます"
    - "急成長フェーズの組織課題について"
  
  questions_likely_asked:
    - "他社事例は?"
    - "ROI は?"
    - "セキュリティは?"
  
  prepared_answers:
    - q: "他社事例は?"
      a: "Founding Member 30 名のうち、IT・SaaS 業界からは 8 名参画予定..."
  
  pricing_strategy:
    primary: "Tier 2 Virtus Box Pro"
    alternative: "Tier 1 → Tier 2 へのアップグレードパス"
    objection_handling: "..."
  
  meeting_objective:
    primary: "Tier 2 契約の合意"
    secondary: "次回 MTG の確定"
    fallback: "無料診断の受諾"
```

---

## サミットデモでの活用

サミット 20 分の中で、提案書自動生成を 30 秒で実演:

```
1. 「あなたが商談相手の情報を Virtus に入力します」
2. 入力例:「株式会社X、Series A完了、SaaS業界」
3. 「30 秒待ってください」
4. 提案書 PDF が完成、画面に表示
5. 「これを商談前に毎回手作業で作っていたら、何時間かかりますか?」
6. 「Virtus は 30 秒です」
```

観客に「商談準備の革命」を体感させる重要な実演です。
