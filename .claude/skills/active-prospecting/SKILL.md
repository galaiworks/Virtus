---
name: active-prospecting
description: PR タイムズ等から能動営業ターゲットを自動抽出するスキル。「儲かってそう」「決済権あり」「痛みがありそう」をスコアリングし、上位 50 件を毎日更新。Researcher エージェントが朝 5 時に自動実行。サミットデモの目玉機能。
---

# Active Prospecting スキル

PR タイムズ等から能動営業ターゲットを抽出する Virtus のキラー機能。

---

## ワークフロー全体像

```
朝 5:00  PR タイムズ新着取得(過去 24 時間分)
    ↓
朝 5:05  業界フィルタリング(顧客のターゲット業界)
    ↓
朝 5:10  「儲かってそう」スコアリング
    ↓
朝 5:15  ホームページから問合せ情報抽出
    ↓
朝 5:20  X/LinkedIn から決済権者特定
    ↓
朝 5:25  上位 50 件選定
    ↓
朝 5:30  Brain 層に保存、Drafter に営業メール生成依頼
    ↓
朝 5:45  営業メール 50 通完成
    ↓
朝 7:00  Lead Strategist が朝報で報告
```

---

## スコアリングロジック

### スコア構成(100 点満点)

| 項目 | 配点 | 検出方法 |
|------|------|---------|
| 売上シグナル | 25 | プレスリリース内の数字 |
| 資金調達シグナル | 25 | 「Series A」「資金調達」キーワード |
| 採用シグナル | 15 | 「採用拡大」「人員増」キーワード |
| プレスリリース頻度 | 10 | 過去 90 日の発信回数 |
| 業界トップ層 | 10 | 業界ランキング/ニュース言及 |
| 決済権者特定 | 15 | LinkedIn で代表/役員クラスを特定 |

### スコア解釈

```
90-100点: ★★★★★ 最優先(即日アプローチ)
80-89点:  ★★★★☆ 高優先(翌日アプローチ)
70-79点:  ★★★☆☆ 中優先(週内アプローチ)
60-69点:  ★★☆☆☆ 低優先(条件付きアプローチ)
60点未満: ☆☆☆☆☆ スキップ
```

---

## 実装

### Step 1: PR タイムズ取得

```python
async def fetch_prtimes_releases(period_hours=24):
    """
    PR タイムズの新着プレスリリースを取得
    """
    # 公式 RSS or API 経由(規約遵守)
    feed_url = "https://prtimes.jp/index.rdf"
    
    releases = await parse_rss(feed_url)
    
    # 期間フィルタ
    cutoff = datetime.now() - timedelta(hours=period_hours)
    recent_releases = [r for r in releases if r.published >= cutoff]
    
    return recent_releases
```

### Step 2: 業界フィルタリング

```python
def filter_by_industry(releases, target_industries):
    """
    顧客のターゲット業界に合致するもののみ抽出
    """
    filtered = []
    
    for release in releases:
        # キーワードマッチ
        if matches_industry_keywords(release, target_industries):
            filtered.append(release)
        # カテゴリーマッチ
        elif release.category in target_industries:
            filtered.append(release)
    
    return filtered
```

### Step 3: スコアリング

```python
def score_release(release):
    """
    プレスリリースをスコアリング
    """
    score = 0
    breakdown = {}
    
    # 売上シグナル
    revenue_match = re.search(r'売上(\d+)億円?', release.text)
    if revenue_match:
        revenue = int(revenue_match.group(1))
        if revenue >= 10:
            breakdown["revenue_signal"] = 25
        elif revenue >= 1:
            breakdown["revenue_signal"] = 15
    
    # 資金調達シグナル
    funding_keywords = ["Series A", "Series B", "資金調達", "シリーズ", "投資"]
    if any(kw in release.text for kw in funding_keywords):
        breakdown["funding_signal"] = 25
    
    # 採用シグナル
    hiring_keywords = ["採用拡大", "人員増", "募集中", "採用強化"]
    if any(kw in release.text for kw in hiring_keywords):
        breakdown["hiring_signal"] = 15
    
    # プレスリリース頻度
    company_release_count = count_recent_releases(release.company, days=90)
    if company_release_count >= 10:
        breakdown["frequency_signal"] = 10
    elif company_release_count >= 5:
        breakdown["frequency_signal"] = 6
    
    # 業界トップ層判定
    if is_top_tier_company(release.company):
        breakdown["industry_position"] = 10
    
    score = sum(breakdown.values())
    
    return ScoredRelease(
        release=release,
        score=score,
        breakdown=breakdown,
    )
```

