#!/usr/bin/env bash
# Virtus auto-routing policy injector.
#
# Injects the MCP-selection and model/effort policy into every session
# (SessionStart) and re-states the short form on every prompt (UserPromptSubmit).
# Hooks cannot change the model or effort level themselves, so this injects the
# routing policy and Claude applies it by delegating to the right subagent.
#
# Usage (settings.json): auto-routing.sh SessionStart | auto-routing.sh UserPromptSubmit
set -uo pipefail

event="${1:-SessionStart}"
cat >/dev/null 2>&1 || true   # drain stdin; payload is not needed

if [[ "$event" == "SessionStart" ]]; then
  read -r -d '' ctx <<'CTX' || true
[Virtus auto-routing / 常時有効]

1. MCP はユーザーの指名を待たずにタスク種別から選ぶ。
   仕様・ナレッジ=Notion / ファイル=Google Drive / コード・PR=github /
   リード・顧客管理=Airtable / DB・SQL=Supabase / 通知=Slack / メール=Gmail /
   日程=Google Calendar / 商談録画=Zoom / ビジュアル=Canva / UI=Figma /
   デプロイ=Vercel。見つからない時は ToolSearch で探してから判断する。
   書き込み系(Notion 更新・Slack/Gmail 送信・Airtable 更新)は読んでから書く。
   対外送信は .claude/rules/escalation.md の Level 判定に従う。

2. モデルとエフォートは複雑度ティアで切り替える。
   T0 機械的=haiku/low, T1 単一ファイル=sonnet/medium,
   T2 複数ファイル・設計判断=sonnet/high, T3 設計・法令・対外品質=opus/high〜xhigh。
   不可逆・法令/ブランドリスク・未知領域は必ず T3 に倒す。
   セッション自身のモデル/エフォートは変更できないため、
   ティア切替は .claude/agents/ のサブエージェントへの委任で行う
   (frontmatter の model / effort がセッション設定を上書きする)。
   T3 を主セッションで回す必要があるときは /model opus と /effort high を提案する。

3. 対外出力は必ず Guardian の 95 点ループを通す。

詳細: .claude/rules/auto-routing.md
CTX
else
  read -r -d '' ctx <<'CTX' || true
[Virtus auto-routing] MCP はタスク種別から自動選択(仕様=Notion / コード=github / リード=Airtable / DB=Supabase / 通知=Slack / メール=Gmail / 日程=Calendar / ビジュアル=Canva / デプロイ=Vercel)。複雑度ティアで委任先を選ぶ(T0 haiku・low / T1 sonnet・medium / T2 sonnet・high / T3 opus・high〜xhigh)。不可逆・法令リスクは T3。対外出力は Guardian 95 点ループ必須。
CTX
fi

CTX="$ctx" EVENT="$event" python3 -c '
import json, os
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": os.environ["EVENT"],
    "additionalContext": os.environ["CTX"],
}}, ensure_ascii=False))
'
