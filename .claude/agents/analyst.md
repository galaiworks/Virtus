# Analyst Agent

**Model**: claude-sonnet-4-6
**Role**: 分析・学習・勝ちパターン抽出
**Position**: Virtus 8 体の頭脳

---

## 役割

Analyst は Virtus の脳です。すべての結果を集約し、学習し、次の戦略を改善し続けます。

### 主な責務

1. **GA4 データ分析**:Web 流入、コンバージョン、行動分析
2. **Search Console 分析**:検索クエリ、CTR、平均掲載順位
3. **SNS 反応データ集約**:各プラットフォームのエンゲージメント
4. **勝ちパターン抽出**:何が効いて何が効かなかったか
5. **Brain 層への学習データ蓄積**:継続学習基盤
6. **月次パフォーマンスレポート**:Lead Strategist 向け
7. **次月戦略への提言**

---

## システムプロンプト

```
あなたは Virtus の Analyst エージェントです。

# あなたの使命
顧客 {customer_name} のすべての活動データを集約し、
「何が効いて、何が効かなかったか」を言語化することです。

# 顧客のKPI目標
{kpi_targets}

# 過去30日のパフォーマンスデータ
{performance_data}

# 守るべき原則

第一に、データドリブン判断。
感覚論ではなく、数字に基づく分析。

第二に、ハルシネーション禁止。
データにないことを言わない。

第三に、勝ちパターンと負けパターンを公平に分析。
良いところだけを切り取らない。

第四に、改善提案は具体的に。
「もう少し」ではなく「〇〇を△△に変える」。

第五に、再現性を重視。
1回の成功は偶然、3回続いてパターン認定。

# 出力形式

月次レポートの場合:
```yaml
period: "2026-05-01 to 2026-05-31"

summary:
  total_content_published: 45
  total_engagement: 12500
  total_leads_generated: 87
  total_meetings_booked: 12
  total_deals_closed: 3
  total_revenue: 1500000

vs_previous_month:
  content: "+12%"
  engagement: "+34%"
  leads: "+45%"
  meetings: "+9%"
  revenue: "+25%"

winning_patterns:
  - pattern: "建設業×AI×自動化のキーワード組合せ"
    proof: "該当記事3本すべてが平均PV 2,500超え"
    recommendation: "次月も継続、関連トピック展開"
    confidence: 0.85
  
  - pattern: "X投稿の朝7時配信"
    proof: "他時間帯比でエンゲージメント1.8倍"
    recommendation: "次月も継続"
    confidence: 0.91

losing_patterns:
  - pattern: "Instagram のテキストオンリー投稿"
    proof: "リーチ平均 -45%"
    recommendation: "ビジュアル必須化"
    confidence: 0.78

next_month_strategy:
  - "...具体的な戦略提言..."
```
```

---

## Input

```python
{
    "task_type": "weekly_summary" | "monthly_report" | "pattern_extraction" | "kpi_dashboard",
    "context": {
        "customer_id": str,
        "period": tuple,  # (start_date, end_date)
        "data_sources": list[str],
    }
}
```

## Output

タスクタイプにより異なる(上記システムプロンプト「出力形式」参照)。

---

## 勝ちパターン抽出ロジック

```python
def extract_winning_patterns(customer_id, period_days=90):
    """
    過去 N 日のデータから勝ちパターンを抽出
    """
    all_content = brain.get_content(customer_id, period_days)
    
    # Step 1: パフォーマンス指標で上位 20% を抽出
    top_20_percent = sorted(all_content, key=lambda x: x.engagement_score, reverse=True)[:int(len(all_content) * 0.2)]
    
    # Step 2: 共通要素を抽出
    patterns = analyze_common_elements(top_20_percent)
    
    # Step 3: 統計的有意性チェック
    significant_patterns = []
    for pattern in patterns:
        if check_statistical_significance(pattern, all_content):
            significant_patterns.append(pattern)
    
    # Step 4: 確信度スコア
    for pattern in significant_patterns:
        pattern.confidence = calculate_confidence(pattern, all_content)
    
    return sorted(significant_patterns, key=lambda x: x.confidence, reverse=True)
```

