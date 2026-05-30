"""Lead Strategist - 戦略統括・朝報生成."""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent

MORNING_BRIEF_SYSTEM = """あなたは Virtus の Lead Strategist です。

# あなたの使命
ひとり社長である {customer_name} の経営判断を最大化し、
集客→営業→クロージングのすべてを最適化することです。

# 顧客のブランド DNA
{brand_dna}

# 守るべき原則

第一に、神さんの教え「逃げるな、95 点に大丈夫?と聞き返せ」を実装する。
過剰な楽観論や曖昧な助言は禁止。具体的で実行可能な指示のみ出す。

第二に、ブランド DNA を完全継承する。
顧客の声で語り、顧客の価値観で判断する。

第三に、過剰約束を絶対にしない。
「絶対」「必ず」「100%」等の保証表現は使わない。

第四に、データドリブンで判断する。
感覚論ではなく、与えられた数値に基づく。

# 朝報の出力形式

```
おはようございます、{customer_name} さん。{date} です。

【今日の優先事項】
1. [具体的アクション]
2. [具体的アクション]
3. [具体的アクション]

【背景データ】
- [なぜそれが重要か、数字付き]

【Virtus の動き】
- [各エージェントが今日実行する内容]

【{customer_name} さんが判断すべきこと】
- [人間判断が必要な事項]
```

優先事項は必ず 3 つに絞る。多すぎると顧客が動けない。
"""


class LeadStrategist(BaseAgent):
    """戦略統括エージェント.

    朝報生成、週次レビュー、エージェント間オーケストレーション.
    """

    SUPPORTED_TASKS = frozenset({"morning_brief", "weekly_review", "delegate_task"})

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """タスクタイプに応じてメソッドを呼び分け."""
        task_type = task.get("task_type")
        if task_type not in self.SUPPORTED_TASKS:
            raise ValueError(
                f"Lead Strategist は task_type={task_type} をサポートしていません"
            )

        if task_type == "morning_brief":
            return self.morning_brief(task["context"])
        if task_type == "weekly_review":
            return self.weekly_review(task["context"])
        return self.delegate_task(task["context"])

    def morning_brief(self, context: dict[str, Any]) -> dict[str, Any]:
        """朝報を生成する.

        Args:
            context: {customer_id, customer_name, current_date,
                     yesterday_data, active_leads, active_deals, kpi_status}.

        Returns:
            {"task_type": "morning_brief", "output": "...朝報本文..."}.
        """
        system = MORNING_BRIEF_SYSTEM.format(
            customer_name=context.get("customer_name", "顧客"),
            brand_dna=self.brand_dna_block(),
            date=context.get("current_date", "本日"),
        )

        user_message = self._format_context_for_brief(context)
        text = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        return {"task_type": "morning_brief", "output": text}

    def weekly_review(self, context: dict[str, Any]) -> dict[str, Any]:
        """週次レビューを生成する (Phase 1 最小実装)."""
        prompt = (
            "あなたは Virtus の Lead Strategist です。"
            "以下のデータを元に、週次レビューを生成してください。\n\n"
            f"ブランド DNA:\n{self.brand_dna_block()}\n\n"
            f"先週のデータ:\n{context}"
        )
        text = self.call_llm(
            system=prompt,
            messages=[{"role": "user", "content": "週次レビューを作成してください"}],
        )
        return {"task_type": "weekly_review", "output": text}

    def delegate_task(self, context: dict[str, Any]) -> dict[str, Any]:
        """タスクを適切なエージェントへ振り分け (Phase 1 最小実装)."""
        return {
            "task_type": "delegate_task",
            "delegations": context.get("subtasks", []),
        }

    @staticmethod
    def _format_context_for_brief(context: dict[str, Any]) -> str:
        """朝報生成用にコンテキストを構造化."""
        lines = ["# 今日の状況"]
        if (date := context.get("current_date")):
            lines.append(f"- 日付: {date}")
        if (yesterday := context.get("yesterday_data")):
            lines.append(f"- 昨日のサマリー: {yesterday}")
        if (leads := context.get("active_leads")):
            lines.append(f"- 進行中リード ({len(leads)} 件): {leads}")
        if (deals := context.get("active_deals")):
            lines.append(f"- 進行中商談 ({len(deals)} 件): {deals}")
        if (kpi := context.get("kpi_status")):
            lines.append(f"- KPI 状況: {kpi}")
        lines.append("\n上記を元に、今日の朝報を生成してください。")
        return "\n".join(lines)
