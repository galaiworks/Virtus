# ブランドDNA テンプレート

このファイルは、各顧客のブランドDNAを定義するテンプレートです。
顧客オンボーディング時に、このテンプレートをコピーしてカスタマイズします。

実際の顧客データは `/brain/customers/{customer_id}/brand-dna.md` に保存されます。

---

## 顧客固有のブランドDNA(galaiworks 自身を例として)

### Identity(同一性)

```yaml
identity:
  name: "galaiworks"
  founder: "ガライ"
  founded_year: 2024
  business: "AI 開発、SaaS、コンテンツ自動化"
  
  primary_target_audience: "ひとり社長・コーチ・コンサル・専門家"
  secondary_target_audience: "中小企業の経営者"
  
  unique_value_proposition: |
    海外最先端の AI エージェント技術を、
    日本のひとり社長が使えるレベルまで落とし込む唯一のサービス
  
  core_competencies:
    - "Claude Code 実装力"
    - "Anthropic 公式アーキテクチャ準拠"
    - "Garai Tone、DREAM WRITING、IMPACT v2.0R 独自IP"
    - "SEO 80件以上 1 位獲得"
    - "建設業 20 年のリアルビジネス経験"
```

### Voice(声)

```yaml
voice:
  tone: "プロフェッショナル × 親近感 × 直球"
  
  personality:
    - "率直、嘘や曖昧さを嫌う"
    - "海外動向に詳しい"
    - "数字に強い"
    - "実装力を見せる"
    - "建設業経験から来る現場感"
  
  vocabulary:
    preferred:
      - "率直に言うと"
      - "正直に言います"
      - "本質は"
      - "結論から言うと"
      - "具体的には"
      - "実装"
      - "アーキテクチャ"
    
    avoid:
      - "絶対"
      - "必ず"
      - "100%"
      - "簡単"
      - "すぐ稼げる"
      - "魔法"
  
  signature_phrases:
    - "率直に言います"
    - "現実的かつ厳密に"
    - "海外で起きている革命"
    - "これは事実です"
  
  forbidden_tones:
    - "誇張表現"
    - "過剰な楽観論"
    - "煽り"
    - "MLM 風表現"
```

### Content Strategy(戦略)

```yaml
content_strategy:
  pillar_topics:
    - "AI エージェント・マルチエージェント設計"
    - "ひとり社長の自動化戦略"
    - "海外最先端の AI 動向"
    - "Claude Code 実装"
    - "SEO・コンテンツマーケティング"
  
  content_types:
    primary:
      - note_articles  # メイン
      - x_posts
      - youtube
    secondary:
      - linkedin
      - instagram_reels
  
  publishing_frequency:
    note: "週 2-3 本"
    x: "1 日 5-8 本"
    youtube: "週 1 本"
    linkedin: "週 2-3 本"
```

### Forbidden(禁忌)

```yaml
forbidden:
  topics:
    - "競合のディスり"
    - "個人攻撃"
    - "政治的発言"
    - "宗教的発言"
    - "未確認情報"
  
  expressions:
    - "絶対稼げる"
    - "誰でも簡単に"
    - "魔法のような"
    - "革命的(乱用しない、文脈次第)"
  
  practices:
    - "ブラウザ自動化"
    - "無断スクレイピング"
    - "個人情報の不正取得"
    - "スパム送信"
```

### Reference(参照)

```yaml
reference:
  past_winning_content:
    - title: "建設業20年の経験者がAI開発に転身した理由"
      url: "..."
      pv: 12500
      key_insight: "リアルビジネス経験 × AI が刺さる"
    
    - title: "海外で評価額1兆5000億円のAIサービス"
      url: "..."
      pv: 8900
      key_insight: "海外データの引用が信頼性を高める"
  
  competitor_examples:
    - name: "いいねAI"
      reference_for: "SNS特化のポジショニング(差別化対象)"
    - name: "JAPAN AI AGENT"
      reference_for: "法人汎用型(差別化対象)"
    - name: "NoimosAI"
      reference_for: "マーケチーム型(最も近いが差別化必要)"
  
  inspiration_sources:
    - name: "Sintra"
      reason: "ひとり社長向け 12 ヘルパー、英語圏で大成功"
    - name: "Sierra"
      reason: "$10B 評価額のマルチエージェント"
    - name: "神さん(動画)"
      reason: "AI CEO 設計、PR タイムズ自動営業"
```

---

## 顧客オンボーディング時のヒアリング項目

### 30 問ヒアリング(60 分 MTG)

```
Identity 編(5 問)
1. ビジネス名は?
2. 何をしているか 30 秒で説明すると?
3. 主要顧客は誰か?
4. 競合は誰か?
5. あなたの独自性は何か?

Voice 編(8 問)
6. 普段の話し方は丁寧/カジュアル/混合 ?
7. 好む言葉、口癖は?
8. 絶対使わない言葉は?
9. 自分の発信を一言で表すと?
10. 親近感を出すフレーズは?
11. プロフェッショナル感を出すフレーズは?
12. 過去の自分の発信で「これは自分らしい」と感じたものは?
13. 過去の自分の発信で「これは自分らしくない」と感じたものは?

Content Strategy 編(7 問)
14. 主要トピック 3 つ?
15. 副次トピック 3 つ?
16. メインプラットフォームは?
17. 投稿頻度は?
18. 過去にバズった/反応が良かった投稿は?
19. 過去に反応が悪かった投稿は?
20. 競合の中で「これは真似したい」発信は?

Target Audience 編(5 問)
21. 想定読者の年齢層は?
22. 業界・職種は?
23. 年商規模は?
24. 抱える典型的な悩みは 3 つ?
25. 行動パターン(どんな媒体を見るか)は?

Forbidden 編(3 問)
26. 扱いたくないトピックは?
27. 言いたくない表現は?
28. 競合との関わり方は?

Goal 編(2 問)
29. 6 ヶ月後の理想は?
30. 1 年後の理想は?
```

### ヒアリング後の作業

```python
def build_brand_dna(hearing_data, past_content_urls):
    """
    ヒアリングデータと過去コンテンツから brand-dna.md を生成
    """
    # Step 1: 過去コンテンツの voice 分析
    voice_analysis = analyze_writing_style(past_content_urls)
    
    # Step 2: ヒアリングデータと voice 分析の統合
    brand_dna = merge_hearing_and_analysis(
        hearing_data,
        voice_analysis,
    )
    
    # Step 3: テンプレートに沿って整形
    formatted = format_as_brand_dna_yaml(brand_dna)
    
    # Step 4: 顧客に確認、微調整
    return formatted
```

---

## ブランドDNA の更新タイミング

```
月次:
- Analyst が違反パターンを検出 → 微調整提案

四半期:
- 全体的な見直し
- ピラートピックの追加・削除
- voice の更新

年次:
- 完全なリブランディング
- 新しいビジネス展開に合わせた再構築
```
