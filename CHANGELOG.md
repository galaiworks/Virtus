# Changelog

本プロジェクトの変更履歴。

## [Unreleased]

### Added — Officina v0.2(KPI・撤退基準・フェーズ計画)

- **KPI / 撤退基準**(`src/officina/metrics.py`・要件定義 §10):
  - `FunnelCounts` — 返信率 → 商談実施率(booked→held)→ クローズドウォンを実数で計測。
  - `gate_pass_rates` / `reject_recurrence_rate` — ゲート合格率・リジェクト再発率。
  - `KpiTracker.withdrawal_triggers` — スパム苦情率上昇 / 勝率のハイブリッド基準割れ /
    ゲート合格率下限割れ の撤退・見直しトリガー(§10.2)。
- **フェーズ計画**(`src/officina/phases.py`・要件定義 §11):Phase 1-3 の自律比率を定義。
  漸近線(契約署名・納品承認の 2 ゲート)は全フェーズで人間固定。import 時に
  「2 ゲート人間」「自律比率の単調増加」を自己検証。
- テストを 11 ケース追加(計 48 ケース全通過)。

### Added — Officina(自律型 AI エージェンシー OS)v0.1 実装

要件定義書 `自律型AIエージェンシーOS 要件定義 v0.1` を実装。

- **パイプライン**(`src/officina/pipeline.py`):営業リサーチ → 納品 →
  アフターまでの全 12 ステージを定義。人間必須ゲートは契約署名・納品承認の 2 点に
  固定し、import 時に自己検証。
- **オーケストレーター**(`src/officina/orchestrator.py`):案件をステージごとに
  分解・委任・統合(Orchestrator-Worker 型)。各ステージの合格ゲートを通し、
  人間ゲート/エスカレーションで停止・再開できる。
- **エージェント編成**(`src/officina/agents/`):Scout / Prospector / Outreach /
  Qualifier / Discovery / Proposer / Closer / ArchitectBuilder / Delivery / Ops。
  すべて `BaseAgent`(`src/agents/base.py`)を継承し、オフライン実行可能。
- **ガバナンス 3 層**(`src/officina/governance/`):
  - 決定論ゲート(送信量・価格・契約・デプロイ・課金)
  - deliverability 監視(バウンス/苦情/評価/ウォームアップ)
  - ゼロトラスト権限スコープ
  - Guardian 独立検証(95 点ループ・生成と検証の分離)
  - 人間 HITL ゲート(契約署名・納品承認)+ 例外エスカレーション
  - リジェクトログ = リグレッションテスト
- **デモ**(`scripts/officina_demo.py`):1 案件を 2 ゲートまで自律実行する E2E デモ。
- **テスト**(`tests/`):37 ケース。決定論ゲート・deliverability・Guardian・
  リジェクトログ・パイプライン・E2E をカバー。
- `docs/OFFICINA.md`、`.claude/agents/officina-roster.md`、`pyproject.toml`、
  `.env.example` の Officina 設定を追加。
