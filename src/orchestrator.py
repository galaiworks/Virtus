"""Virtus Orchestrator - coordinates the 8-agent team."""

import contextlib
from pathlib import Path
from typing import Any

from .agents.analyst import Analyst
from .agents.connector import Connector
from .agents.designer import Designer
from .agents.distributor import Distributor
from .agents.drafter import Drafter
from .agents.guardian import Guardian
from .agents.lead_strategist import LeadStrategist
from .agents.researcher import Researcher
from .brain import BrainLayer


class Orchestrator:
    """Coordinates the 8-agent Virtus team."""

    def __init__(
        self,
        api_key: str,
        brand_dna: dict[str, Any],
        output_dir: Path | None = None,
        brain: BrainLayer | None = None,
        customer_id: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.brand_dna = brand_dna
        self.output_dir = output_dir or Path.cwd() / "output"
        self.brain = brain
        self.customer_id = customer_id

        self.lead_strategist = LeadStrategist(api_key, brand_dna)
        self.researcher = Researcher(api_key, brand_dna)
        self.drafter = Drafter(api_key, brand_dna)
        self.designer = Designer(api_key, brand_dna, output_dir=self.output_dir)
        self.distributor = Distributor(api_key, brand_dna)
        self.connector = Connector(api_key, brand_dna)
        self.analyst = Analyst(api_key, brand_dna)
        self.guardian = Guardian(api_key, brand_dna)

        self.agents = {
            "lead_strategist": self.lead_strategist,
            "researcher": self.researcher,
            "drafter": self.drafter,
            "designer": self.designer,
            "distributor": self.distributor,
            "connector": self.connector,
            "analyst": self.analyst,
            "guardian": self.guardian,
        }

    def write_and_review(
        self,
        content_type: str,
        context: dict[str, Any],
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Write content with Drafter and run it through Guardian's 95-point loop."""
        draft_result = self.drafter.execute(
            {
                "task_type": content_type,
                "context": context,
            }
        )

        if not draft_result.get("success"):
            return {
                "status": "draft_failed",
                "error": draft_result.get("error", "Drafter failed"),
            }

        content_text = self._extract_content_text(draft_result.get("output", {}))

        def revise_fn(content: str, feedback: str) -> str:
            return self.drafter.refine(content, feedback, content_type)

        loop_result = self.guardian.evaluate_with_loop(
            content=content_text,
            content_type=content_type,
            agent_name="Drafter",
            revise_fn=revise_fn,
            max_retries=max_retries,
        )

        result = {
            "status": loop_result["status"],
            "content": loop_result.get("content"),
            "draft_output": draft_result.get("output"),
            "evaluation": loop_result.get("evaluation"),
            "retry_count": loop_result.get("retry_count", 0),
        }
        self._audit_log(
            "evaluations",
            {
                "agent": "Drafter",
                "content_type": content_type,
                "status": result["status"],
                "total_score": (result["evaluation"] or {}).get("total_score"),
                "retry_count": result["retry_count"],
            },
        )
        return result

    def morning_brief(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate the morning brief with Lead Strategist."""
        return self.lead_strategist.execute(
            {
                "task_type": "morning_brief",
                "context": context,
            }
        )

    def full_content_pipeline(
        self,
        topic: str,
        target_audience: str,
        platforms: list[str],
    ) -> dict[str, Any]:
        """Generate a full multi-platform content set.

        Pipeline:
        1. Drafter writes for each platform
        2. Guardian reviews each
        3. Designer creates visuals where appropriate
        4. Distributor schedules (stub - waits for human approval)
        """
        results: dict[str, Any] = {"platforms": {}}

        for platform in platforms:
            platform_result = self.write_and_review(
                content_type=platform,
                context={
                    "topic": topic,
                    "target_audience": target_audience,
                },
            )

            if platform_result["status"] == "approved" and platform in (
                "note_article",
                "youtube_script",
            ):
                visual_result = self.designer.execute(
                    {
                        "task_type": "video" if platform == "youtube_script" else "overlay",
                        "context": {
                            "platform": platform.replace("_script", "").replace(
                                "note_article", "youtube"
                            ),
                            "content_text": platform_result.get("content", "")[:500],
                            "title": topic,
                            "duration": 10.0,
                        },
                    }
                )
                platform_result["visual"] = visual_result

            results["platforms"][platform] = platform_result

        return results

    def handle_incoming_message(self, message_context: dict[str, Any]) -> dict[str, Any]:
        """Handle an incoming DM/comment with Connector + Guardian."""
        connector_result = self.connector.execute(
            {
                "task_type": "draft_dm_reply",
                "context": message_context,
            }
        )

        output = connector_result.get("output", {})
        if output.get("escalation_required"):
            self._audit_log(
                "escalations",
                {
                    "agent": "Connector",
                    "level": output.get("escalation_level"),
                    "reason": output.get("reason"),
                },
            )
            return {
                "status": "escalated",
                "connector_result": connector_result,
            }

        reply_draft = output.get("reply_draft", {})
        reply_message = reply_draft.get("message", "")

        if not reply_message:
            return {
                "status": "no_reply_generated",
                "connector_result": connector_result,
            }

        guardian_eval = self.guardian.evaluate(reply_message, "dm_reply")

        return {
            "status": "ready_for_approval" if guardian_eval.total_score >= 95 else "needs_revision",
            "reply": reply_message,
            "draft_metadata": reply_draft,
            "evaluation_score": guardian_eval.total_score,
            "evaluation_feedback": guardian_eval.feedback,
        }

    def delegate(self, agent_name: str, task: dict[str, Any]) -> dict[str, Any]:
        """Delegate a task directly to a specific agent."""
        agent = self.agents.get(agent_name)
        if not agent:
            return {"error": f"Unknown agent: {agent_name}"}
        return agent.execute(task)

    def _audit_log(self, log_type: str, entry: dict[str, Any]) -> None:
        """Persist an audit entry when a BrainLayer is attached (quality-95 要件)."""
        if self.brain is None or self.customer_id is None:
            return
        # 監査ログの書き込み失敗でコンテンツ生成自体は止めない
        with contextlib.suppress(OSError):
            self.brain.append_log(self.customer_id, log_type, entry)

    def _extract_content_text(self, output: dict[str, Any]) -> str:
        """Extract text content from drafter output."""
        if isinstance(output, str):
            return output
        for key in ("content", "body", "message", "text", "script"):
            if key in output:
                value = output[key]
                if isinstance(value, str):
                    return value
        if "slides" in output:
            slides = output["slides"]
            return "\n\n".join(s.get("text", "") for s in slides if isinstance(s, dict))
        return str(output)