### Step 4: 決済権者特定

```python
async def identify_decision_maker(company_name):
    """
    LinkedIn 等から決済権者候補を特定
    """
    # LinkedIn API 経由(規約遵守)
    candidates = await search_linkedin(
        company=company_name,
        titles=["代表取締役", "CEO", "取締役", "執行役員"],
    )
    
    # 公式サイトの「会社概要」「役員一覧」もパース
    website_info = await scrape_company_website(company_name)
    
    # 統合
    decision_makers = consolidate(candidates, website_info)
    
    return decision_makers[0] if decision_makers else None
```

### Step 5: 連絡先取得

```python
async def get_contact_info(company_name, company_url):
    """
    問合せ先情報を取得
    """
    info = {
        "contact_form": None,
        "email": None,
        "phone": None,
    }
    
    # サイトからの問合せフォーム検出
    contact_page = await find_contact_page(company_url)
    if contact_page:
        info["contact_form"] = contact_page
    
    # 公開メールアドレスの検出(info@等)
    public_email = await find_public_email(company_url)
    if public_email:
        info["email"] = public_email
    
    return info
```

---

## 出力例

```yaml
# /brain/customers/founding_001/leads/2026-05-15_active_prospects.yaml

extracted_at: "2026-05-15T05:30:00+09:00"
total_releases_processed: 247
qualified_leads: 50

leads:
  - lead_id: "lead_20260515_001"
    company: "株式会社ABC"
    company_url: "https://abc.co.jp"
    score: 92
    breakdown:
      revenue_signal: 25
      funding_signal: 25
      hiring_signal: 15
      frequency_signal: 10
      industry_position: 10
      decision_maker_identified: 7
    
    press_release:
      title: "Series Aで5億円調達、本格的な事業拡大へ"
      url: "https://prtimes.jp/main/html/rd/p/000000xxx"
      published: "2026-05-15T09:00:00+09:00"
    
    decision_maker:
      name: "山田太郎"
      title: "代表取締役"
      linkedin_url: "https://linkedin.com/in/..."
      verified: true
    
    contact:
      form_url: "https://abc.co.jp/contact"
      email: "info@abc.co.jp"
    
    pain_estimate: |
      Series A 完了で急成長フェーズ。
      組織拡大で業務効率化ニーズが高い。
      AI 活用に積極的な可能性。
    
    recommended_approach: |
      「資金調達おめでとうございます」を起点に、
      組織拡大時の業務効率化サポートとして Virtus を提案。
    
    outreach_priority: "★★★★★"
    next_action: "本日中に Drafter に営業メール生成依頼"
    status: "qualified"
```

---

## 連携パターン

```
Active Prospecting
    ├─ Researcher が実行
    │   ↓
    ├─ Brain層に保存
    │   ↓
    ├─ Drafter に営業メール生成依頼
    │   ├→ 個別カスタマイズ
    │   └→ Garai Tone + 顧客のブランドDNA
    │   ↓
    ├─ Guardian 95点ループ
    │   ↓
    ├─ 顧客承認待ちキュー
    │   ↓
    └─ 顧客承認後、Distributor が配信
```

---

## 法令・規約遵守

第一に、**robots.txt 遵守**。スクレイピング前に必ず確認。

第二に、**特定電子メール法**:営業メールには連絡先・解除動線必須。

第三に、**LinkedIn 規約**:公式 API のみ、無断スクレイピング禁止。

第四に、**個人情報保護法**:公開情報のみ収集、目的外利用禁止。

第五に、**プレスリリース著作権**:全文転載せず、要約・引用のみ。

---

## サミットデモでの実演手順

```
1. オーナーが「IT・SaaS業界の資金調達企業」と入力(5秒)

2. Virtus 起動(画面共有)

3. Researcher が PR タイムズから新着取得
   「過去 24 時間で 247 件のプレスリリースを発見」

4. 業界フィルタリング
   「IT・SaaS関連で 89 件に絞り込み」

5. スコアリング実行
   「『儲かってそう』『決済権あり』を判定...」

6. 上位 50 件確定
   「優先度順に並べ替え完了」

7. 結果表示
   「★★★★★ 株式会社X: Series A 5億円調達」
   「★★★★★ 株式会社Y: 売上 30 億円達成」
   ...

8. Drafter が個別営業メール生成
   「30 秒で 50 通の個別カスタマイズメール完成」

9. サンプル 1 通を画面表示
   「これが、Virtus が毎朝5時にやっていることです」
```

これがサミット 20 分の最大の山場になります。
