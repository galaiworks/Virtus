# Auto Routing — MCP 自動選択 / モデル・エフォート自動調整

このファイルは、Virtus リポジトリでの作業中に Claude Code が
**どの MCP を使い、どのモデル・エフォートで実行するか**を自動判断するための規約です。

`.claude/settings.json` の SessionStart / UserPromptSubmit フックが
毎セッション・毎プロンプトでこの規約を読み込ませます。

---

## 基本原則

第一に、**道具はタスクが決める**。MCP はユーザーが指名しなくてもタスク種別から選ぶ。

第二に、**燃費と品質を両立する**。全部を Opus で回さない。全部を Haiku で回さない。

第三に、**迷ったら上のティアに倒す**。不可逆・対外・法令リスクのある作業は必ず T3。

第四に、**対外出力は必ず Guardian を通す**。95 点ループは省略しない。

---

## 1. 複雑度ティアとモデル/エフォート

| ティア | 判定 | モデル | エフォート | 例 |
|-------|------|-------|-----------|-----|
| **T0** | 機械的・判断不要 | `haiku` | `low` | ファイル整形、リネーム、ログ抽出、配信実行 |
| **T1** | 単一ファイル・仕様明快 | `sonnet` | `medium` | 関数追加、テスト追加、定型調査、SNS 投稿下書き |
| **T2** | 複数ファイル・設計判断あり | `sonnet` | `high` | モジュール追加、リファクタ、note 記事執筆、提案書 |
| **T3** | アーキテクチャ・法令・対外品質 | `opus` | `high`〜`xhigh` | 全体設計、Guardian 95 点評価、コンプラ判断、契約・価格 |

### ティア判定シグナル

上に倒す(T2→T3)シグナル:
- 触るファイルが 5 つ以上、またはディレクトリ構造が変わる
- **不可逆**(送信、公開、課金、削除、push)
- **法令・ブランドリスク**(景表法、薬機法、特電法、ブランドDNA 違反)
- 未知の領域・前例のないパターン
- 失敗時に人間が気づけない

下に倒す(T2→T1)シグナル:
- 既存パターンの複製で済む
- テストが即座に正否を判定する
- ロールバックが 1 コマンドで済む

---

## 2. MCP ルーティング表

ユーザーが MCP を指名しなくても、タスク種別から以下を選ぶ。
接続されていない場合はその旨を伝え、代替(ローカル操作 / WebFetch)に落とす。

| タスク | 第一選択 MCP | 補助 |
|-------|------------|------|
| 仕様書・議事録・ナレッジの読み書き | Notion | Google Drive |
| ファイル・資料の保管/共有 | Google Drive | Notion |
| コード・PR・Issue・CI | github | — |
| 顧客リスト・リード管理・スコアリング | Airtable | Supabase |
| DB スキーマ・マイグレーション・SQL | Supabase | — |
| 通知・エスカレーション・社内連携 | Slack | Gmail |
| メール送受信・営業メール下書き | Gmail | — |
| 商談・打合せの日程 | Google Calendar | Zoom for Claude |
| 商談録画・文字起こし | Zoom for Claude | — |
| ビジュアル・スライド・LP デザイン | Canva | Figma |
| デザインシステム・UI 実装連携 | Figma | Canva |
| デプロイ・ホスティング | Vercel | Netlify |
| 認証基盤 | Clerk | — |
| 外部情報の一次調査 | WebSearch / WebFetch | — |

### 選択ルール

1. **読む前に書かない**。書き込み系 MCP(Notion 更新、Slack 送信、Gmail 送信、Airtable 更新)は、
   対象を読んで現状を確認してから実行する。
2. **対外送信は人間承認**。Slack/Gmail/SNS への送信は `escalation.md` の Level 判定に従う。
3. **複数候補がある場合は第一選択**。ユーザーが別を指名したらそれに従う。
4. **ツールが見つからない場合は ToolSearch で探す**。「使えない」と即断しない。

---

## 3. 実装メカニズム(Claude Code の制約と回避策)

### 制約(2026-09 時点 / Claude Code v2.1.x)

- **セッション自身のモデル・エフォートは Claude 自身では変更できない。**
  変更経路は `/model`・`/effort`・`--model`・`--effort`・`CLAUDE_CODE_EFFORT_LEVEL`・
  settings の `model` / `effortLevel` / `modelSettings` のみ。
- **フックもモデル・エフォートを変えられない**(`additionalContext` でコンテキスト注入のみ)。

### 回避策 — サブエージェント委任でティアを実現する

サブエージェント定義(`.claude/agents/*.md`)の frontmatter は
`model` と `effort` を持ち、**セッションの設定を上書きする**。
したがってティアの切替は「その仕事に合ったエージェントへ委任する」ことで行う。

```yaml
---
name: distributor
model: haiku      # T0
effort: low
---
```

Agent ツール呼び出し時の `model` パラメータでも都度上書きできる。

### セッション既定値の決め方

- 既定は `sonnet` / `medium`(T1)で開始し、T3 の作業に入る前に `/model opus` `/effort high` に上げる。
- 恒久的に変えたい場合は `.claude/settings.local.json`(個人・gitignore 対象)に記述する:

```json
{
  "model": "sonnet",
  "modelSettings": {
    "claude-opus-5": { "effortLevel": "high" },
    "claude-sonnet-5": { "effortLevel": "medium" }
  }
}
```

---

## 4. Virtus エージェントのティア対応

| エージェント | モデル | エフォート | ティア |
|------------|-------|-----------|-------|
| Lead Strategist | opus | high | T3 |
| Guardian | opus | xhigh | T3 |
| Drafter | sonnet | high | T2 |
| Researcher | sonnet | medium | T1-T2 |
| Designer | sonnet | medium | T1-T2 |
| Connector | sonnet | medium | T1-T2 |
| Analyst | sonnet | medium | T1-T2 |
| Distributor | haiku | low | T0 |

frontmatter ではエイリアス(`opus` / `sonnet` / `haiku`)を使う。
最新世代に自動追従するため、日付付きモデル ID は書かない。

> 注: `CLAUDE.md` の 8 体表に書かれたモデル ID は
> **Virtus プロダクトが Anthropic SDK 経由で呼ぶ実行時モデル**であり、
> ここで扱う Claude Code サブエージェントのモデルとは別レイヤーです。
