"""Distributor - 配信処理."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .base import AgentResult, BaseAgent


@dataclass
class DistributionTask:
    """Distribution task data."""

    content_id: str
    platform: str
    content: str
    scheduled_time: datetime | None = None
    status: str = "pending"


class Distributor(BaseAgent):
    """
    Distributor エージェント (Haiku 4.5)

    役割:
    - 各プラットフォームへの予約投稿
    - 配信タイミング最適化
    - メルマガ・LINE配信
    - 規約遵守の API 経由配信
    """

    name = "distributor"
    model_tier = "batch"

    def execute(self, task: dict[str, Any]) -> AgentResult:
        """Execute Distributor task."""
        task_type = task.get("type", "schedule")

        handlers = {
            "schedule": self.schedule_distribution,
            "optimize_timing": self.optimize_timing,
            "validate_content": self.validate_for_platform,
            "batch_schedule": self.batch_schedule,
        }

        handler = handlers.get(task_type)
        if not handler:
            return AgentResult(
                success=False,
                content=None,
                error=f"Unknown task type: {task_type}",
            )

        return handler(task)

    def schedule_distribution(self, task: dict[str, Any]) -> AgentResult:
        """Schedule content for distribution."""
        platform = task.get("platform", "")
        content = task.get("content", "")
        scheduled_time = task.get("scheduled_time")

        if not platform or not content:
            return AgentResult(
                success=False,
                content=None,
                error="Platform and content are required",
            )

        validation = self._validate_content(platform, content)
        if not validation["valid"]:
            return AgentResult(
                success=False,
                content=None,
                error=f"Content validation failed: {validation['errors']}",
            )

        distribution_task = {
            "platform": platform,
            "content": content,
            "scheduled_time": scheduled_time,
            "status": "scheduled",
            "created_at": datetime.now().isoformat(),
            "validation": validation,
        }

        self.logger.info(f"Scheduled distribution to {platform}")

        return AgentResult(
            success=True,
            content=distribution_task,
            metadata={"type": "schedule", "platform": platform},
        )

    def optimize_timing(self, task: dict[str, Any]) -> AgentResult:
        """Optimize posting time based on platform and audience."""
        platform = task.get("platform", "")
        audience_data = task.get("audience_data", {})

        system_prompt = f"""{self.get_system_prompt()}

あなたは配信タイミングを最適化します。

【考慮事項】
- プラットフォームの特性
- ターゲットオーディエンスの活動時間
- 過去のエンゲージメントデータ
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のプラットフォームで最適な投稿時間を提案してください。

【プラットフォーム】
{platform}

【オーディエンスデータ】
{audience_data if audience_data else 'データなし'}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "optimize_timing", "platform": platform},
            )
        except Exception as e:
            self.logger.error(f"Timing optimization failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def validate_for_platform(self, task: dict[str, Any]) -> AgentResult:
        """Validate content for specific platform requirements."""
        platform = task.get("platform", "")
        content = task.get("content", "")

        validation = self._validate_content(platform, content)

        return AgentResult(
            success=validation["valid"],
            content=validation,
            metadata={"type": "validate", "platform": platform},
        )

    def batch_schedule(self, task: dict[str, Any]) -> AgentResult:
        """Schedule multiple content items."""
        items = task.get("items", [])

        results = []
        for item in items:
            result = self.schedule_distribution(item)
            results.append({
                "platform": item.get("platform"),
                "success": result.success,
                "error": result.error,
            })

        success_count = sum(1 for r in results if r["success"])

        return AgentResult(
            success=success_count == len(items),
            content={
                "total": len(items),
                "success": success_count,
                "failed": len(items) - success_count,
                "details": results,
            },
            metadata={"type": "batch_schedule"},
        )

    def _validate_content(self, platform: str, content: str) -> dict[str, Any]:
        """Validate content against platform requirements."""
        errors = []
        warnings = []

        platform_limits = {
            "x": {"max_length": 280, "name": "X (Twitter)"},
            "instagram": {"max_length": 2200, "name": "Instagram"},
            "linkedin": {"max_length": 3000, "name": "LinkedIn"},
            "note": {"max_length": 100000, "name": "note"},
            "line": {"max_length": 5000, "name": "LINE"},
        }

        platform_lower = platform.lower()
        if platform_lower in platform_limits:
            limit = platform_limits[platform_lower]
            if len(content) > limit["max_length"]:
                errors.append(
                    f"{limit['name']}: 文字数超過 ({len(content)}/{limit['max_length']})"
                )

        if platform_lower in ["newsletter", "email", "line"]:
            if "配信解除" not in content and "unsubscribe" not in content.lower():
                warnings.append("配信解除リンクが見つかりません（特定電子メール法）")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "platform": platform,
            "content_length": len(content),
        }

    def get_system_prompt(self) -> str:
        """Get Distributor specific system prompt."""
        return f"""あなたは Virtus の Distributor（配信処理）エージェントです。

あなたの役割:
- 各プラットフォームへの予約投稿準備
- 配信タイミング最適化
- 規約遵守の確認

以下のブランドDNAを完全に遵守してください:

{self.format_brand_dna()}

重要な原則:
- ブラウザ自動化禁止（規約違反）
- 公式API経由のみ
- 配信前に必ず人間承認を経由
- 特定電子メール法遵守
"""
