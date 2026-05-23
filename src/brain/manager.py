"""Brain Manager - 永続記憶層の管理."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ..utils.logger import get_logger


class BrainManager:
    """
    Brain層の管理

    永続記憶を管理し、各エージェントに必要なデータを提供する。

    構造:
    brain/
    ├── customers/{customer_id}/
    │   ├── brand-dna.yaml
    │   ├── profile.json
    │   └── kpi-targets.json
    ├── content-history/{customer_id}/
    ├── leads/{customer_id}/
    ├── deals/{customer_id}/
    ├── win-patterns/{customer_id}/
    └── active.md
    """

    def __init__(self, brain_path: Path | str, customer_id: str):
        self.brain_path = Path(brain_path)
        self.customer_id = customer_id
        self.logger = get_logger("virtus.brain")

        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            self.brain_path / "customers" / self.customer_id,
            self.brain_path / "content-history" / self.customer_id,
            self.brain_path / "leads" / self.customer_id,
            self.brain_path / "deals" / self.customer_id,
            self.brain_path / "win-patterns" / self.customer_id,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def save_content(
        self,
        content_type: str,
        content: Any,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Save generated content."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        content_id = f"{content_type}_{timestamp}"

        content_dir = self.brain_path / "content-history" / self.customer_id / content_type
        content_dir.mkdir(parents=True, exist_ok=True)

        content_file = content_dir / f"{content_id}.json"
        data = {
            "id": content_id,
            "type": content_type,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
        }

        with open(content_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Saved content: {content_id}")
        return content_id

    def get_content(self, content_id: str) -> dict[str, Any] | None:
        """Retrieve content by ID."""
        for content_type_dir in (self.brain_path / "content-history" / self.customer_id).iterdir():
            if content_type_dir.is_dir():
                content_file = content_type_dir / f"{content_id}.json"
                if content_file.exists():
                    with open(content_file, encoding="utf-8") as f:
                        return json.load(f)
        return None

    def save_lead(self, lead: dict[str, Any]) -> str:
        """Save a lead."""
        lead_id = lead.get("id") or f"lead_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        lead["id"] = lead_id

        leads_file = self.brain_path / "leads" / self.customer_id / "active.json"
        leads = self._load_json(leads_file, default=[])
        leads.append(lead)
        self._save_json(leads_file, leads)

        self.logger.info(f"Saved lead: {lead_id}")
        return lead_id

    def get_leads(self, status: str = "active") -> list[dict[str, Any]]:
        """Get leads by status."""
        leads_file = self.brain_path / "leads" / self.customer_id / f"{status}.json"
        return self._load_json(leads_file, default=[])

    def save_deal(self, deal: dict[str, Any]) -> str:
        """Save a deal."""
        deal_id = deal.get("id") or f"deal_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        deal["id"] = deal_id

        pipeline_file = self.brain_path / "deals" / self.customer_id / "pipeline.json"
        pipeline = self._load_json(pipeline_file, default=[])
        pipeline.append(deal)
        self._save_json(pipeline_file, pipeline)

        self.logger.info(f"Saved deal: {deal_id}")
        return deal_id

    def get_pipeline(self) -> list[dict[str, Any]]:
        """Get current deal pipeline."""
        pipeline_file = self.brain_path / "deals" / self.customer_id / "pipeline.json"
        return self._load_json(pipeline_file, default=[])

    def update_win_patterns(self, patterns: Any) -> None:
        """Update winning patterns."""
        patterns_file = self.brain_path / "win-patterns" / self.customer_id / "patterns.json"
        existing = self._load_json(patterns_file, default={"patterns": [], "updated_at": None})

        if isinstance(patterns, str):
            existing["patterns"].append({
                "content": patterns,
                "extracted_at": datetime.now().isoformat(),
            })
        elif isinstance(patterns, dict):
            existing["patterns"].append(patterns)
        elif isinstance(patterns, list):
            existing["patterns"].extend(patterns)

        existing["updated_at"] = datetime.now().isoformat()
        self._save_json(patterns_file, existing)

        self.logger.info("Updated win patterns")

    def get_win_patterns(self) -> dict[str, Any]:
        """Get winning patterns."""
        patterns_file = self.brain_path / "win-patterns" / self.customer_id / "patterns.json"
        return self._load_json(patterns_file, default={"patterns": [], "updated_at": None})

    def get_yesterday_summary(self) -> dict[str, Any] | None:
        """Get yesterday's summary."""
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        summary_dir = self.brain_path / "content-history" / self.customer_id / "daily_summary"

        if summary_dir.exists():
            for f in summary_dir.iterdir():
                if yesterday in f.name:
                    with open(f, encoding="utf-8") as file:
                        return json.load(file)
        return None

    def get_weekly_goals(self) -> dict[str, Any] | None:
        """Get current week's goals."""
        goals_file = self.brain_path / "customers" / self.customer_id / "weekly_goals.json"
        return self._load_json(goals_file, default=None)

    def get_monthly_goals(self) -> dict[str, Any] | None:
        """Get current month's goals."""
        goals_file = self.brain_path / "customers" / self.customer_id / "monthly_goals.json"
        return self._load_json(goals_file, default=None)

    def get_today_performance(self) -> dict[str, Any]:
        """Get today's performance data."""
        today = datetime.now().strftime("%Y%m%d")
        return {
            "date": today,
            "content_published": self._count_content_today(),
            "leads_generated": len(self.get_leads()),
            "deals_active": len(self.get_pipeline()),
        }

    def get_week_data(self) -> dict[str, Any]:
        """Get current week's data."""
        return {
            "kpi": self.get_weekly_goals(),
            "content_performance": self.get_content_performance(),
            "leads_deals": {
                "leads": len(self.get_leads()),
                "pipeline": len(self.get_pipeline()),
            },
        }

    def get_month_data(self) -> dict[str, Any]:
        """Get current month's data."""
        return {
            "kpi": self.get_monthly_goals(),
            "content": self.get_content_performance(),
            "leads": len(self.get_leads()),
            "deals": self.get_pipeline(),
            "win_patterns": self.get_win_patterns(),
        }

    def get_content_performance(self) -> list[dict[str, Any]]:
        """Get content performance data."""
        performance_file = self.brain_path / "content-history" / self.customer_id / "performance.json"
        return self._load_json(performance_file, default=[])

    def get_outreach_performance(self) -> list[dict[str, Any]]:
        """Get outreach performance data."""
        outreach_file = self.brain_path / "content-history" / self.customer_id / "outreach_performance.json"
        return self._load_json(outreach_file, default=[])

    def get_deal_performance(self) -> list[dict[str, Any]]:
        """Get deal performance data."""
        return self.get_pipeline()

    def _count_content_today(self) -> int:
        """Count content published today."""
        today = datetime.now().strftime("%Y%m%d")
        count = 0
        content_dir = self.brain_path / "content-history" / self.customer_id

        if content_dir.exists():
            for type_dir in content_dir.iterdir():
                if type_dir.is_dir():
                    for f in type_dir.iterdir():
                        if today in f.name:
                            count += 1
        return count

    def _load_json(self, path: Path, default: Any = None) -> Any:
        """Load JSON file safely."""
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                self.logger.warning(f"Failed to parse JSON: {path}")
        return default

    def _save_json(self, path: Path, data: Any) -> None:
        """Save data to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
