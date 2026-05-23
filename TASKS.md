# Virtus タスクリスト

サミット（2026/6/4）に向けた Phase 1 実装タスク。

最終更新: 2026-05-23

---

## 進捗サマリー

| カテゴリ | 進捗 |
|---------|------|
| エージェント実装 | 1/8（Designer 完了） |
| 独自スキル | 0/3 |
| インフラ | 0/4 |
| サミットデモ | 1/5 |

---

## サミット 6/4 最優先（残り 12 日）

> CLAUDE.md の優先順位に基づく。PRタイムズ連携は除外。

| # | タスク | 担当 | 状態 | 期限 |
|---|--------|------|------|------|
| S1 | Drafter の Garai Tone 実装 | Drafter | 未着手 | 5/26 |
| S2 | Lead Strategist の朝報生成 | Lead Strategist | 未着手 | 5/28 |
| S3 | Guardian の 95 点ループ | Guardian | 未着手 | 5/30 |
| S4 | オーケストレーター連携 | Orchestrator | 未着手 | 6/2 |
| S5 | Designer 動画生成（PR #2） | Designer | **完了** | - |

---

## エージェント実装（8 体中 1 体完了）

### 完了

- [x] **Designer** - HyperFrames + Video-Use 統合 ([PR #2](https://github.com/galaiworks/Virtus/pull/2))

### 未着手

- [ ] **Lead Strategist** - 戦略統括・オーケストレーター
  - `claude-opus-4-7`
  - 朝報生成（毎朝7時配信）
  - 月次戦略書
  - 各エージェントへのタスク振り分け

- [ ] **Researcher** - 探索・調査
  - `claude-sonnet-4-6`
  - 業界動向調査
  - 競合分析
  - ※PRタイムズ機能は除外

- [ ] **Drafter** - 全コンテンツ執筆
  - `claude-sonnet-4-6`
  - Garai Tone スキル統合
  - DREAM WRITING フレームワーク
  - IMPACT v2.0R 構造

- [ ] **Distributor** - 配信処理
  - `claude-haiku-4-5`
  - X / note / Instagram 配信
  - スケジュール配信
  - 公式 API のみ使用

- [ ] **Connector** - DM・関係構築
  - `claude-sonnet-4-6`
  - DM 返信
  - エスカレーションキーワード検知
  - 感情分析

- [ ] **Analyst** - 分析・学習
  - `claude-sonnet-4-6`
  - 月次品質レビュー
  - ブランドDNA改善提案
  - エンゲージメント分析

- [ ] **Guardian** - 品質保証
  - `claude-opus-4-7`
  - 95 点ループ実装
  - 法令遵守チェック（compliance.md）
  - エスカレーション判断
  - 自己反省機構

---

## 独自スキル（Skills）

`.claude/skills/` 配下に SKILL.md として実装。

- [ ] **Garai Tone** - galaiworks 独自執筆スタイル
  - 「率直に言うと」「結論から言うと」等のシグネチャ
  - プロフェッショナル × 親近感 × 直球
  - 禁止表現フィルター

- [ ] **DREAM WRITING** - 三層ニーズ分析 + 多段 CTA
  - 顕在ニーズ / 潜在ニーズ / 願望
  - ファネル検出
  - ステップメール対応

- [ ] **IMPACT v2.0R** - 6セクション構造
  - Insight / Mechanism / Proof / Application / Conclusion / Transition
  - 論理性と説得力の両立

---

## インフラ

- [ ] **Orchestrator** (`src/orchestrator.py`)
  - エージェント間連携
  - タスクキュー管理
  - リトライ・エスカレーション
  - 95 点ループ統合

- [ ] **Scheduler** (`src/scheduler.py`)
  - 朝7時の朝報トリガー
  - 配信スケジュール管理
  - cron / APScheduler

- [ ] **Brain 層** (`brain/customers/{id}/`)
  - ブランドDNA 保存
  - 過去コンテンツ蓄積
  - 学習データ管理
  - `.gitignore` 必須

- [ ] **オンボーディングフロー**
  - 30 問ヒアリング（brand-dna.md 参照）
  - 過去コンテンツ voice 分析
  - brand-dna.yaml 自動生成

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

- [ ] **統合テスト** - エージェント間連携
- [ ] **E2E テスト** - 1日のワークフロー全体
- [ ] **CI 設定** - GitHub Actions（pytest、ruff、mypy）
- [ ] **カバレッジ目標** - 80% 以上

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
