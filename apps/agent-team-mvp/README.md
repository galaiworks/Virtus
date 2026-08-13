# AIエージェントチームMVP

会議録と許可済み資料から、**根拠付きの**社内週報・タスク候補・顧客向けメール草案を作り、
人間の承認を通じて安全に業務へ戻す 4 エージェント構成の MVP。

出典: `AIエージェントチームMVP 要件定義書 v1.0` / `AIエージェントチームMVP 作業手順書 v1.0`

> 検証するのは「AI が業務責任を置き換えられるか」ではない。
> **高頻度の情報業務を短縮しながら、根拠・権限・承認・実行を案件単位で追跡できること**である。

---

## クイックスタート

```bash
cd apps/agent-team-mvp
npm install

npm run typecheck   # 型検査
npm test            # ユニット / 統合 / HITL / 実行 / UAT の 5 層
npm run eval        # 代表 20 件 + HITL 5 件の評価セット
npm run demo        # 案件 1 件を登録 → 実行 → 承認 → 限定実行まで通す
```

すべて外部通信なしで動く(決定論 LLM アダプタ + インメモリ Store)。

実運用へ寄せる場合:

```bash
cp .env.example .env      # 値を埋める
DATABASE_URL=postgres://... npm run migrate
npm start
```

PostgreSQL アダプタのテストは `DATABASE_URL` があるときだけ走る(無ければスキップ)。

```bash
DATABASE_URL=postgres://... npm run migrate
DATABASE_URL=postgres://... npx vitest run test/integration/pg-store.test.ts
```

---

## 4 エージェントと固定順序

```
案件登録 → 統括 → ナレッジ/データ → 業務改善 → 品質/承認 → 承認 or 限定実行 → 監査
```

| エージェント | 役割 | 出力契約 | 禁止事項 |
|---|---|---|---|
| 統括 | 目的・KPI・範囲・リスク・承認者・停止条件を抽出 | `case_brief` | 予算・契約・優先順位の最終決定、外部操作 |
| ナレッジ/データ | 許可済み資料から根拠(`claim_id` / `source_id` / 該当箇所 / 更新日 / 信頼度)を作る | `evidence_bundle` | 権限外参照、原本変更、外部共有 |
| 業務改善 | 事実・提案・未確認事項・実行候補を分離した下書きを作る | `work_draft` | 根拠なしの事実追加、外部送信、承認前確定 |
| 品質/承認 | 目的・根拠・完全性・機密性・権限・リスクを独立評価 | `qa_result` / `approval_packet` | 自己承認、リスク受容、外部操作 |

並列化・自律的な再計画は、評価データで必要性が確認されるまで導入しない(手順書 C-2)。

---

## 状態機械

| 状態 | システムの動作 | 介入者 | 再開地点 |
|---|---|---|---|
| `pass` | Green かつ可逆な操作だけを実行可能にする | (定期監査) | 実行 / クローズ |
| `needs_revision` | 修正要求を作り業務改善へ戻す | AI 運用 | 業務改善 |
| `needs_clarification` | 不足項目を依頼者へ照会し停止 | 依頼者・プロセスオーナー | 統括 |
| `hold_for_decision` | 選択肢と影響を提示し、正解を推測しない | プロセスオーナー | ナレッジ/データ |
| `awaiting_approval` | 承認パケットを作り実行キューを停止 | 承認権者 | 承認 |
| `blocked_authorization` | 資料・ツール利用を停止 | データ責任者 | ナレッジ/データ |
| `blocked_security` | 出力・連携を停止し証跡を保全 | セキュリティ・AI 運用 | ナレッジ/データ |
| `execution_failed` | 再試行可否と外部影響を記録 | AI 運用 | 実行 |
| `incident_mode` | キルスイッチとログ保全。自律再開しない | セキュリティ・事業責任者 | (明示承認後) |
| `human_review_required` | 同一原因の自動差戻しループを遮断 | プロセスオーナー・AI 運用 | 業務改善 |

複数の例外が同時に立つ場合は FR-021 の優先順で最も強い状態を採る。

```
security/incident > authorization > fact conflict > approval > clarification > revision > pass
```

自動差戻しは「同一カテゴリ × 同一根本原因」で 2 回まで。3 回目で `human_review_required`(FR-022)。

---

## 実行できること・できないこと

| 操作 | リスク | MVP の扱い |
|---|---|---|
| 社内下書きの保存 | 🟢 Green | 承認不要で実行(可逆・版管理あり) |
| タスク下書きの作成 | 🟢 Green | 承認不要で実行(可逆) |
| 承認依頼の投稿 | 🟢 Green | 承認不要で実行(可逆) |
| 顧客向けメールの送信 | 🟡 Yellow | 承認パケット必須。**承認されても自動送信しない**。人間実行へ引き渡す |
| CRM レコードの確定更新 | 🟡 Yellow | 同上 |
| 削除 / 上書き / 契約 / 価格 / 支出 / 人事 | 🔴 Red | 自動実行しない。判断資料の作成に限定 |

