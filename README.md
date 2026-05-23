# Virtus

> ひとり社長専属の 8 体 AI エージェントチーム

[![Status: Phase 1](https://img.shields.io/badge/status-Phase%201-yellow)]()
[![Model: Claude](https://img.shields.io/badge/model-Claude%204.7-purple)]()
[![License: Proprietary](https://img.shields.io/badge/license-Proprietary-red)]()

---

## Virtus とは

**Virtus**(徳・卓越性)は、ひとり社長・コーチ・コンサル・専門家のための、集客→営業→クロージングまでを完全自動化する 8 体の AI エージェントチームです。

「労働時間で売る」働き方から「成果と仕組みで売る」働き方への転換を実現します。

---

## 8 体構成

| エージェント | 役割 |
|------------|------|
| 🎯 Lead Strategist | 戦略統括・オーケストレーター |
| 🔍 Researcher | 探索・調査・能動営業 |
| ✍️ Drafter | 全コンテンツ執筆 |
| 🎨 Designer | ビジュアル生成 |
| 📤 Distributor | 配信処理 |
| 💬 Connector | DM・関係構築 |
| 📊 Analyst | 分析・学習 |
| 🛡️ Guardian | 品質保証・95 点ループ |

---

## ドキュメント構造

```
virtus/
├── README.md                  # このファイル
├── REQUIREMENTS.md            # 要件定義書(必読)
├── CLAUDE.md                  # Claude Code 用指示書
├── .env.example               # 環境変数テンプレート
│
├── .claude/                   # Claude Code 設定
│   ├── agents/                # 8 体エージェント定義
│   │   ├── lead-strategist.md
│   │   ├── researcher.md
│   │   ├── drafter.md
│   │   ├── designer.md
│   │   ├── distributor.md
│   │   ├── connector.md
│   │   ├── analyst.md
│   │   └── guardian.md
│   ├── skills/                # 共通スキル
│   │   ├── garai-tone/
│   │   ├── dream-writing/
│   │   ├── impact-v2-0r/
│   │   ├── active-prospecting/
│   │   └── proposal-generator/
│   ├── rules/                 # ルール
│   │   ├── brand-dna.md
│   │   ├── compliance.md
│   │   ├── quality-95.md
│   │   └── escalation.md
│   └── commands/              # スラッシュコマンド
│       └── morning-brief.md
```

---

## はじめに

### 1. リポジトリのクローン

```bash
git clone <this-repo>
cd virtus
```

### 2. 環境変数の設定

```bash
cp .env.example .env
# .env ファイルを編集して、Anthropic API キーを設定
```

### 3. 顧客のブランドDNA設定

```bash
# brain/customers/{customer_id}/brand-dna.md を作成
# .claude/rules/brand-dna.md をテンプレートとして参照
```

### 4. 依存関係のインストール

```bash
pip install -e ".[dev]"
```

### 5. デモの実行

```bash
# モックモード（API呼び出しなし）
python scripts/demo.py --mock

# 実際のAPI使用
python scripts/demo.py --api-key YOUR_ANTHROPIC_API_KEY
```

### 6. テストの実行

```bash
pytest tests/ -v
```

### 7. Claude Code で開発開始

```bash
claude  # Claude Code を起動
```

Claude Code は `.claude/` ディレクトリの内容を自動的に認識します。
`CLAUDE.md` と `REQUIREMENTS.md` を最初に読み込むので、即座にコンテキストが揃います。

---

## 開発フェーズ

### 現在: Phase 1(Founding Members 向け実装)

**期間**: 2026年5月〜7月

**スコープ**:
- 8 体エージェントの基本実装
- Claude Code 環境での動作
- 5 フェーズワークフローの基本動作
- ブランドDNA構築フロー
- 95 点品質ループ

### Phase 2(2026年8-10月)
- クライアントサイド BYOK Web UI
- Next.js + Supabase + Vercel

### Phase 3(2026年11月-2027年3月)
- マルチ LLM 対応フル SaaS
- Anthropic / Google AI / OpenAI 切替

### Phase 4(2027年Q2 以降)
- エンタープライズ対応
- IT 導入補助金対象認定

詳細は [REQUIREMENTS.md](./REQUIREMENTS.md) を参照。

---

## ビジネスモデル

**BYOK(Bring Your Own Key)型**

顧客が Anthropic API キーを自己契約し、Virtus はエージェントロジックと運用伴走を提供します。

### 価格構造(2026年10月以降)

| Tier | 初期費用 | 月額 | 対象 |
|------|---------|------|------|
| Founding Member | 49,800円 | 9,800円 | 共創パートナー(初期30名限定) |
| Tier S | 98,000円 | 19,800円 | 個人事業主・年商500万以下 |
| Tier 1 | 198,000円 | 49,800円 | ひとり社長・年商500万-5,000万 |
| Tier 2 | 698,000円 | 198,000円 | 中堅事業者・年商5,000万-2億 |
| Tier 3 | 1,500,000円 | 398,000円 | 法人・年商2億以上 |

---

## サミット 6 月 4 日に向けたタスク

galaiworks のサミット登壇に向けた優先順位:

1. **デモシナリオ用の Researcher 能動探索**(PRタイムズ自動探索)
2. **Drafter の Garai Tone 実装**
3. **Lead Strategist の朝報生成**
4. **Guardian の 95 点ループ**
5. **オーケストレーター連携**

これら 5 つが動けばサミットでの実演デモが可能になります。

---

## 競合差別化

| 競合 | 差別化軸 |
|------|---------|
| いいねAI | SNS のみ → Virtus は集客→営業→クロージング統合 |
| NoimosAI | マーケのみ → Virtus は能動営業+クロージング機能 |
| JAPAN AI AGENT | 法人汎用 → Virtus はひとり社長最適化 |
| Sierra/Decagon | 海外英語圏 → Virtus は日本語対応 |

---

## ライセンス

Proprietary. All rights reserved.

galaiworks 独自 IP(Garai Tone、DREAM WRITING、IMPACT v2.0R)を含む。

---

## 連絡先

- **開発者**: galaiworks(ガライ)
- **会社**: galaiworks.inc
- **役職**: SHIFT AI 講師 / AI 開発エンジニア

---

## 謝辞

- **Anthropic**: Claude モデルと Claude Code の提供
- **神さん**: AI CEO 設計、PR タイムズ自動営業の啓発
- **サミット 6 月 4 日 主催プレダイ**: Virtus 公開機会の提供

---

**最後に**

Virtus は単なる SaaS ツールではありません。

ひとり社長が「労働時間で売る」働き方から「成果と仕組みで売る」働き方への転換を実現するためのパートナーです。

世界基準のアーキテクチャを、日本のひとり社長に。

galaiworks の信念です。
