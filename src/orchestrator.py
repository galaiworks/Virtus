"""Virtus Orchestrator - エージェント間連携."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .agents import (
    Analyst,
    Connector,
    Designer,
    Distributor,
    Drafter,
    Guardian,
    LeadStrategist,
    Researcher,
)
from .agents.base import AgentResult
from .brain.manager import BrainManager
from .utils.config import Config
from .utils.logger import get_logger


@dataclass
class WorkflowResult:
    """Result from workflow execution."""

    success: bool
    phase: str
    results: dict[str, AgentResult]
    errors: list[str]


class VirtusOrchestrator:
    """
    Virtus Orchestrator

    8体のエージェントを統括し、ワークフローを実行する。
    Anthropic公式 Orchestrator-Worker パターンに準拠。
    """

    def __init__(self, config: Config, brand_dna: dict[str, Any]):
        self.config = config
        self.brand_dna = brand_dna
        self.logger = get_logger("virtus.orchestrator")

        self.brain = BrainManager(config.brain_path, config.customer_id)

        self._init_agents()

    def _init_agents(self) -> None:
        """Initialize all 8 agents."""
        api_key = self.config.api_key

        self.lead_strategist = LeadStrategist(
            api_key=api_key,
            model=self.config.get_model("strategic"),
            brand_dna=self.brand_dna,
        )

        self.researcher = Researcher(
            api_key=api_key,
            model=self.config.get_model("execution"),
            brand_dna=self.brand_dna,
        )

        self.drafter = Drafter(
            api_key=api_key,
            model=self.config.get_model("execution"),
            brand_dna=self.brand_dna,
            skills=["garai-tone", "dream-writing", "impact-v2-0r"],
        )

        self.designer = Designer(
            api_key=api_key,
            model=self.config.get_model("execution"),
            brand_dna=self.brand_dna,
        )

        self.distributor = Distributor(
            api_key=api_key,
            model=self.config.get_model("batch"),
            brand_dna=self.brand_dna,
        )

        self.connector = Connector(
            api_key=api_key,
            model=self.config.get_model("execution"),
            brand_dna=self.brand_dna,
        )

        self.analyst = Analyst(
            api_key=api_key,
            model=self.config.get_model("execution"),
            brand_dna=self.brand_dna,
        )

        self.guardian = Guardian(
            api_key=api_key,
            model=self.config.get_model("strategic"),
            brand_dna=self.brand_dna,
        )

        self.logger.info("All 8 agents initialized")

    def run_morning_workflow(self) -> WorkflowResult:
        """
        朝のワークフロー（5:00-7:00）

        1. Researcher/Analyst: 情報収集
        2. Lead Strategist: 朝報生成
        """
        self.logger.info("Starting morning workflow")
        results = {}
        errors = []

        try:
            trend_result = self.researcher.execute({
                "type": "trend_research",
                "topics": self.brand_dna.get("content_strategy", {}).get("pillar_topics", []),
            })
            results["trend_research"] = trend_result
        except Exception as e:
            errors.append(f"Trend research failed: {e}")

        try:
            lead_result = self.researcher.execute({
                "type": "lead_extraction",
                "press_releases": [],
                "target_industries": self.brand_dna.get("identity", {}).get("target_industries", []),
            })
            results["lead_extraction"] = lead_result
        except Exception as e:
            errors.append(f"Lead extraction failed: {e}")

        try:
            context = {
                "yesterday_summary": self.brain.get_yesterday_summary(),
                "new_leads": results.get("lead_extraction", {}).content if results.get("lead_extraction") else None,
                "weekly_goals": self.brain.get_weekly_goals(),
                "trends": results.get("trend_research", {}).content if results.get("trend_research") else None,
            }

            morning_brief = self.lead_strategist.execute({
                "type": "morning_brief",
                "context": context,
            })
            results["morning_brief"] = morning_brief

            if morning_brief.success:
                self.brain.save_content("morning_brief", morning_brief.content, {
                    "date": datetime.now().isoformat(),
                })
        except Exception as e:
            errors.append(f"Morning brief failed: {e}")

        return WorkflowResult(
            success=len(errors) == 0,
            phase="morning",
            results=results,
            errors=errors,
        )

    def run_content_generation_workflow(
        self,
        content_type: str,
        topic: str,
        **kwargs: Any,
    ) -> WorkflowResult:
        """
        コンテンツ生成ワークフロー（9:00-15:00）

        1. Researcher: リサーチ
        2. Drafter: 執筆
        3. Designer: ビジュアル仕様
        4. Guardian: 品質チェック
        """
        self.logger.info(f"Starting content generation: {content_type}")
        results = {}
        errors = []

        try:
            research_result = self.researcher.execute({
                "type": "keyword_research",
                "seed_keywords": kwargs.get("keywords", [topic]),
            })
            results["research"] = research_result
        except Exception as e:
            errors.append(f"Research failed: {e}")

        try:
            draft_task = {
                "type": content_type,
                "topic": topic,
                "research": results.get("research", {}).content if results.get("research") else None,
                **kwargs,
            }
            draft_result = self.drafter.execute(draft_task)
            results["draft"] = draft_result
        except Exception as e:
            errors.append(f"Draft failed: {e}")
            return WorkflowResult(
                success=False,
                phase="content_generation",
                results=results,
                errors=errors,
            )

        if draft_result.success:
            try:
                quality_result = self._run_quality_loop(
                    content=draft_result.content,
                    content_type=content_type,
                )
                results["quality"] = quality_result

                if not quality_result.success:
                    errors.append("Quality loop failed or needs escalation")
            except Exception as e:
                errors.append(f"Quality check failed: {e}")

        if content_type in ["note_article", "instagram_post"]:
            try:
                design_result = self.designer.execute({
                    "type": "thumbnail",
                    "title": topic,
                    "platform": content_type.split("_")[0],
                })
                results["design"] = design_result
            except Exception as e:
                errors.append(f"Design failed: {e}")

        return WorkflowResult(
            success=len(errors) == 0,
            phase="content_generation",
            results=results,
            errors=errors,
        )

    def run_distribution_workflow(
        self,
        content: str,
        platform: str,
        scheduled_time: datetime | None = None,
    ) -> WorkflowResult:
        """
        配信ワークフロー（15:00）

        1. Guardian: 最終チェック
        2. Distributor: 配信スケジュール
        """
        self.logger.info(f"Starting distribution to {platform}")
        results = {}
        errors = []

        try:
            compliance_result = self.guardian.execute({
                "type": "compliance_check",
                "content": content,
                "content_type": platform,
            })
            results["compliance"] = compliance_result

            if not compliance_result.content.get("passed", False):
                errors.append("Compliance check failed")
                return WorkflowResult(
                    success=False,
                    phase="distribution",
                    results=results,
                    errors=errors,
                )
        except Exception as e:
            errors.append(f"Compliance check failed: {e}")
            return WorkflowResult(
                success=False,
                phase="distribution",
                results=results,
                errors=errors,
            )

        try:
            schedule_result = self.distributor.execute({
                "type": "schedule",
                "platform": platform,
                "content": content,
                "scheduled_time": scheduled_time,
            })
            results["schedule"] = schedule_result

            if schedule_result.success:
                self.brain.save_content(
                    f"scheduled_{platform}",
                    content,
                    {
                        "platform": platform,
                        "scheduled_time": scheduled_time.isoformat() if scheduled_time else None,
                        "status": "pending_approval",
                    },
                )
        except Exception as e:
            errors.append(f"Scheduling failed: {e}")

        return WorkflowResult(
            success=len(errors) == 0,
            phase="distribution",
            results=results,
            errors=errors,
        )

    def run_relationship_workflow(
        self,
        incoming_messages: list[dict[str, Any]],
    ) -> WorkflowResult:
        """
        関係構築ワークフロー（18:00）

        1. Connector: DM/コメント返信ドラフト
        2. Guardian: 品質チェック
        """
        self.logger.info("Starting relationship workflow")
        results = {}
        errors = []

        replies = []
        for msg in incoming_messages:
            try:
                reply_result = self.connector.execute({
                    "type": "dm_reply",
                    "incoming_message": msg.get("content", ""),
                    "sender": msg.get("sender", {}),
                    "platform": msg.get("platform", "X"),
                })

                if reply_result.success:
                    quality_result = self.guardian.execute({
                        "type": "evaluate",
                        "content": reply_result.content.get("reply_draft", ""),
                        "content_type": "dm_reply",
                    })

                    replies.append({
                        "message_id": msg.get("id"),
                        "reply_draft": reply_result.content,
                        "quality_score": quality_result.content.get("total_score", 0),
                        "approved": quality_result.content.get("approved", False),
                    })
            except Exception as e:
                errors.append(f"Reply generation failed for {msg.get('id')}: {e}")

        results["replies"] = replies

        return WorkflowResult(
            success=len(errors) == 0,
            phase="relationship",
            results=results,
            errors=errors,
        )

    def run_learning_workflow(self) -> WorkflowResult:
        """
        学習ワークフロー（22:00）

        1. Analyst: 当日成果集約
        2. Analyst: 勝ちパターン抽出
        3. Lead Strategist: 翌日戦略更新
        """
        self.logger.info("Starting learning workflow")
        results = {}
        errors = []

        try:
            performance_data = self.brain.get_today_performance()
            analysis_result = self.analyst.execute({
                "type": "performance_report",
                "period": "daily",
                "data": performance_data,
            })
            results["analysis"] = analysis_result
        except Exception as e:
            errors.append(f"Analysis failed: {e}")

        try:
            win_pattern_result = self.analyst.execute({
                "type": "win_pattern_extraction",
                "content_data": self.brain.get_content_performance(),
                "outreach_data": self.brain.get_outreach_performance(),
                "deal_data": self.brain.get_deal_performance(),
            })
            results["win_patterns"] = win_pattern_result

            if win_pattern_result.success:
                self.brain.update_win_patterns(win_pattern_result.content)
        except Exception as e:
            errors.append(f"Win pattern extraction failed: {e}")

        return WorkflowResult(
            success=len(errors) == 0,
            phase="learning",
            results=results,
            errors=errors,
        )

    def run_weekly_review(self) -> WorkflowResult:
        """ウィークリーレビュー（毎週月曜）"""
        self.logger.info("Starting weekly review")
        results = {}
        errors = []

        try:
            week_data = self.brain.get_week_data()
            review_result = self.lead_strategist.execute({
                "type": "weekly_review",
                "week_data": week_data,
            })
            results["review"] = review_result

            if review_result.success:
                self.brain.save_content("weekly_review", review_result.content, {
                    "date": datetime.now().isoformat(),
                })
        except Exception as e:
            errors.append(f"Weekly review failed: {e}")

        return WorkflowResult(
            success=len(errors) == 0,
            phase="weekly_review",
            results=results,
            errors=errors,
        )

    def run_monthly_review(self) -> WorkflowResult:
        """マンスリーレビュー（月末）"""
        self.logger.info("Starting monthly review")
        results = {}
        errors = []

        try:
            month_data = self.brain.get_month_data()
            review_result = self.lead_strategist.execute({
                "type": "monthly_review",
                "month_data": month_data,
            })
            results["review"] = review_result

            if review_result.success:
                self.brain.save_content("monthly_review", review_result.content, {
                    "date": datetime.now().isoformat(),
                })
        except Exception as e:
            errors.append(f"Monthly review failed: {e}")

        try:
            strategy_result = self.lead_strategist.execute({
                "type": "monthly_strategy",
                "context": {
                    "last_month_summary": results.get("review", {}).content if results.get("review") else None,
                    "monthly_goals": self.brain.get_monthly_goals(),
                },
            })
            results["strategy"] = strategy_result
        except Exception as e:
            errors.append(f"Monthly strategy failed: {e}")

        return WorkflowResult(
            success=len(errors) == 0,
            phase="monthly_review",
            results=results,
            errors=errors,
        )

    def _run_quality_loop(
        self,
        content: str,
        content_type: str,
        max_retries: int = 3,
    ) -> AgentResult:
        """Run the 95-point quality loop."""

        def refine_callback(current_content: str, feedback: str) -> str:
            return self.drafter.refine(current_content, feedback)

        return self.guardian.execute({
            "type": "quality_loop",
            "content": content,
            "content_type": content_type,
            "refine_callback": refine_callback,
        })
