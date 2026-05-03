# Virtus 要件定義書

**Document Version**: 1.0
**Last Updated**: 2026-05-03
**Status**: Phase 1 (Founding Members向け実装) 開始準備
**Author**: galaiworks
**Implementation Tool**: Claude Code

---

## 目次

1. [プロダクト概要](#1-プロダクト概要)
2. [事業要件](#2-事業要件)
3. [システムアーキテクチャ](#3-システムアーキテクチャ)
4. [8体エージェント詳細仕様](#4-8体エージェント詳細仕様)
5. [ワークフロー仕様](#5-ワークフロー仕様)
6. [データ構造](#6-データ構造)
7. [外部連携(MCP)](#7-外部連携mcp)
8. [ブランドDNA仕様](#8-ブランドdna仕様)
9. [品質管理(Guardian仕様)](#9-品質管理guardian仕様)
10. [セキュリティ・法令遵守](#10-セキュリティ法令遵守)
11. [実装ロードマップ](#11-実装ロードマップ)
12. [Phase 1実装スコープ](#12-phase-1実装スコープ)
13. [リポジトリ構造](#13-リポジトリ構造)
14. [運用フロー](#14-運用フロー)
15. [非機能要件](#15-非機能要件)
16. [Founding Member 専用要件](#16-founding-member-専用要件)

---

## 1. プロダクト概要

### 1.1 プロダクト名

**Virtus**(ウィルトゥス、徳・卓越性)

### 1.2 一行説明

ひとり社長・コーチ・コンサル・専門家のための、集client→営業→クロージングまでを完全自動化する 8 体の AI エージェントチーム

### 1.3 根本思想

「労働時間で売る」働き方から「成果と仕組みで売る」働き方への転換を支援する。

### 1.4 ターゲット顧客

| Tier | 対象 | 年商目安 |
|------|------|---------|
| Founding Member | 共創パートナー(初期30名限定) | 制限なし |
| Tier S | 個人事業主・フリーランス | 500万円以下 |
| Tier 1 | ひとり社長・コーチ・コンサル | 500万-5,000万円 |
| Tier 2 | 中堅事業者 | 5,000万-2億円 |
| Tier 3 | 法人 | 2億円以上 |

### 1.5 プロダクト形態

**箱型 Productized Service** + **将来的にWeb UI**

- Phase 1(現在〜2026年10月): Claude Code + リポジトリ配布
- Phase 2(2026年10月〜): クライアントサイドBYOK Web UI
- Phase 3(2027年Q1〜): マルチLLM対応フル SaaS

### 1.6 ビジネスモデル

**BYOK(Bring Your Own Key)型**

顧客が Anthropic API キーを自己契約。Virtus はエージェントロジック、運用伴走、独自IPを提供。

---

## 2. 事業要件

### 2.1 商品の本質

Virtus は単なるツールではなく、**「ひとり社長専属のAIチーム」というビジネスパートナー**として位置付ける。

### 2.2 価値提供の3軸

第一の軸: **時間解放**
1日12時間労働から1日6時間労働へ。

第二の軸: **生産量増大**
月8本のコンテンツから月30本以上へ、新規リード月5件から月50件以上へ。

第三の軸: **戦略集中**
オーナーが経営判断と顧客対応に集中できる環境構築。

### 2.3 主な競合差別化

| 競合カテゴリ | 代表 | Virtus の差別化 |
|-------------|------|-----------------|
| SNS特化 | いいねAI、∞AI Social | コンテンツ集客→営業→クロージング統合領域 |
| マーケティング統合 | NoimosAI | ひとり社長向け最適化、能動営業/クロージング機能 |
| 法人汎用 | JAPAN AI AGENT、Agentforce | 個人事業主・ひとり社長への適合 |
| 海外UGC広告 | Arcads、MakeUGC | 日本語対応、戦略統合 |
| コンタクトセンター型 | Sierra、Decagon、vottia | 集客・営業領域カバー |

### 2.4 価格構造

#### Founding Member プラン(★最初の30名限定)

```
契約期間: 12ヶ月コミット
初期構築費: 49,800円
月額: 9,800円
別途: 顧客が Anthropic API キー自己契約
```

特典:
- 全機能フル開放(Tier 3相当)
- Higgsfield/MakeUGCオプションも初期統合費無料
- 月次フィードバックMTG 60分込み
- Phase 2/Phase 3 アップグレード追加料金なし
- 正規版リリース後も生涯50%割引
- 「Founding Member」称号(LP掲載、事例公開協力時)

義務:
- 月1回のフィードバックアンケート
- 月1回のMTG参加
- 12ヶ月活用するコミット

#### 正規版 Tier 構造(2026年10月以降)

```
■ Tier 0: Virtus Diagnosis(無料、60分オンライン)

■ Tier S: Virtus Lite
   初期: 98,000円 / 月額: 19,800円
   API実費上限: 約2,000円/月

■ Tier 1: Virtus Box
   初期: 198,000円 / 月額: 49,800円
   API実費上限: 約6,000円/月

■ Tier 2: Virtus Box Pro(★メイン商品)
   初期: 698,000円 / 月額: 198,000円
   API実費上限: 約18,000円/月

■ Tier 3: Virtus Box Enterprise
   初期: 1,500,000円 / 月額: 398,000円
   API実費上限: 約45,000円/月
```

### 2.5 オプション

```
■ オプション A: Higgsfield MCP 統合(シネマ動画)
   初期: 49,800円 / 月額追加: 9,800円
   別途: Higgsfield プラン($9〜$84/月)を顧客自己契約

■ オプション B: MakeUGC 統合(UGC広告)
   初期: 49,800円 / 月額追加: 9,800円
   別途: MakeUGC プラン($49〜$199/月)を顧客自己契約

■ その他
   追加エージェント構築: 198,000円/体
   追加 MCP接続: 49,800円/接続
   カスタムスキル開発: 98,000円/スキル
   追加MTG (60分): 29,800円/回
   緊急対応 (48時間以内): 9,800円/対応
   ブランドDNA再構築: 148,000円
```

---

## 3. システムアーキテクチャ

### 3.1 アーキテクチャパターン

**Anthropic公式 Orchestrator-Worker パターン**

```
[Lead Strategist (Orchestrator)]
        │
        ├─ Researcher (Worker)
        ├─ Drafter (Worker)
        ├─ Designer (Worker)
        ├─ Distributor (Worker)
        ├─ Connector (Worker)
        ├─ Analyst (Worker)
        └─ Guardian (Quality Gate)
```

### 3.2 モデル使い分け

| エージェント | モデル | 用途 |
|------------|-------|------|
| Lead Strategist | Opus 4.7 | 戦略立案・統括 |
| Guardian | Opus 4.7 | 品質判定・ブランド遵守 |
| Researcher | Sonnet 4.6 | 探索・調査 |
| Drafter | Sonnet 4.6 | 執筆 |
| Designer | Sonnet 4.6 | ビジュアル生成 |
| Connector | Sonnet 4.6 | 関係構築 |
| Analyst | Sonnet 4.6 | 分析 |
| Distributor | Haiku 4.5 | 配信バッチ |

### 3.3 技術スタック

```yaml
implementation_tool: Claude Code
language: Python 3.11+ (一部 TypeScript)
llm_api: Anthropic Claude API (claude-opus-4-7, claude-sonnet-4-6, claude-haiku-4-5)
mcp_servers:
  - notion (https://mcp.notion.com/mcp)
  - google_drive
  - gmail
  - higgsfield (https://mcp.higgsfield.ai/mcp) ※オプション
storage:
  - local_filesystem (Phase 1)
  - supabase (Phase 2以降)
deployment:
  - phase_1: 顧客のローカル環境(Claude Code)
  - phase_2: Vercel + Supabase
```

### 3.4 BYOK セキュリティ設計

- API キーは顧客のローカル環境(.env)に保存
- galaiworks のサーバーには永続保存しない
- Phase 2 Web UI でも、ブラウザのlocalStorage(暗号化)に保存
- セッション中のメモリ保持以外は記録しない

---

## 4. 8体エージェント詳細仕様

### 4.1 Lead Strategist(戦略統括)

**モデル**: Opus 4.7

**役割**:
- オーケストレーター(全体指揮)
- 月次戦略立案、KPI管理
- 顧客との対話窓口(朝報、ウィークリーレビュー、マンスリーレビュー)
- 各エージェントへのタスク分配

**Input**:
- ブランドDNA(brand-dna.md)
- 過去の戦略履歴(brain/strategy-history/)
- 月次目標KPI
- 各エージェントからの報告

**Output**:
- 朝報(顧客向け、毎日7時)
- 月次戦略書(月初)
- ウィークリーレビュー(毎週月曜)
- マンスリーレビュー(月末)
- 各エージェントへの指示書

**システムプロンプト要件**:
- ブランドDNAを完全継承
- 95点未満は許さない(神さんの教え)
- 過剰な楽観論禁止、現実的な戦略
- Garai Tone継承(顧客の声で書く)

### 4.2 Researcher(探索専任)

**モデル**: Sonnet 4.6

**役割**:
- 業界トレンド継続調査
- 競合動向監視
- 検索キーワード調査
- PRタイムズ毎日監視(能動営業ターゲット抽出)
- X/LinkedInからの決済権者特定
- 月次市場洞察レポート生成

**Input**:
- ターゲット業界・キーワード
- 競合リスト
- 過去のリサーチ履歴

**Output**:
- 日次トレンドレポート
- 週次競合動向レポート
- PRタイムズ抽出リード(週20件以上)
- 月次市場洞察レポート

**重要要件**:
- ハルシネーション防止(全データはソースURL付き)
- 「儲かってそう」スコアリング(売上記載/資金調達/採用増等のシグナル)

### 4.3 Drafter(全コンテンツ執筆)

**モデル**: Sonnet 4.6

**役割**:
- note記事、ブログ
- X投稿、Instagram、LinkedIn投稿
- メルマガ、LINE配信
- YouTube台本
- 営業メール、提案書、商談シナリオ
- LP文章、ステップメール、ホワイトペーパー

**Input**:
- ブランドDNA
- Researcher のリサーチサマリー
- Garai Tone スキル(galaiworks独自)
- DREAM WRITING フレームワーク
- IMPACT v2.0R フレームワーク
- 過去執筆履歴

**Output**:
- 各種コンテンツドラフト(全て Guardian 95点ループ前提)

**重要要件**:
- Garai Tone を完全継承
- 顧客のブランドDNAを優先
- 過去記事との一貫性維持
- SEO最適化(note記事の場合)

### 4.4 Designer(ビジュアル生成)

**モデル**: Sonnet 4.6

**役割**:
- サムネイル生成
- 図解生成(Nano Banana連携)
- カルーセル画像生成
- OGP画像生成
- 提案書ビジュアル化

**Input**:
- ブランドカラー、フォント、ビジュアルガイド
- Drafter からのテキストコンテンツ

**Output**:
- 各種ビジュアル素材

**オプション機能**:
- Higgsfield MCP統合 → シネマ動画
- MakeUGC統合 → UGC広告動画

### 4.5 Distributor(配信処理)

**モデル**: Haiku 4.5(コスト最適化)

**役割**:
- 各プラットフォームへの予約投稿
- 配信タイミング最適化
- メルマガ・LINE配信
- 規約遵守の API 経由配信

**Input**:
- 配信スケジュール
- 配信先プラットフォーム
- Drafter+Designer の最終承認済みコンテンツ

**Output**:
- 配信ログ
- 配信エラーレポート

**重要要件**:
- ブラウザ自動化禁止(規約違反リスク)
- 公式 API のみ使用
- 配信前に必ず人間の承認を経由

### 4.6 Connector(関係構築)

**モデル**: Sonnet 4.6

**役割**:
- DM・コメント返信ドラフト生成(24時間体制)
- サイレントリード抽出(保存・複数閲覧者)
- 商談スケジューリング
- フォローアップシーケンス自動運用

**Input**:
- 受信DM・コメント
- 過去のやり取り履歴
- ブランドDNA

**Output**:
- 返信ドラフト(人間承認後送信)
- サイレントリードリスト
- 商談予約データ

**重要要件**:
- 自動送信は禁止(人間承認必須)
- 個別カスタマイズ(テンプレ感を排除)

### 4.7 Analyst(分析・学習)

**モデル**: Sonnet 4.6

**役割**:
- GA4データ分析
- Search Console分析
- 各SNS反応データ集約
- 勝ちパターン抽出
- Brain層への学習データ蓄積

**Input**:
- GA4 API データ
- Search Console データ
- 各SNS API データ
- 過去のパフォーマンスデータ

**Output**:
- 月次パフォーマンスレポート
- 勝ちパターンサマリー
- 次月戦略への提言
- KPI ダッシュボードデータ

### 4.8 Guardian(品質保証)

**モデル**: Opus 4.7(品質判定の重要性)

**役割**:
- 全出力の95点品質ループ
- ブランドDNA違反検出
- 法令遵守チェック(特定電子メール法、景表法、薬機法、著作権法等)
- 過剰約束防止
- 誤情報フィルタ

**Input**:
- 各エージェントの出力
- ブランドDNA
- 法令遵守ガイドライン

**Output**:
- 品質判定スコア(0-100)
- 違反検出レポート
- 改善指示(95点未満の場合、Drafter/Designer等に差し戻し)

**重要要件**:
- 95点未満は絶対に通さない
- 違反検出時は具体的な修正指示
- 神さんの教え:「逃げるな、95点に大丈夫?と聞き返せ」を実装

---

## 5. ワークフロー仕様

### 5.1 5フェーズワークフロー

```
Phase 1: コンテンツ集客(発信)
   Lead Strategist → 戦略立案
   Researcher → トレンド・キーワード調査
   Drafter → 記事/SNS投稿/動画台本生成
   Designer → ビジュアル生成
   Distributor → 全プラットフォーム配信
   Guardian → 95点品質ループ
   ↓
Phase 2: リード捕捉(受動)
   Connector → DM/コメント24時間応対
   Connector → サイレントリード抽出
   Analyst → 流入分析、LP通過率測定
   ↓
Phase 3: 能動営業(攻撃)
   Researcher → ターゲット企業・個人を能動探索
                  (PRタイムズ/Wantedly/X/LinkedIn)
   Researcher → 「儲かってそう」「決済権あり」を自動選別
   Drafter → 個別カスタマイズしたDM/メール/問合せフォーム文章生成
   Distributor → 個別チャネル別に配信(問合せフォーム自動投入含む)
   Guardian → スパム判定/法令遵守/トーン統制
   ↓
Phase 4: 商談・クロージング(成約)
   Lead Strategist → 個別商談の文脈理解、提案戦略立案
   Researcher → 該当顧客の業界・競合・直近動向を即座リサーチ
   Drafter → 提案書/見積書/契約書ドラフト生成(StoryGen AI技術応用)
   Designer → 提案書ビジュアル化
   Connector → 商談スケジューリング、フォローアップ自動化
   Analyst → 商談ボトルネック分析、勝率予測
   Guardian → 提案内容のリスク判定、過剰約束防止
   ↓
Phase 5: 学習ループ(全フェーズ横断)
   Analyst が全結果を集約 → Lead Strategist へFB
   勝ちパターンを「Brain層」に蓄積 → 次月以降の精度向上
```

### 5.2 1日のスケジュール(自動実行)

```
朝5:00  Researcher / Analyst が情報収集
        ・業界ニュース、競合動向、PR タイムズ新着
        ・SNS 反応集計(前日分)

朝7:00  Lead Strategist が顧客に「朝報」配信
        ・「今日の優先事項3つ」
        ・Slack / LINE / メールで配信

朝9-15時  生成フェーズ
        ・Drafter: 当日分記事執筆
        ・Designer: 図解・サムネ生成
        ・Researcher: 営業ターゲット50社更新
        ・Connector: 前日DM/コメント返信ドラフト準備

15:00  配信フェーズ
        ・Distributor: スケジューリング済みコンテンツ配信
        (顧客承認後)

夕方18:00  関係構築フェーズ
        ・Connector: 当日コメント・DM応対
        ・Researcher: サイレントリード抽出

夜22:00  学習フェーズ
        ・Analyst: 当日成果集約
        ・Lead Strategist: 翌日戦略更新

毎週月曜  ウィークリーレビュー
毎月最終週  マンスリーレビュー
```

### 5.3 顧客承認フロー

すべての対外的な配信は**人間承認必須**。

```
[Drafter生成] → [Guardian品質チェック95点] → [顧客承認待ちキュー]
                                                       ↓
                                           [顧客が承認/修正/却下]
                                                       ↓
                                    [Distributor が配信実行]
```

承認待ち通知:
- Slack
- LINE
- メール(オプション)

---

## 6. データ構造

### 6.1 Brain 層(永続記憶)

```
brain/
├── customers/              # 顧客ごとのデータ
│   └── {customer_id}/
│       ├── brand-dna.md    # ブランドDNA
│       ├── profile.json    # 顧客基本情報
│       └── kpi-targets.json
├── content-history/        # 全出力履歴
│   └── {customer_id}/
│       ├── notes/
│       ├── x-posts/
│       ├── instagram/
│       └── proposals/
├── leads/                  # リードデータベース
│   └── {customer_id}/
│       ├── active.json
│       ├── silent.json
│       └── archived.json
├── deals/                  # 商談履歴
│   └── {customer_id}/
│       ├── pipeline.json
│       └── closed.json
├── win-patterns/           # 勝ちパターン蓄積
│   └── {customer_id}/
│       ├── content-patterns.md
│       ├── outreach-patterns.md
│       └── closing-patterns.md
└── active.md               # 現在の進捗(リビングチェックポイント)
```

### 6.2 ブランドDNA構造

```yaml
# brand-dna.md (顧客ごと)
identity:
  name: "顧客名"
  business: "ビジネス内容"
  target_audience: "ターゲット顧客"
  unique_value_proposition: "独自の価値提案"

voice:
  tone: "カジュアル/プロフェッショナル/友好的"
  personality: "声の特徴"
  vocabulary: "好む言葉/避ける言葉"
  signature_phrases: "決まり文句"

content_strategy:
  pillar_topics: ["主要トピック1", "主要トピック2", "主要トピック3"]
  content_types: ["記事/動画/SNS"]
  publishing_frequency: "頻度"

forbidden:
  - "絶対に使わない表現"
  - "扱わないトピック"
  - "競合への言及"

reference:
  past_winning_content: "過去のヒットコンテンツ"
  competitor_examples: "参考にする競合(参考のみ)"
```

### 6.3 リード管理

```json
// leads/{customer_id}/active.json
{
  "lead_id": "lead_001",
  "source": "PRTimes / X / LinkedIn / Inbound",
  "company_name": "株式会社○○",
  "decision_maker": "山田太郎",
  "title": "代表取締役",
  "score": {
    "wealth": 85,
    "decision_authority": 90,
    "pain_signal": 75,
    "total": 83.3
  },
  "context": "直近のプレスリリース内容、痛み推定",
  "outreach_history": [
    {
      "date": "2026-05-10",
      "channel": "form",
      "message_id": "msg_001",
      "result": "no_reply"
    }
  ],
  "status": "warm / cold / archived",
  "next_action": "..."
}
```

---

## 7. 外部連携(MCP)

### 7.1 標準MCP接続(全Tier)

| サービス | 用途 | 必須/任意 |
|---------|------|----------|
| Notion | ブランドDNA管理、コンテンツカレンダー | 必須 |
| Google Drive | ドキュメント保存 | 必須 |
| Gmail | メール送信(承認後) | 必須 |
| X API | 投稿、トレンド取得 | 必須 |
| Instagram Graph API | 投稿、分析 | 必須 |

### 7.2 拡張MCP接続(Tier 2以上)

| サービス | 用途 |
|---------|------|
| LinkedIn API | 投稿、リード探索 |
| GA4 | 分析 |
| Search Console | SEO分析 |
| WordPress | ブログ自動投稿 |
| LINE公式 API | 配信 |

### 7.3 オプションMCP接続

| サービス | 用途 | 顧客自己契約 |
|---------|------|------------|
| Higgsfield MCP | シネマ動画生成 | あり |
| MakeUGC API | UGC広告動画 | あり |
| Salesforce / HubSpot | CRM連携 | あり |

### 7.4 MCP接続フロー

```python
# .mcp.json (顧客リポジトリ)
{
  "mcpServers": {
    "notion": {
      "url": "https://mcp.notion.com/mcp",
      "auth": "oauth"
    },
    "higgsfield": {
      "url": "https://mcp.higgsfield.ai/mcp",
      "auth": "oauth",
      "optional": true
    }
  }
}
```

---

## 8. ブランドDNA仕様

### 8.1 設計思想

ブランドDNAは Virtus の魂。**顧客の声をそのまま再現するための設計図**。

### 8.2 構成要素

第一に、**Identity(同一性)**: 何者か
第二に、**Voice(声)**: どう話すか
第三に、**Content Strategy(戦略)**: 何を発信するか
第四に、**Forbidden(禁忌)**: 何をしないか
第五に、**Reference(参照)**: 過去の成功と参考事例

### 8.3 構築フロー

```
1. オンボーディング時
   ├─ 30問の構造化ヒアリング
   ├─ 過去コンテンツの分析(URL/PDF/画像から)
   └─ ブランドDNA初版生成

2. 月次調整
   ├─ Analyst が勝ちパターンを蓄積
   ├─ Guardian が違反検出時にFB
   └─ オーナーが MTG で調整

3. 四半期レビュー
   └─ ブランドDNA本体の見直し
```

### 8.4 galaiworks 独自IPの統合

Founding Member 向けには以下を選択肢として提供:

- **Garai Tone**(galaiworks執筆スタイル)
- **DREAM WRITING フレームワーク**
- **IMPACT v2.0R フレームワーク**

これらは顧客のブランドDNAと組み合わせて使用。

---

## 9. 品質管理(Guardian仕様)

### 9.1 95点ループ

```python
def guardian_quality_check(content):
    score = evaluate(content)

    if score >= 95:
        return APPROVED, content
    else:
        feedback = generate_specific_feedback(content)
        return REJECTED, feedback
```

### 9.2 評価軸(100点満点)

| 軸 | 配点 | 内容 |
|----|------|------|
| ブランドDNA遵守 | 25 | voice, tone, vocabulary一致 |
| 法令遵守 | 25 | 特定電子メール法、景表法、薬機法等 |
| 内容の質 | 20 | 論理性、有用性、独自性 |
| ターゲット適合 | 15 | 想定読者への適合度 |
| 過剰約束チェック | 10 | 「絶対」「必ず」等のリスク表現 |
| ハルシネーション検出 | 5 | 事実誤認の有無 |

### 9.3 違反パターンの検出

```yaml
critical_violations:
  - 法令違反(即停止)
  - 個人情報漏洩リスク
  - 過剰な医療効果訴求(薬機法)
  - 虚偽表示(景表法)

major_violations:
  - ブランドDNA voice 不一致
  - ターゲット層へのミスマッチ
  - 競合ディスり

minor_violations:
  - 表記ゆれ
  - 文体の混在
  - SEO最適化不足
```

### 9.4 神さんの教え実装

> 「逃げるな、95点に大丈夫?と聞き返せ」

Guardian は**常に厳しい目で見る**。「これで本当に95点ですか?」と問い返す。

---

## 10. セキュリティ・法令遵守

### 10.1 法令遵守(必須)

第一に、**特定電子メール法**: 営業メールには連絡先・解除動線必須
第二に、**景品表示法**: 過剰表示・虚偽表示禁止
第三に、**薬機法**: 医療効果の過剰訴求禁止
第四に、**著作権法**: 他者コンテンツの無断使用禁止
第五に、**個人情報保護法**: 顧客データの適切管理
第六に、**プラットフォーム規約**: 各SNSの規約遵守

### 10.2 セキュリティ要件

```yaml
api_keys:
  storage: 顧客のローカル.envのみ
  galaiworks_server: 永続保存しない
  transmission: HTTPS必須

customer_data:
  encryption: at-rest, in-transit
  access_control: 顧客本人 + galaiworks(運用時のみ)
  retention: 契約期間 + 6ヶ月、その後完全削除
  
audit_log:
  - すべてのエージェント実行ログ
  - すべての配信ログ
  - すべてのデータアクセスログ
```

### 10.3 自動化の境界

**禁止事項**:
- ブラウザ自動化での投稿(規約違反)
- 自動DM大量送信(スパム判定リスク)
- 個人情報の無断収集
- 顔画像の無断使用

**許可事項**:
- 公式API経由の投稿(承認後)
- 個別カスタマイズされた営業メール(承認後)
- 公開情報のリサーチ
- 商談前ブリーフィング

---

## 11. 実装ロードマップ

### 11.1 Phase 1: Founding Members 向け実装(2026年5-7月)

**スコープ**:
- 8体エージェント基本実装
- Claude Code環境での動作
- Notion / Drive / X / Instagram MCP接続
- 5フェーズワークフローの基本動作
- ブランドDNA構築フロー
- 95点品質ループ

**完了条件**:
- Founding Member 30名のオンボーディングが可能
- 1日のスケジュール自動実行が動作
- ウィークリーレビュー / マンスリーレビュー出力

### 11.2 Phase 2: 軽量Web UI(2026年8-10月)

**スコープ**:
- クライアントサイドBYOK Web UI
- APIキー入力画面(ローカル保存)
- 8体エージェント実行UI
- 出力結果プレビュー
- 履歴管理(直近30日、サーバー保存)
- スケジュール実行

**技術スタック**:
- Next.js 14
- Supabase (auth, minimal data only)
- Vercel deployment
- Tailwind CSS

### 11.3 Phase 3: マルチLLM対応フルSaaS(2026年11月-2027年3月)

**スコープ**:
- Anthropic / Google AI / OpenAI 切替
- エージェントごとにLLM選択可能
- リッチダッシュボード
- モバイル対応
- Stripe課金統合
- チームアカウント、権限管理

### 11.4 Phase 4: エンタープライズ対応(2027年Q2以降)

**スコープ**:
- ホワイトラベル
- SSO (SAML, OIDC)
- SOC 2 Type II 取得
- IT導入補助金対象認定
- 監査ログ、コンプライアンス機能

---

## 12. Phase 1 実装スコープ

### 12.1 必須機能(Founding Members向け)

#### 12.1.1 エージェント実装

すべての8体エージェントを Claude Code で実装。Anthropic API直接呼び出し。

```python
# agents/lead_strategist.py
from anthropic import Anthropic

class LeadStrategist:
    def __init__(self, api_key, brand_dna):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-opus-4-7"
        self.brand_dna = brand_dna
    
    def morning_brief(self, context):
        # 朝報生成
        ...
    
    def weekly_review(self, week_data):
        # ウィークリーレビュー
        ...
```

#### 12.1.2 オーケストレーション

```python
# orchestrator.py
class VirtusOrchestrator:
    def __init__(self, customer_id):
        self.lead_strategist = LeadStrategist(...)
        self.researcher = Researcher(...)
        self.drafter = Drafter(...)
        # ... 8体すべて

    def run_daily_workflow(self):
        # 朝5時: 情報収集
        # 朝7時: 朝報配信
        # 朝9-15時: 生成フェーズ
        # 15時: 配信フェーズ
        # 18時: 関係構築フェーズ
        # 22時: 学習フェーズ
        ...
```

#### 12.1.3 スケジューラー

```python
# scheduler.py
import schedule
import time

def main():
    schedule.every().day.at("05:00").do(morning_research)
    schedule.every().day.at("07:00").do(send_morning_brief)
    schedule.every().day.at("09:00").do(content_generation)
    schedule.every().day.at("15:00").do(distribution)
    schedule.every().day.at("18:00").do(relationship_building)
    schedule.every().day.at("22:00").do(learning_loop)
    
    schedule.every().monday.at("09:00").do(weekly_review)
    
    while True:
        schedule.run_pending()
        time.sleep(60)
```

#### 12.1.4 Brain 層管理

```python
# brain/manager.py
class BrainManager:
    def save_content(self, content_type, content, metadata):
        ...
    
    def retrieve_pattern(self, pattern_type):
        ...
    
    def update_winning_patterns(self, performance_data):
        ...
```

### 12.2 Phase 1 で **実装しない** もの

- Web UI(Phase 2)
- 課金システム(別途請求書ベース)
- マルチLLM対応(Phase 3)
- モバイルアプリ(Phase 3以降)
- ホワイトラベル(Phase 4)

### 12.3 必須スキル(galaiworks独自IP)

```
skills/
├── garai-tone/
│   ├── SKILL.md
│   └── examples/
├── dream-writing/
│   ├── SKILL.md
│   ├── framework.md
│   └── examples/
└── impact-v2-0r/
    ├── SKILL.md
    ├── template.md
    └── examples/
```

---

## 13. リポジトリ構造

```
virtus/
├── README.md                       # プロダクト概要
├── REQUIREMENTS.md                 # 本要件定義書
├── CHANGELOG.md                    # バージョン履歴
├── LICENSE                         # ライセンス
├── .gitignore
├── .env.example                    # APIキー雛形
│
├── .claude/                        # Claude Code設定
│   ├── CLAUDE.md                   # プロダクト全体の指示書
│   ├── rules/
│   │   ├── brand-dna.md           # 顧客ごとのブランドDNA(差し替え)
│   │   ├── compliance.md          # 法令遵守ルール
│   │   ├── quality-95.md          # Guardian 95点ループ仕様
│   │   ├── escalation.md          # エスカレーション条件
│   │   └── communication.md       # 顧客コミュニケーションルール
│   ├── agents/
│   │   ├── lead-strategist.md     # サブエージェント定義
│   │   ├── researcher.md
│   │   ├── drafter.md
│   │   ├── designer.md
│   │   ├── distributor.md
│   │   ├── connector.md
│   │   ├── analyst.md
│   │   └── guardian.md
│   ├── skills/
│   │   ├── garai-tone/
│   │   ├── dream-writing/
│   │   ├── impact-v2-0r/
│   │   ├── content-engine/
│   │   ├── active-prospecting/    # PRタイムズ自動探索
│   │   ├── personalized-outreach/ # 個別営業文生成
│   │   ├── deal-strategy/         # 商談戦略
│   │   ├── proposal-generator/    # 提案書自動生成
│   │   ├── silent-lead-capture/
│   │   └── analytics-loop/
│   └── commands/                   # スラッシュコマンド
│       ├── morning-brief.md
│       ├── weekly-review.md
│       ├── monthly-review.md
│       └── deploy-content.md
│
├── src/                            # 実装コード
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                 # 基底クラス
│   │   ├── lead_strategist.py
│   │   ├── researcher.py
│   │   ├── drafter.py
│   │   ├── designer.py
│   │   ├── distributor.py
│   │   ├── connector.py
│   │   ├── analyst.py
│   │   └── guardian.py
│   ├── orchestrator.py
│   ├── scheduler.py
│   ├── brain/
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   └── storage.py
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── notion.py
│   │   ├── drive.py
│   │   └── higgsfield.py
│   └── utils/
│       ├── logger.py
│       ├── config.py
│       └── validators.py
│
├── brain/                          # 永続記憶層(.gitignore対象、顧客固有)
│   ├── customers/
│   ├── content-history/
│   ├── leads/
│   ├── deals/
│   ├── win-patterns/
│   └── active.md                   # 現在進捗
│
├── tests/                          # テストコード
│   ├── test_agents/
│   ├── test_orchestrator.py
│   └── test_brain.py
│
├── scripts/                        # 運用スクリプト
│   ├── onboard_customer.py        # 顧客オンボーディング
│   ├── generate_brand_dna.py      # ブランドDNA生成
│   ├── daily_run.py               # 日次実行
│   └── monthly_report.py          # 月次レポート生成
│
├── docs/                           # ドキュメント
│   ├── ONBOARDING.md              # 顧客オンボーディングガイド
│   ├── ARCHITECTURE.md            # アーキテクチャ詳細
│   ├── SECURITY.md                # セキュリティ仕様
│   └── TROUBLESHOOTING.md         # トラブルシューティング
│
└── logs/                           # 実行ログ(.gitignore対象)
    ├── daily/
    ├── weekly/
    └── errors/
```

---

## 14. 運用フロー

### 14.1 顧客オンボーディング

```
Day 0: 契約締結
   ↓
Day 1-3: 環境構築(完全代行)
   ├─ Anthropic API キー取得サポート
   ├─ Claude Code セットアップ
   ├─ リポジトリ clone
   ├─ MCP接続設定(Notion, Drive, X, Instagram)
   └─ 基本動作確認

Day 4-5: ブランドDNA構築
   ├─ 30問ヒアリングMTG (60分)
   ├─ 過去コンテンツ分析
   └─ brand-dna.md 初版作成

Day 6-7: 試運転
   ├─ サンプルコンテンツ生成
   ├─ オーナーが品質確認
   └─ 微調整

Day 8: 本格運用開始
   └─ 1日のスケジュール自動実行開始
```

### 14.2 月次運用フロー

```
月初:
- Lead Strategist が月次戦略書発行
- 顧客との戦略MTG (60分、Tier 2以上は2回)

毎日:
- 自動実行(朝5時から夜22時)
- 顧客は朝報チェック、コンテンツ承認のみ

毎週月曜:
- ウィークリーレビュー配信
- 必要に応じて MTG (30-60分)

月末:
- マンスリーレビュー
- 次月戦略の擦り合わせ
- KPI 振り返り
```

### 14.3 トラブル対応

```
レベル1: 軽微なバグ
   - エージェント側で自動再試行
   - ログ記録

レベル2: 機能停止
   - galaiworks に自動通知
   - 24時間以内に対応

レベル3: 重大インシデント(API漏洩等)
   - 即時停止
   - 顧客に48時間以内に報告
   - 法的対応検討
```

---

## 15. 非機能要件

### 15.1 パフォーマンス

| 項目 | 目標値 |
|------|-------|
| note記事生成 | 5分以内 |
| X投稿生成 | 1分以内 |
| 朝報生成 | 3分以内 |
| マンスリーレビュー | 15分以内 |
| API レイテンシ | 平均 < 30秒 |

### 15.2 可用性

- Phase 1: 顧客のローカル環境のため、オーナーのPC稼働状況に依存
- Phase 2以降: 99.5%稼働率目標

### 15.3 拡張性

- 顧客追加時の工数: 1顧客あたり 5-7時間(オンボーディング)
- 新エージェント追加: 1体 198,000円 / 約20時間
- 新スキル追加: 1スキル 98,000円 / 約10時間

### 15.4 保守性

- すべてのコードは型ヒント付き Python 3.11
- 自動テストカバレッジ 70% 以上
- ドキュメント駆動開発

---

## 16. Founding Member 専用要件

### 16.1 Founding Member 30名向け追加要件

#### 16.1.1 共創開発フロー

```
月次フィードバックサイクル:
  Week 1: Founding Member が機能を活用
  Week 2: フィードバックアンケート提出
  Week 3: galaiworks がアンケート集計、優先順位付け
  Week 4: 改善版リリース、月次MTGで共有
```

#### 16.1.2 限定特典の実装

```yaml
founding_member_benefits:
  full_features:
    - all_8_agents: true
    - higgsfield_integration: free
    - makeugc_integration: free
    - tier_3_equivalent_features: true
  
  pricing:
    initial_fee: 49800
    monthly_fee: 9800
    forever_discount: 50%  # 正規版移行後も生涯50%割引
  
  meetings:
    monthly_60min: 12       # 12ヶ月分
    
  upgrade_rights:
    phase_2_upgrade: free
    phase_3_upgrade: free
    
  recognition:
    title: "Founding Member"
    lp_listing: optional
    case_study: optional
```

#### 16.1.3 Founding Member ダッシュボード(将来)

Phase 2 Web UI で Founding Member 専用セクションを設置:
- 提案機能リスト(投票機能)
- 開発ロードマップ閲覧
- 他Founding Member との交流
- 限定コンテンツアクセス

### 16.2 Founding Member 募集要件

```yaml
募集要件:
  募集期間: 2026年6月4日(サミット当日) - 2026年8月末
  募集枠: 30名(最小10名で成立)
  
  対象条件:
    - 月1回30分のフィードバックMTG参加可能
    - 月1回フィードバックアンケート提出
    - 12ヶ月活用コミット
    - 改善提案を積極的に出す姿勢
  
  申込フロー:
    1. サミット視聴 → LINE登録
    2. ウェビナー参加(2026年6月15日予定)
    3. 申込フォーム記入
    4. 30分選考面談
    5. 30名選抜(超過時は galaiworks 選考)
    6. 契約 → オンボーディング
```

---

## 付録A: 開発開始チェックリスト

Phase 1 実装開始前の確認事項:

- [ ] Anthropic API アカウント取得済み
- [ ] Claude Code 最新版インストール
- [ ] Antigravity または別IDE の準備
- [ ] Git リポジトリ作成
- [ ] Notion ワークスペース準備
- [ ] テスト顧客(galaiworks自身)のブランドDNA草案
- [ ] galaiworks独自IP(Garai Tone等)のスキル化
- [ ] 月次運用予算の確認(Anthropic API)

---

## 付録B: 参考リソース

- Anthropic公式 Claude Code ドキュメント
- Anthropic Multi-Agent Research パターン
- 神さんの動画(AI CEO設計、5000万円事例、PRタイムズ自動営業)
- 49 Game Studios の Claude Code 実装事例
- SEO自動化7体エージェント
- Sintra、Sierra、Decagon 等海外マルチエージェント事例

---

## 付録C: 用語集

| 用語 | 意味 |
|------|------|
| BYOK | Bring Your Own Key、顧客が自分のAPIキーを使う方式 |
| MCP | Model Context Protocol、AIエージェントが外部ツールに接続する標準プロトコル |
| Brain層 | 顧客固有の永続記憶データ |
| ブランドDNA | 顧客の声・文体・戦略を再現するための設計図 |
| Garai Tone | galaiworks独自の執筆スタイル |
| 95点ループ | Guardian が品質95点未満を許さない品質管理プロセス |
| Founding Member | 共創パートナーとなる初期30名の限定枠 |

---

**文書終わり**
