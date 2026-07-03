# Changelog

本プロジェクトの変更履歴。

## [Unreleased]

### Added — 税理士 AI エージェント(Tax Accountant / Zeirishi)

ひとり社長・フリーランスのバックオフィス支援として、記帳補助・情報提供・
書類整理・期限管理を行う税理士 AI エージェントを実装。CLAUDE.md 第四原則
「規約遵守を絶対視する」と神さんの教え「逃げるな」を税務ドメインに適用。

- **税理士法遵守ルール**(`.claude/rules/tax-compliance.md`):税理士業務は
  独占業務(税理士法第 52 条)。税務代理・税務書類の作成・個別の税務相談には
  一切踏み込まない境界を定義。免責事項・エスカレーション基準・監査ログ要件を規定。
- **エージェント定義**(`.claude/agents/tax-accountant.md`):役割・システム
  プロンプト・タスク種別・Guardian 連携を定義。
- **実装**(`src/agents/tax_accountant.py`・`BaseAgent` 継承):
  - **独占業務境界ゲート**(決定論):脱税幇助=`critical_violation`(Level 4・関与
    拒否)、税務代理/書類作成/税務調査=`escalate_to_zeirishi`(Level 3)、個別
    税務相談=`escalate_to_zeirishi`(Level 2)。LLM 解釈に委ねず if/then で強制。
  - **記帳補助**:取引内容 → 勘定科目候補(信頼度・要確認フラグ付き)。
  - **所得税概算**:令和6年度速算表 + 復興特別所得税(参考値・確定値でない旨明記)。
  - **インボイスチェック**:適格請求書 6 記載事項の有無 + 登録番号(T+13 桁)形式判定。
  - **月次記帳サマリー / 申告・納付期限リマインド**。
  - 全出力に免責事項を付与。オフライン(dry_run)で決定論的に動作。
- **ゼロトラスト権限**(`permissions.py`):`tax_accountant` は記帳補助・情報提供の
  み。`file_tax_return` / `tax_representation` / `create_tax_document`(税理士独占
  業務)を `HUMAN_ONLY_ACTIONS` に追加し、全エージェントで実行不可に。
- テストを 19 ケース追加(計 74 ケース全通過)。境界ゲートの「逃げない」停止・
  免責付与・決定論動作を検証。

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
