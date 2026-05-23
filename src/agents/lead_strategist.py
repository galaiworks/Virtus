"""Lead Strategist - 戦略統括・オーケストレーター."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .base import AgentResult, BaseAgent


class LeadStrategist(BaseAgent):
    """
    Lead Strategist エージェント (Opus 4.7)

    役割:
    - オーケストレーター（全体指揮）
    - 月次戦略立案、KPI管理
    - 顧客との対話窓口（朝報、ウィークリーレビュー、マンスリーレビュー）
    - 各エージェントへのタスク分配
    """

    name = "lead_strategist"
    model_tier = "strategic"

    def execute(self, task: dict[str, Any]) -> AgentResult:
        """Execute Lead Strategist task."""
        task_type = task.get("type", "morning_brief")

        handlers = {
            "morning_brief": self.morning_brief,
            "weekly_review": self.weekly_review,
            "monthly_review": self.monthly_review,
            "monthly_strategy": self.monthly_strategy,
            "delegate_task": self.delegate_task,
        }

        handler = handlers.get(task_type)
        if not handler:
            return AgentResult(
                success=False,
                content=None,
                error=f"Unknown task type: {task_type}",
            )

        return handler(task)

    def morning_brief(self, task: dict[str, Any]) -> AgentResult:
        """Generate morning brief for customer."""
        context = task.get("context", {})
        date = datetime.now().strftime("%Y年%m月%d日")

        system_prompt = f"""{self.get_system_prompt()}

あなたは顧客の戦略パートナーとして、毎朝7時に「朝報」を配信します。

朝報の構成:
1. 挨拶（簡潔に）
2. 今日の優先事項3つ（具体的なアクション）
3. 昨日の成果サマリー（あれば）
4. 注目すべきトレンドやリード情報

トーンは {self.brand_dna.get('voice', {}).get('tone', 'プロフェッショナルかつ親近感')} で。
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下の情報をもとに、{date}の朝報を生成してください。

【昨日の活動サマリー】
{context.get('yesterday_summary', '情報なし')}

【新規リード情報】
{context.get('new_leads', '情報なし')}

【今週の目標】
{context.get('weekly_goals', '情報なし')}

【トレンド情報】
{context.get('trends', '情報なし')}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "morning_brief", "date": date},
            )
        except Exception as e:
            self.logger.error(f"Morning brief generation failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def weekly_review(self, task: dict[str, Any]) -> AgentResult:
        """Generate weekly review."""
        week_data = task.get("week_data", {})

        system_prompt = f"""{self.get_system_prompt()}

あなたは毎週月曜日にウィークリーレビューを配信します。

レビューの構成:
1. 先週のKPI達成状況
2. 成功ポイント（勝ちパターン）
3. 改善ポイント
4. 今週の重点施策
5. 注目リード・商談状況
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のデータをもとにウィークリーレビューを生成してください。

【先週のKPI】
{week_data.get('kpi', '情報なし')}

【コンテンツパフォーマンス】
{week_data.get('content_performance', '情報なし')}

【リード・商談状況】
{week_data.get('leads_deals', '情報なし')}

【特記事項】
{week_data.get('notes', 'なし')}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "weekly_review"},
            )
        except Exception as e:
            self.logger.error(f"Weekly review generation failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def monthly_review(self, task: dict[str, Any]) -> AgentResult:
        """Generate monthly review."""
        month_data = task.get("month_data", {})

        system_prompt = f"""{self.get_system_prompt()}

あなたは月末にマンスリーレビューを配信します。

レビューの構成:
1. 今月の成果サマリー
2. KPI達成率（目標 vs 実績）
3. 最も効果的だった施策 TOP3
4. 改善が必要な領域
5. 来月への提言
6. 勝ちパターンの更新
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のデータをもとにマンスリーレビューを生成してください。

【月間KPI】
{month_data.get('kpi', '情報なし')}

【コンテンツ実績】
{month_data.get('content', '情報なし')}

【リード獲得実績】
{month_data.get('leads', '情報なし')}

【商談・成約実績】
{month_data.get('deals', '情報なし')}

【勝ちパターン候補】
{month_data.get('win_patterns', '情報なし')}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "monthly_review"},
            )
        except Exception as e:
            self.logger.error(f"Monthly review generation failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def monthly_strategy(self, task: dict[str, Any]) -> AgentResult:
        """Generate monthly strategy document."""
        context = task.get("context", {})

        system_prompt = f"""{self.get_system_prompt()}

あなたは月初に月次戦略書を作成します。

戦略書の構成:
1. 先月の振り返り（簡潔に）
2. 今月の重点目標（KPI含む）
3. コンテンツカレンダー概要
4. 能動営業ターゲット方針
5. リソース配分
6. リスクと対策
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下の情報をもとに月次戦略書を生成してください。

【先月実績サマリー】
{context.get('last_month_summary', '情報なし')}

【今月の目標】
{context.get('monthly_goals', '情報なし')}

【市場動向】
{context.get('market_trends', '情報なし')}

【リソース状況】
{context.get('resources', '情報なし')}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "monthly_strategy"},
            )
        except Exception as e:
            self.logger.error(f"Monthly strategy generation failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def delegate_task(self, task: dict[str, Any]) -> AgentResult:
        """Create task delegation instructions for other agents."""
        target_agent = task.get("target_agent")
        task_description = task.get("description")

        if not target_agent or not task_description:
            return AgentResult(
                success=False,
                content=None,
                error="target_agent and description are required",
            )

        delegation = {
            "target": target_agent,
            "task": task_description,
            "priority": task.get("priority", "normal"),
            "deadline": task.get("deadline"),
            "context": task.get("context", {}),
        }

        return AgentResult(
            success=True,
            content=delegation,
            metadata={"type": "delegation"},
        )

    def get_system_prompt(self) -> str:
        """Get Lead Strategist specific system prompt."""
        return f"""あなたは Virtus の Lead Strategist（戦略統括）エージェントです。

あなたの役割:
- オーケストレーター（全体指揮）
- 月次戦略立案、KPI管理
- 顧客との対話窓口
- 各エージェントへのタスク分配

以下のブランドDNAを完全に遵守してください:

{self.format_brand_dna()}

重要な原則:
- 95点未満の品質は許さない（神さんの教え）
- 過剰な楽観論禁止、現実的な戦略
- 具体的なアクションを提示
- 顧客の声で書く（Garai Tone）
"""