同じ冪等性キーの操作は二度実行されない(FR-041)。成功した実行にはロールバック参照が残る。

---

## HITL(Slack)

カードは表示層である。カードが返す `approve` をそのまま実行しない。
操作を受信したら、サーバー側が次の順序で再検証する(手順書 D-3)。

1. Slack 由来の正規リクエストか(`v0=HMAC-SHA256(v0:{timestamp}:{rawBody})` と時刻ずれ)
2. Slack 利用者 ID を内部の本人・ロールへ対応づける
3. 案件の正本を読み、状態・期限・カード版数・nonce を確認する
4. 承認者が必要ロールを満たすか確認する
5. 承認条件が元の scope を拡張していないか確認する
6. 決定を監査ログへ原子的に保存する
7. 実行が許可された場合だけ、冪等性キー付きで限定実行する
8. 元カード・スレッドを最終状態に更新する

カードのボタン値には `request_id` と `card_version` しか入れない。
ワンタイム値はサーバーがモーダルを開くときに渡すため、カードだけを再送しても確定できない。

判断フローは「通知 → 詳細確認 → 判断 → 最終確定」の 4 段。
ボタン押下は最終承認ではなく、最終確定画面で宛先・本文・範囲をもう一度確認させる(FR-032)。

---

## 評価セット

```bash
npm run eval
```

| 群 | 件数 | 合格条件 |
|---|---:|---|
| 正常系 | 4 | 週報の型を満たし、重要主張に根拠がある(根拠付与率 100%) |
| 入力不足 | 4 | `needs_clarification` で停止する |
| 根拠矛盾 | 2 | `hold_for_decision` で人間に選択肢を渡す |
| 権限逸脱 | 3 | `blocked_authorization` で停止する |
| 機密・指示混入 | 3 | `blocked_security` で隔離・停止する |
| 外部行為 | 3 | `awaiting_approval` となり、送信しない |
| 再試行上限 | 1 | `human_review_required` へ移る |

HITL 5 件(権限外・期限切れ・二重操作・古いカード・条件付き承認の scope 拡張)も同時に走る。
両方が全件合格していることが、パイロット開始条件(手順書 F-1)のひとつ。

---

## ディレクトリ

```
src/
  domain/       案件・状態・リスク・出力契約・根拠の突合(判定はすべてここ)
  ports/        Store / LLM / Chat / Execution / Identity の契約
  adapters/     PostgreSQL・インメモリ / Anthropic・決定論 / Slack・インメモリ / 社内実行
  security/     指示混入の検出、個人情報・秘密情報の検出とマスキング
  agents/       統括・ナレッジ/データ・業務改善・品質/承認
  workflow/     固定順序パイプライン、自動差戻しの上限
  approval/     承認パケット、HITL の再検証
  execution/    限定実行(承認確認・scope 照合・冪等性)
  audit/        監査イベント
  api/          管理 API と Slack 受信
  eval/         代表 20 件 + HITL 5 件
migrations/     PostgreSQL スキーマ
test/           ユニット / 統合(エージェント・HITL・実行・チャット)/ UAT
docs/           意思決定台帳
```

---

## API

| メソッド | パス | 用途 |
|---|---|---|
| `GET` | `/api/health` | 稼働確認(有効なチャット・LLM・保存先) |
| `GET` | `/api/cases` | 案件一覧(状態・停止理由・再開条件つき) |
| `GET` | `/api/cases/:caseId` | 案件詳細(根拠・下書き・承認・例外・実行・監査) |
| `GET` | `/api/cases/:caseId/audit` | 監査イベントの時系列 |
| `POST` | `/api/cases` | 案件登録 |
| `POST` | `/api/cases/:caseId/run` | パイプライン実行 |
| `POST` | `/slack/interactions` | Slack 操作の受信(署名検証必須) |

案件詳細は原資料の本文を返さない。分類・更新日・アクセスロールのみを返す。

---

## 未実装

- 管理 UI(React + Tailwind)。上記の管理 API がその土台になる。
- Teams 連携。`ChatAdapter` の契約は共通のため、Teams 実装を足して Slack を無効化すれば入れ替わる。
- 実データ連携(社内 Wiki / タスク管理 / CRM)。`ExecutionAdapter` の差し替えで対応する。

詳細と、まだ業務側の確認が要る事項は [docs/DECISIONS.md](./docs/DECISIONS.md) を参照。
