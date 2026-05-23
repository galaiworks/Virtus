"""Distributor Agent - Content distribution via official APIs."""

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .base import BaseAgent


@dataclass
class DistributionResult:
    """Result of a distribution attempt."""

    distribution_id: str
    status: str
    platform: str
    scheduled_time: str | None = None
    actual_delivery_time: str | None = None
    api_response: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    retry_count: int = 0


class Distributor(BaseAgent):
    """Distributor - publishes content via official APIs."""

    PLATFORM_BEST_TIMES = {
        "x": {
            "weekday": ["08:00", "12:00", "18:00", "22:00"],
            "weekend": ["10:00", "14:00", "20:00"],
        },
        "instagram": {
            "weekday": ["07:00", "12:00", "20:00"],
            "weekend": ["11:00", "15:00", "21:00"],
        },
        "linkedin": {
            "weekday": ["07:30", "12:00", "17:30"],
            "weekend": [],
        },
        "youtube": {
            "any": ["18:00", "20:00"],
        },
    }

    PLATFORM_LIMITS = {
        "x": {"daily_posts": 300, "hourly_posts": 50},
        "instagram": {"daily_posts": 25, "hourly_posts": 10},
        "linkedin": {"daily_posts": 50, "hourly_posts": 20},
        "youtube": {"daily_uploads": 50, "hourly_uploads": 5},
    }

    def __init__(
        self,
        api_key: str,
        brand_dna: dict[str, Any],
        log_dir: Path | None = None,
        skills: list[str] | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model="claude-haiku-4-5",
            brand_dna=brand_dna,
            skills=skills or [],
        )
        self.log_dir = log_dir or Path.cwd() / "logs" / "distribution"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute a distribution task."""
        task_type = task.get("task_type", "")
        context = task.get("context", {})

        if task_type == "schedule_post":
            return self.schedule_post(context)
        elif task_type == "immediate_post":
            return self.immediate_post(context)
        elif task_type == "send_email":
            return self.send_email(context)
        elif task_type == "calculate_optimal_time":
            return self.calculate_optimal_time(context)
        else:
            return {"error": f"Unknown task type: {task_type}"}

    def schedule_post(self, context: dict[str, Any]) -> dict[str, Any]:
        """Schedule a post for future delivery."""
        if context.get("approval_status") != "approved":
            return {"error": "Content not approved by Guardian"}

        platform = context.get("platform", "")
        scheduled_time = context.get("scheduled_time")

        if not scheduled_time:
            optimal = self._calculate_optimal_time(platform)
            scheduled_time = optimal

        result = DistributionResult(
            distribution_id=self._generate_id(),
            status="scheduled",
            platform=platform,
            scheduled_time=scheduled_time,
        )

        self._log(result, context)

        return {
            "task_type": "schedule_post",
            "success": True,
            "output": {
                "distribution_id": result.distribution_id,
                "status": result.status,
                "platform": result.platform,
                "scheduled_time": result.scheduled_time,
            },
        }

    def immediate_post(self, context: dict[str, Any]) -> dict[str, Any]:
        """Post content immediately.

        NOTE: This is a stub. Actual API calls must be implemented
        per platform (X API v2, Instagram Graph API, etc.) with
        proper OAuth credentials from the customer's .env file.
        """
        if context.get("approval_status") != "approved":
            return {"error": "Content not approved by Guardian"}

        platform = context.get("platform", "")
        content = context.get("content", {})

        compliance_check = self._check_platform_compliance(platform, content)
        if not compliance_check["passed"]:
            return {
                "error": "Platform compliance check failed",
                "violations": compliance_check["violations"],
            }

        result = DistributionResult(
            distribution_id=self._generate_id(),
            status="ready_for_api_call",
            platform=platform,
            actual_delivery_time=datetime.now(UTC).isoformat(),
            api_response={
                "note": "Stub implementation. Actual API call requires customer OAuth credentials.",
                "platform": platform,
                "content_preview": str(content)[:200],
            },
        )

        self._log(result, context)

        return {
            "task_type": "immediate_post",
            "success": True,
            "output": {
                "distribution_id": result.distribution_id,
                "status": result.status,
                "platform": result.platform,
                "note": "API integration pending - see api_response for stub data",
            },
        }

    def send_email(self, context: dict[str, Any]) -> dict[str, Any]:
        """Send an email with specified-email-law compliance."""
        if context.get("approval_status") != "approved":
            return {"error": "Content not approved by Guardian"}

        recipient = context.get("recipient", {})
        content = context.get("content", {})
        sender_info = context.get("sender_info", {})

        compliant_email = self._build_compliant_email(content, recipient, sender_info)

        result = DistributionResult(
            distribution_id=self._generate_id(),
            status="ready_for_smtp",
            platform="email",
            actual_delivery_time=datetime.now(UTC).isoformat(),
            api_response={
                "note": "Stub. Requires SMTP/Gmail API credentials.",
                "email": compliant_email,
            },
        )

        self._log(result, context)

        return {
            "task_type": "send_email",
            "success": True,
            "output": {
                "distribution_id": result.distribution_id,
                "compliant_email": compliant_email,
            },
        }

    def calculate_optimal_time(self, context: dict[str, Any]) -> dict[str, Any]:
        """Calculate optimal posting time."""
        platform = context.get("platform", "x")
        optimal = self._calculate_optimal_time(platform)
        return {
            "task_type": "calculate_optimal_time",
            "success": True,
            "output": {"platform": platform, "optimal_time": optimal},
        }

    def _calculate_optimal_time(self, platform: str) -> str:
        """Determine the next optimal posting time for the platform."""
        times = self.PLATFORM_BEST_TIMES.get(platform, {})
        now = datetime.now()
        is_weekend = now.weekday() >= 5
        slots = times.get(
            "weekend" if is_weekend else "weekday",
            times.get("any", ["12:00"]),
        )
        return f"{now.date().isoformat()}T{slots[0]}:00"

    def _check_platform_compliance(self, platform: str, content: dict[str, Any]) -> dict[str, Any]:
        """Check content against platform rules."""
        violations = []

        text = content.get("text", "") or content.get("body", "") or str(content)

        if platform == "x" and len(text) > 280:
            violations.append("X 280文字制限超過")

        if platform == "instagram":
            hashtags = content.get("hashtags", [])
            if len(hashtags) > 30:
                violations.append("Instagram ハッシュタグ30個制限超過")

        forbidden_patterns = ["follow for follow", "f4f", "sub4sub"]
        for pattern in forbidden_patterns:
            if pattern.lower() in text.lower():
                violations.append(f"スパム的表現検出: {pattern}")

        return {"passed": len(violations) == 0, "violations": violations}

    def _build_compliant_email(
        self,
        content: dict[str, Any],
        recipient: dict[str, Any],
        sender_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Build email compliant with specified email law."""
        unsubscribe_url = f"https://unsubscribe.example.com/{recipient.get('email', '')}"

        return {
            "to": recipient.get("email", ""),
            "from": sender_info.get("address", ""),
            "subject": content.get("subject", ""),
            "body": f"""{content.get("body", "")}

---
{sender_info.get("company_name", "")}
{sender_info.get("address", "")}
{sender_info.get("phone", "")}

このメールは {recipient.get("email", "")} 宛に送信されています。
今後配信を希望されない場合は、以下のリンクから解除可能です:
{unsubscribe_url}
""",
            "headers": {
                "List-Unsubscribe": f"<{unsubscribe_url}>",
            },
        }

    def _generate_id(self) -> str:
        """Generate a unique distribution ID."""
        return (
            f"dist_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{int(time.time() * 1000) % 10000:04d}"
        )

    def _log(self, result: DistributionResult, context: dict[str, Any]) -> None:
        """Log the distribution attempt."""
        log_file = self.log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "distribution_id": result.distribution_id,
            "status": result.status,
            "platform": result.platform,
            "scheduled_time": result.scheduled_time,
            "actual_delivery_time": result.actual_delivery_time,
            "retry_count": result.retry_count,
            "error": result.error,
            "context_keys": list(context.keys()),
        }
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
