"""Analyst Agent - Performance analysis and pattern extraction."""

import json
from typing import Any

from .base import BaseAgent


class Analyst(BaseAgent):
    """Analyst - data analysis, pattern extraction, monthly reports."""

    KPI_DEFINITIONS = {
        "content_volume": {
            "metric": "公開されたコンテンツ数",
            "unit": "本/月",
            "tier_1_target": 30, "tier_2_target": 50, "tier_3_target": 80,
        },
        "lead_acquisition": {
            "metric": "新規リード獲得数",
            "unit": "件/月",
            "tier_1_target": 20, "tier_2_target": 50, "tier_3_target": 100,
        },
        "meeting_booked": {
            "metric": "商談予約数",
            "unit": "件/月",
            "tier_1_target": 5, "tier_2_target": 15, "tier_3_target": 30,
        },
        "conversion_rate": {
            "metric": "リード→商談 転換率",
            "unit": "%",
            "tier_1_target": 25, "tier_2_target": 30, "tier_3_target": 35,
        },
        "deal_close_rate": {
            "metric": "商談→成約 転換率",
            "unit": "%",
            "tier_1_target": 25, "tier_2_target": 30, "tier_3_target": 40,
        },
        "average_deal_size": {
            "metric": "平均取引額",
            "unit": "円",
            "tier_1_target": 100000, "tier_2_target": 500000, "tier_3_target": 2000000,
        },
    }

    def __init__(
        self,
        api_key: str,
        brand_dna: dict[str, Any],
        skills: list[str] | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model="claude-sonnet-4-6",
            brand_dna=brand_dna,
            skills=skills or [],
        )

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute an analysis task."""
        task_type = task.get("task_type", "")
        context = task.get("context", {})

        if task_type == "weekly_summary":
            return self.weekly_summary(context)
        elif task_type == "monthly_report":
            return self.monthly_report(context)
        elif task_type == "pattern_extraction":
            return self.extract_patterns(context)
        elif task_type == "kpi_dashboard":
            return self.kpi_dashboard(context)
        else:
            return {"error": f"Unknown task type: {task_type}"}

    def weekly_summary(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate weekly performance summary."""
        period = context.get("period", "")
        performance_data = context.get("performance_data", {})

        system = self._system_prompt()
        prompt = f"""週次パフォーマンスサマリーを生成してください。

# 期間
{period}

# パフォーマンスデータ
{json.dumps(performance_data, ensure_ascii=False, indent=2)}

# 出力形式
- 主要指標サマリー（前週比含む）
- 良かった点（数字付き）
- 課題（数字付き）
- 次週への提言（3点以内）

データドリブン、ハルシネーション禁止。"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        return {
            "task_type": "weekly_summary",
            "success": True,
            "output": {"content": response, "period": period},
        }

    def monthly_report(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate monthly performance report."""
        period = context.get("period", "")
        performance_data = context.get("performance_data", {})
        previous_month = context.get("previous_month_data", {})
        kpi_targets = context.get("kpi_targets", {})

        system = self._system_prompt()
        prompt = f"""月次パフォーマンスレポートを生成してください。

# 期間
{period}

# 今月データ
{json.dumps(performance_data, ensure_ascii=False, indent=2)}

# 前月データ
{json.dumps(previous_month, ensure_ascii=False, indent=2)}

# KPI目標
{json.dumps(kpi_targets, ensure_ascii=False, indent=2)}

# 出力形式（YAML風）
```
period: "..."

summary:
  total_content_published: N
  total_engagement: N
  total_leads_generated: N
  total_meetings_booked: N
  total_deals_closed: N

vs_previous_month:
  content: "+X%"
  engagement: "+X%"
  ...

winning_patterns:
  - pattern: "..."
    proof: "..."
    recommendation: "..."
    confidence: 0.XX

losing_patterns:
  - pattern: "..."
    proof: "..."
    recommendation: "..."

next_month_strategy:
  - "..."
```

重要:
- 1回の成功は偶然、3回続いてパターン認定
- 改善提案は具体的に（「もう少し」ではなく「○○を△△に」）
- データにないことを言わない"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=6000,
        )

        return {
            "task_type": "monthly_report",
            "success": True,
            "output": {"content": response, "period": period},
        }

    def extract_patterns(self, context: dict[str, Any]) -> dict[str, Any]:
        """Extract winning and losing patterns from content data."""
        content_data = context.get("content_data", [])
        pattern_type = context.get("pattern_type", "winning")

        if not content_data:
            return {
                "task_type": "pattern_extraction",
                "success": False,
                "error": "コンテンツデータがありません",
            }

        scored = sorted(
            content_data,
            key=lambda x: x.get("engagement_score", 0),
            reverse=(pattern_type == "winning"),
        )
        sample_size = max(1, int(len(scored) * 0.2))
        sample = scored[:sample_size]

        system = self._system_prompt()
        prompt = f"""以下のコンテンツデータから {pattern_type} パターンを抽出してください。

# {'上位' if pattern_type == 'winning' else '下位'} 20% サンプル ({sample_size}件)
{json.dumps(sample, ensure_ascii=False, indent=2)}

# 全体件数
{len(content_data)}件

# 出力形式（JSON）
{{
  "patterns": [
    {{
      "pattern": "パターン名",
      "proof": "数字付きの証拠（最低3例）",
      "recommendation": "具体的な提案",
      "confidence": 0.85,
      "occurrences": N
    }}
  ]
}}

重要: 3回以上の繰り返しで初めてパターン認定。1-2回はノイズとして除外。"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            data = json.loads(response[start:end]) if start != -1 else {"raw": response}
        except json.JSONDecodeError:
            data = {"raw": response}

        return {
            "task_type": "pattern_extraction",
            "success": True,
            "output": data,
        }

    def kpi_dashboard(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate KPI dashboard data."""
        current_metrics = context.get("current_metrics", {})
        tier = context.get("tier", 1)
        tier_key = f"tier_{tier}_target"

        dashboard = {}
        for kpi_id, kpi_def in self.KPI_DEFINITIONS.items():
            current = current_metrics.get(kpi_id, 0)
            target = kpi_def.get(tier_key, 0)
            progress = (current / target * 100) if target > 0 else 0

            dashboard[kpi_id] = {
                "metric": kpi_def["metric"],
                "unit": kpi_def["unit"],
                "current": current,
                "target": target,
                "progress_percent": round(progress, 1),
                "status": self._kpi_status(progress),
            }

        return {
            "task_type": "kpi_dashboard",
            "success": True,
            "output": {"tier": tier, "kpis": dashboard},
        }

    def _kpi_status(self, progress: float) -> str:
        """Determine KPI status from progress percent."""
        if progress >= 100:
            return "達成"
        elif progress >= 80:
            return "順調"
        elif progress >= 50:
            return "要注意"
        else:
            return "未達"

    def _system_prompt(self) -> str:
        """Build base system prompt."""
        customer_name = self.brand_dna.get("identity", {}).get("name", "顧客")

        return f"""あなたは Virtus の Analyst エージェントです。

# あなたの使命
顧客 {customer_name} のすべての活動データを集約し、
「何が効いて、何が効かなかったか」を言語化することです。

# 守るべき原則

第一に、データドリブン判断。感覚論ではなく、数字に基づく分析。

第二に、ハルシネーション禁止。データにないことを言わない。

第三に、勝ちパターンと負けパターンを公平に分析。良いところだけを切り取らない。

第四に、改善提案は具体的に。「もう少し」ではなく「〇〇を△△に変える」。

第五に、再現性を重視。1回の成功は偶然、3回続いてパターン認定。"""
