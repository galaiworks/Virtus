# Officina Roster — 自律型エージェンシー OS のエージェント編成

Officina(`src/officina/`)は Virtus 8 体に加え、営業〜納品〜アフターを通す
エージェント編成を持つ。各エージェントの実装は `src/officina/agents/` に、
詳細設計は [docs/OFFICINA.md](../../docs/OFFICINA.md) を参照。

| ステージ | エージェント | 既存資産 | 主責務 | 合格ゲート | モデル |
|---------|------------|---------|--------|-----------|-------|
| 0 | Scout | Virtus: Researcher | ICP・市場リサーチ | ソース実在性 | Sonnet |
| 1 | Prospector | 新規(Clay 相当) | リスト・エンリッチ・シグナル | データ検証率・重複/不達除去 | Haiku |
| 2 | Outreach | Virtus: Distributor | 多 ch ファーストタッチ | deliverability・送信量上限 | Haiku |
| 3 | Qualifier | Virtus: Connector | 返信トリアージ | 分類信頼度・危険ワード | Sonnet |
| 4 | Discovery | Faber: Discovery | 要件・課題抽出 | 必須項目充足 | Opus |
| 5 | Proposer | Virtus: Drafter+Designer | 提案・見積・SOW | 価格ガードレール | Sonnet |
| 6 | Closer | 新規(補助役) | 反論対応・条件整理 | 高額は人間主導 | Opus |
| 🚩7 | (人間) | — | 契約署名 | **人間必須・不可逆** | — |
| 8 | Architect/Builder | Faber: Architect→Builder | 設計・実装・検証 | 受入テスト全通過 | Opus |
| 🚩9 | (人間) | — | 納品物 最終承認 | **人間必須・不可逆** | — |
| 10 | Delivery | 新規 | 引き渡し・初期設定 | 疎通テスト | Sonnet |
| 11 | Ops/Analyst | Virtus: Analyst | 請求・監視・アップセル | 課金トリガー・ドリフト | Sonnet |

横断:
- **Orchestrator**(Virtus: Lead Strategist)が全工程を分解・委任・統合する。
- **Guardian**(`GuardianGate`)が生成物を統合前に独立検証する(生成と検証の分離)。

ガバナンス 3 層(決定論ゲート / Guardian 独立検証 / 人間 HITL)はすべての
自律実行が必ず通る。詳細は `src/officina/governance/` と
`.claude/rules/quality-95.md` / `escalation.md` / `compliance.md` を参照。
