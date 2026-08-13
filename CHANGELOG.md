# Changelog

本プロジェクトの変更履歴。

## [Unreleased]

### Added — AIエージェントチームMVP v0.1(`apps/agent-team-mvp/`)

『AIエージェントチームMVP 要件定義書 v1.0』『同 作業手順書 v1.0』を実装。
会議録と許可済み資料から、根拠付きの社内週報・タスク候補・メール草案を作り、
人間の承認を通じて業務へ戻す 4 エージェント構成。

Virtus(8 体・Python)/ Officina とはエージェント構成・スコープ・技術要件が異なる
別プロダクトのため、`apps/agent-team-mvp/` に TypeScript のモジュラーモノリスとして分離した
(判断の経緯は `apps/agent-team-mvp/docs/DECISIONS.md` D-001)。

- **出力契約**(手順書 C-1):`case_brief` / `evidence_bundle` / `work_draft` /
  `qa_result` / `approval_packet` を Zod で検証。共通ヘッダに `status` / `facts` /
  `uncertainties` / `log_refs` / `next_action`。
- **固定順序ワークフロー**(C-2):統括 → ナレッジ/データ → 業務改善 → 品質/承認。
  並列化・自律再計画は評価データで必要性が確認されるまで導入しない。
- **状態機械**(C-3 / FR-020〜022):9 状態 + `human_review_required`。
  FR-021 の優先順(security > authorization > fact conflict > approval >
  clarification > revision > pass)で最も強い状態を採る。
  同一カテゴリ・同一根本原因の自動差戻しは 2 回まで。
- **HITL**(FR-030〜034 / D-3):Slack Block Kit カード + 署名・タイムスタンプ検証。
  カードの `approve` をそのまま実行せず、本人・ロール・状態・期限・カード版数・
  nonce・scope をサーバー側で再検証してから限定実行する。
- **限定実行**(FR-040 / FR-041):Green は可逆な社内操作のみ。外部メール送信・
  CRM 確定更新等は承認後も人間実行へ引き渡す。冪等性キーで二重実行を防ぐ。
- **監査**(FR-042):`case_id` から根拠・承認・実行・状態遷移を時系列で再現できる。
- **根拠付与率**(G2):重要な数値・日付・決定事項の抽出と突合を決定論で行い、
  LLM には文章化と指摘追加だけを任せる(DECISIONS.md D-002)。
- **テスト**:ユニット / エージェント統合 / HITL 統合 / 実行統合 / UAT の 5 層、113 ケース。
  代表 20 件の評価セットと HITL 5 件(権限外・期限切れ・二重操作・古いカード・
  scope 拡張)が全件合格。

### Added — Officina v0.3(§12 オープン決定事項の確定)

要件定義 §12 の 5 点を「勝ち筋」で確定。

- **決定の単一真実源**(`src/officina/decisions.py`):`CONFIRMED`(ACV 帯=低 ACV 高
  ボリューム / 納品物=エージェント構築に絞る / シグナル層=外部連携 / 法人スキーム
  組込=有効 / deliverability=内製)。各決定に根拠(`rationale`)を付与。
- **納品物の標準型**(`src/officina/deliverables.py`・§12-2 / §8.4):エージェント構築に
  絞り、受入テストテンプレートを定義。士業独占業務は自律納品の対象外。
- **シグナル層アダプタ**(`src/officina/signals.py`・§12-3):外部連携/自前を切替できる
  `SignalSource` 境界。Prospector が `signal_source` 経由で候補取得。実在性検証付き(§8.5)。
- **法人スキーム前提**(§12-4):`config.corporate_entity_active` +
  `corporate_entity_gate`。法人未設立なら契約締結ゲートに進めない(orchestrator に配線)。
- テストを 7 ケース追加(計 55 ケース全通過)。

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
