"""Lead Strategist Agent - Strategy orchestrator and morning brief."""

import json
from datetime import date
from typing import Any

from .base import BaseAgent
from ..skills import format_brand_dna


class LeadStrategist(BaseAgent):
    """Lead Strategist - strategic decisions and morning briefs."""

    def __init__(
        self,
        api_key: str,
        brand_dna: dict[str, Any],
        skills: list[str] | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model="claude-opus-4-7",
            brand_dna=brand_dna,
            skills=skills or ["morning-brief"],
        )

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute a strategy task."""
        task_type = task.get("task_type", "")
        context = task.get("context", {})

        if task_type == "morning_brief":
            return self.generate_morning_brief(context)
        elif task_type == "weekly_review":
            return self.generate_weekly_review(context)
        elif task_type == "monthly_review":
            return self.generate_monthly_review(context)
        elif task_type == "delegate_task":
            return self.delegate_task(context)
        else:
            return {"error": f"Unknown task type: {task_type}"}

    def generate_morning_brief(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate the daily morning brief."""
        customer_name = self.brand_dna.get("identity", {}).get("name", "経営者")
        current_date = context.get("current_date", date.today().isoformat())
        yesterday_data = context.get("yesterday_data", {})
        active_leads = context.get("active_leads", [])
        active_deals = context.get("active_deals", [])
        kpi_status = context.get("kpi_status", {})

        system = self._system_prompt()

        prompt = f"""今日（{current_date}）の朝報を生成してください。

# 昨日の成果データ
{json.dumps(yesterday_data, ensure_ascii=False, indent=2)}

# 進行中のリード（上位5件）
{json.dumps(active_leads[:5], ensure_ascii=False, indent=2)}

# 進行中の商談
{json.dumps(active_deals, ensure_ascii=False, indent=2)}

# KPI状況
{json.dumps(kpi_status, ensure_ascii=False, indent=2)}

# 出力フォーマット
```
おはようございます、{customer_name} さん。

【今日の優先事項】（3つに絞る）
1. [具体的アクション]
2. [具体的アクション]
3. [具体的アクション]

【背景データ】
- [なぜそれが重要か、数字付き]

【Virtusの動き】
- [各エージェントが今日実行する内容]

【あなたが判断すべきこと】
- [人間判断が必要な事項]
```

重要:
- 3つの優先事項を超えない（過剰指示禁止）
- 数字を必ず含める
- 顧客のブランドDNA voice で語る"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000,
        )

        return {
            "task_type": "morning_brief",
            "success": True,
            "output": {
                "date": current_date,
                "content": response,
            },
        }

    def generate_weekly_review(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate weekly review."""
        week_data = context.get("week_data", {})
        previous_week = context.get("previous_week_data", {})

        system = self._system_prompt()
        prompt = f"""週次レビューを生成してください。

# 今週のデータ
{json.dumps(week_data, ensure_ascii=False, indent=2)}

# 前週のデータ（比較用）
{json.dumps(previous_week, ensure_ascii=False, indent=2)}

# 出力フォーマット
```
【先週の成果】
- リード獲得: X件 (前週比 +Y%)
- コンテンツ配信: X本
- 商談: X件
- 成約: X件

【勝ちパターン】
- [具体的に何が効いたか]

【課題】
- [何が改善必要か]

【今週の戦略】
- [具体的な実行計画]

【判断必要事項】
- [顧客が決断すべき事項]
```"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
        )

        return {
            "task_type": "weekly_review",
            "success": True,
            "output": {"content": response},
        }

    def generate_monthly_review(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate monthly review."""
        month_data = context.get("month_data", {})
        targets = context.get("targets", {})

        system = self._system_prompt()
        prompt = f"""月次レビューを生成してください。

# 今月のデータ
{json.dumps(month_data, ensure_ascii=False, indent=2)}

# KPI目標
{json.dumps(targets, ensure_ascii=False, indent=2)}

含める内容:
- KPI達成状況（数値）
- 勝ちパターン分析
- 失敗の分析と学習
- 翌月の戦略提言
- ブランドDNA進化の提案

マークダウン形式で出力。"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=6000,
        )

        return {
            "task_type": "monthly_review",
            "success": True,
            "output": {"content": response},
        }

    def delegate_task(self, context: dict[str, Any]) -> dict[str, Any]:
        """Delegate task to appropriate agent."""
        goal = context.get("goal", "")
        available_agents = context.get(
            "available_agents",
            ["Researcher", "Drafter", "Designer", "Distributor", "Connector", "Analyst"],
        )

        system = self._system_prompt()
        prompt = f"""以下のゴールを、適切なエージェントに分配してください。

# ゴール
{goal}

# 利用可能なエージェント
{', '.join(available_agents)}

# 出力形式（JSON）
{{
  "delegations": [
    {{
      "agent": "Drafter",
      "task_type": "note_article",
      "context": {{...}},
      "priority": "high|medium|low",
      "dependencies": []
    }}
  ],
  "execution_order": ["Researcher", "Drafter", "Designer"],
  "rationale": "この分配の理由"
}}"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            data = json.loads(response[start:end]) if start != -1 else {}
        except json.JSONDecodeError:
            data = {"raw_response": response}

        return {
            "task_type": "delegate_task",
            "success": True,
            "output": data,
        }

    def _system_prompt(self) -> str:
        """Build the base system prompt."""
        customer_name = self.brand_dna.get("identity", {}).get("name", "経営者")
        brand_dna_text = format_brand_dna(self.brand_dna)

        return f"""あなたは Virtus の Lead Strategist です。

# あなたの使命
ひとり社長である {customer_name} の経営判断を最大化し、
集客→営業→クロージングのすべてを最適化することです。

# 顧客のブランドDNA
{brand_dna_text}

# 守るべき原則

第一に、神さんの教え「逃げるな、95点に大丈夫?と聞き返せ」を実装する。
過剰な楽観論や曖昧な助言は禁止。具体的で実行可能な指示のみ出す。

第二に、ブランドDNAを完全継承する。顧客の声で語り、顧客の価値観で判断する。

第三に、過剰約束を絶対にしない。「絶対」「必ず」「100%」等の保証表現は使わない。

第四に、データドリブンで判断する。感覚論ではなく、数字に基づく。

第五に、判断委ねる場面を明確にする。Virtus は提案、決断は顧客。"""
