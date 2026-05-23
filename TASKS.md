# Virtus タスクリスト

サミット（2026/6/4）に向けた Phase 1 実装タスク。

最終更新: 2026-05-23

---

## 進捗サマリー

| カテゴリ | 進捗 |
|---------|------|
| エージェント実装 | **8/8 完了** |
| 独自スキル統合 | **3/3 完了**（Drafter経由） |
| インフラ | **4/4 完了**（Orchestrator/Scheduler/Skills loader/Brain層） |
| サミットデモ | 4/5 |

---

## サミット 6/4 最優先（残り 12 日）

> CLAUDE.md の優先順位に基づく。PRタイムズ連携は除外。

| # | タスク | 担当 | 状態 | 期限 |
|---|--------|------|------|------|
| S1 | Drafter の Garai Tone 実装 | Drafter | **完了** | - |
| S2 | Lead Strategist の朝報生成 | Lead Strategist | **完了** | - |
| S3 | Guardian の 95 点ループ | Guardian | **完了** | - |
| S4 | オーケストレーター連携 | Orchestrator | **完了** | - |
| S5 | Designer 動画生成（PR #2） | Designer | **完了** | - |

---

## エージェント実装（8 体中 1 体完了）

### 完了（全 8 体）

- [x] **Designer** - HyperFrames + Video-Use 統合 ([PR #2](https://github.com/galaiworks/Virtus/pull/2))
- [x] **Lead Strategist** - 朝報、週次/月次レビュー、タスク分配
- [x] **Researcher** - トレンド調査、競合監視、SEO キーワード調査
- [x] **Drafter** - note記事、X投稿、メール、提案書、カルーセル、YouTube台本（Garai Tone/DREAM/IMPACT 統合）
- [x] **Distributor** - スケジュール配信、配信タイミング最適化、特定電子メール法準拠
- [x] **Connector** - DM返信、コメント返信、エスカレーション検知、フォローアップ計画
- [x] **Analyst** - 月次レポート、KPI ダッシュボード、パターン抽出
- [x] **Guardian** - 95 点ループ、法令遵守チェック、自己反省機構

---

## 独自スキル（Skills）

`.claude/skills/` 配下に既存。`SkillLoader` 経由で Drafter に統合済み。

- [x] **Garai Tone** - galaiworks 独自執筆スタイル（Drafter システムプロンプトに自動注入）
- [x] **DREAM WRITING** - 三層ニーズ分析 + 多段 CTA
- [x] **IMPACT v2.0R** - 6セクション構造

---

## インフラ

- [x] **Orchestrator** (`src/orchestrator.py`)
  - エージェント間連携
  - `write_and_review` で Drafter ↔ Guardian 95点ループ
  - `handle_incoming_message` で Connector + Guardian
  - `full_content_pipeline` でマルチプラットフォーム

- [x] **Scheduler** (`src/scheduler.py`)
  - 朝7時の朝報トリガー
  - 平日のみ実行オプション
  - `build_default_scheduler` でデフォルト構成

- [x] **SkillLoader** (`src/skills.py`)
  - `.claude/skills/` から自動読み込み
  - `format_brand_dna` でプロンプト整形

- [x] **Brain 層** (`brain/customers/{id}/`, `src/brain.py`)
  - ブランドDNA 保存 (`BrandDNA` dataclass)
  - 過去コンテンツ蓄積 (`ContentRecord`, `list_content`)
  - 学習データ管理 (`save_learning_data`, `load_learning_data`)
  - 監査ログ (`append_log`, `read_logs`)
  - `.gitignore` 設定済み

- [x] **オンボーディングフロー** (`src/onboarding.py`)
  - 30 問ヒアリング（`HEARING_QUESTIONS`）
  - 過去コンテンツ voice 分析（`analyze_past_content`）
  - brand-dna.yaml 自動生成（`generate_brand_dna`）

---

## 動画生成パイプライン拡張（Designer 続き）

- [ ] **TTS 統合** - Kokoro 経由
- [ ] **Whisper 文字起こし統合**
- [ ] **背景除去** - u2net 経由
- [ ] **テロップ自動追加** - Whisper → 字幕焼き込み
- [ ] **Higgsfield MCP 統合**（Tier 2 オプション）
- [ ] **MakeUGC 統合**（Tier 2 オプション）

---

## テスト・品質

- [x] **統合テスト** - エージェント間連携 (`tests/test_integration.py`)
- [ ] **E2E テスト** - 1日のワークフロー全体
- [x] **CI 設定** - GitHub Actions（pytest、ruff、mypy）`.github/workflows/ci.yml`
- [ ] **カバレッジ目標** - 80% 以上（現在推定 72%、98テスト）

---

## ドキュメント

- [ ] **README.md** - プロジェクト概要、クイックスタート
- [ ] **CONTRIBUTING.md** - 開発参加ガイド
- [ ] **API.md** - 各エージェントの API リファレンス
- [ ] **DEMO.md** - サミットデモ手順書

---

## サミットデモシナリオ

> Drafter + Lead Strategist + Guardian + Designer の連携を見せる。

```
1. Lead Strategist が朝報生成（毎朝7時想定）
   ↓
2. Drafter が note 記事を執筆（Garai Tone 適用）
   ↓
3. Guardian が 95 点ループでチェック
   ↓
4. Designer がサムネイル + ショート動画生成
   ↓
5. （Distributor は手動承認後配信）
```

- [ ] デモ用ブランドDNA（galaiworks 自身）整備
- [ ] デモシナリオ動画録画
- [ ] スライド資料（galai-tone + impact-v2-0r で生成）
- [ ] バックアップシナリオ（API障害時用）

---

## Phase 2 以降（参考）

- Web UI
- マルチ LLM 対応
- 課金システム
- Slack / LINE 配信統合
- iOS / Android アプリ

---

## 直近1週間のアクション

| 日付 | 優先タスク |
|------|-----------|
| 5/24（土） | Drafter スケルトン + Garai Tone スキル |
| 5/25（日） | Garai Tone 実装完成 + Drafter テスト |
| 5/26（月） | Lead Strategist スケルトン + 朝報生成 |
| 5/27（火） | 朝報フォーマット完成 + brand-dna 連携 |
| 5/28（水） | Guardian スケルトン + 評価マトリクス |
| 5/29（木） | 95 点ループ + 自己反省実装 |
| 5/30（金） | Orchestrator 連携 + 統合テスト |

---

## ブロッカー・懸念事項

- [ ] Anthropic API キー使用量・コスト見積もり
- [ ] HyperFrames の Docker 環境セットアップ
- [ ] サミット会場のネットワーク帯域確認
- [ ] デモ用素材（音声、画像）の準備