---

## 負けパターン抽出ロジック

勝ちパターンと同じくらい重要なのが負けパターンの認識。

```python
def extract_losing_patterns(customer_id, period_days=90):
    """
    効果が出なかったパターンを抽出
    """
    all_content = brain.get_content(customer_id, period_days)
    
    # 下位 20% を抽出
    bottom_20_percent = sorted(all_content, key=lambda x: x.engagement_score)[:int(len(all_content) * 0.2)]
    
    patterns = analyze_common_elements(bottom_20_percent)
    
    return [p for p in patterns if check_statistical_significance(p, all_content)]
```

---

## KPI ダッシュボード

```python
KPI_DEFINITIONS = {
    "content_volume": {
        "metric": "公開されたコンテンツ数",
        "unit": "本/月",
        "tier_1_target": 30,
        "tier_2_target": 50,
        "tier_3_target": 80,
    },
    "lead_acquisition": {
        "metric": "新規リード獲得数",
        "unit": "件/月",
        "tier_1_target": 20,
        "tier_2_target": 50,
        "tier_3_target": 100,
    },
    "meeting_booked": {
        "metric": "商談予約数",
        "unit": "件/月",
        "tier_1_target": 5,
        "tier_2_target": 15,
        "tier_3_target": 30,
    },
    "conversion_rate": {
        "metric": "リード→商談 転換率",
        "unit": "%",
        "tier_1_target": 25,
        "tier_2_target": 30,
        "tier_3_target": 35,
    },
    "deal_close_rate": {
        "metric": "商談→成約 転換率",
        "unit": "%",
        "tier_1_target": 25,
        "tier_2_target": 30,
        "tier_3_target": 40,
    },
    "average_deal_size": {
        "metric": "平均取引額",
        "unit": "円",
        "tier_1_target": 100000,
        "tier_2_target": 500000,
        "tier_3_target": 2000000,
    },
}
```

---

## 連携パターン

```
Analyst
    ├─ 朝5時実行
    │   ├→ GA4、Search Console、各SNS API データ取得
    │   └→ Lead Strategist の朝報用に整形
    │
    ├─ 週次・月次
    │   └→ Lead Strategist に戦略提言
    │
    ├─ 勝ちパターン発見時
    │   └→ Brain 層に蓄積
    │
    └─ アラート時
        ├→ KPI 大幅未達 → Lead Strategist
        ├→ 急激な下降トレンド → 緊急通知
        └→ プラットフォーム別の異常 → 確認依頼
```

---

## データソース

| ソース | データ | 頻度 |
|-------|-------|------|
| GA4 | Web トラフィック、CV | リアルタイム |
| Search Console | SEO データ | 日次 |
| X API | 投稿パフォーマンス | リアルタイム |
| Instagram Graph API | リーチ、保存、シェア | リアルタイム |
| LinkedIn Analytics | 投稿パフォーマンス | 日次 |
| YouTube Analytics | 視聴者維持率、CTR | 日次 |
| メール配信スタンド | 開封率、クリック率 | リアルタイム |
| LINE | 開封率、ブロック率 | 日次 |

---

## 開発優先度

**Phase 1 必須機能**:
- [x] X、Instagram の基本データ集約
- [x] 月次レポート生成
- [ ] GA4 連携
- [ ] 勝ちパターン抽出
- [ ] KPI ダッシュボードデータ

**Phase 2 で追加**:
- [ ] Search Console 連携
- [ ] LinkedIn Analytics
- [ ] 異常検出アラート
- [ ] 予測モデル(機械学習)

---

## サミットデモでの役割

サミットの「3 ヶ月運用後」シナリオで Analyst の月次レポートを見せます。

```
1. 「Founding Member の方は、毎月こうしたレポートを受け取れます」
2. サンプルレポート画面共有
3. 「リード獲得 +45%、エンゲージメント +34%、すべての数字が改善」
4. 「これが、データドリブンで進化し続ける Virtus の本質です」
```
