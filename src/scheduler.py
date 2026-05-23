"""Virtus Scheduler - cron-style task scheduling."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Any


@dataclass
class ScheduledTask:
    """A scheduled recurring task."""

    name: str
    hour: int
    minute: int
    callback: Callable[[], Any]
    last_run: datetime | None = None
    enabled: bool = True
    weekday_only: bool = False
    description: str = ""


@dataclass
class Scheduler:
    """Simple in-process scheduler for Virtus daily/weekly tasks."""

    tasks: list[ScheduledTask] = field(default_factory=list)

    def add_task(
        self,
        name: str,
        hour: int,
        minute: int,
        callback: Callable[[], Any],
        weekday_only: bool = False,
        description: str = "",
    ) -> None:
        """Register a recurring task."""
        self.tasks.append(
            ScheduledTask(
                name=name,
                hour=hour,
                minute=minute,
                callback=callback,
                weekday_only=weekday_only,
                description=description,
            )
        )

    def get_due_tasks(self, now: datetime | None = None) -> list[ScheduledTask]:
        """Return tasks that should run now."""
        now = now or datetime.now()
        due = []
        for task in self.tasks:
            if not task.enabled:
                continue
            if task.weekday_only and now.weekday() >= 5:
                continue
            target_time = time(task.hour, task.minute)
            if now.time() >= target_time and (
                task.last_run is None or task.last_run.date() < now.date()
            ):
                due.append(task)
        return due

    def run_due_tasks(self, now: datetime | None = None) -> list[dict[str, Any]]:
        """Run all due tasks and return results."""
        now = now or datetime.now()
        results = []
        for task in self.get_due_tasks(now):
            try:
                output = task.callback()
                task.last_run = now
                results.append(
                    {
                        "task": task.name,
                        "success": True,
                        "output": output,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "task": task.name,
                        "success": False,
                        "error": str(e),
                    }
                )
        return results

    def next_run(self, task_name: str, now: datetime | None = None) -> datetime | None:
        """Calculate the next run time for a task."""
        now = now or datetime.now()
        task = next((t for t in self.tasks if t.name == task_name), None)
        if not task:
            return None

        target = now.replace(hour=task.hour, minute=task.minute, second=0, microsecond=0)
        if target <= now or (task.last_run and task.last_run.date() == now.date()):
            target += timedelta(days=1)

        if task.weekday_only:
            while target.weekday() >= 5:
                target += timedelta(days=1)

        return target

    def list_tasks(self) -> list[dict[str, Any]]:
        """List all registered tasks."""
        return [
            {
                "name": t.name,
                "schedule": f"{t.hour:02d}:{t.minute:02d}",
                "weekday_only": t.weekday_only,
                "enabled": t.enabled,
                "last_run": t.last_run.isoformat() if t.last_run else None,
                "description": t.description,
            }
            for t in self.tasks
        ]


def build_default_scheduler(orchestrator: Any) -> Scheduler:
    """Build the default Virtus daily schedule.

    Default schedule:
    - 05:00 - Researcher trends + Analyst data collection
    - 07:00 - Lead Strategist morning brief
    - 09:00 (Mon) - Weekly review
    - 23:00 - Daily wrap-up logs
    """
    scheduler = Scheduler()

    scheduler.add_task(
        name="morning_brief",
        hour=7,
        minute=0,
        callback=lambda: orchestrator.morning_brief(
            {
                "current_date": datetime.now().date().isoformat(),
            }
        ),
        description="毎朝7時の朝報生成",
    )

    scheduler.add_task(
        name="weekly_review",
        hour=9,
        minute=0,
        callback=lambda: orchestrator.lead_strategist.execute(
            {
                "task_type": "weekly_review",
                "context": {},
            }
        ),
        weekday_only=True,
        description="毎週月曜9時の週次レビュー（手動でstartingDateを指定）",
    )

    return scheduler
