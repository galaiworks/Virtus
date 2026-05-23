"""Virtus Scheduler - 自動実行スケジューラー."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Callable

import schedule

from .orchestrator import VirtusOrchestrator
from .utils.config import Config
from .utils.logger import get_logger


class VirtusScheduler:
    """
    Virtus Scheduler

    1日のスケジュールを自動実行する。

    スケジュール:
    - 05:00: 朝のワークフロー（情報収集）
    - 07:00: 朝報配信
    - 09:00: コンテンツ生成開始
    - 15:00: 配信フェーズ
    - 18:00: 関係構築フェーズ
    - 22:00: 学習フェーズ
    - 毎週月曜 09:00: ウィークリーレビュー
    - 毎月最終週: マンスリーレビュー
    """

    def __init__(self, orchestrator: VirtusOrchestrator):
        self.orchestrator = orchestrator
        self.logger = get_logger("virtus.scheduler")
        self._setup_schedule()

    def _setup_schedule(self) -> None:
        """Setup all scheduled tasks."""
        schedule.every().day.at("05:00").do(self._run_morning_research)
        schedule.every().day.at("07:00").do(self._run_morning_brief)
        schedule.every().day.at("22:00").do(self._run_learning)

        schedule.every().monday.at("09:00").do(self._run_weekly_review)

        self.logger.info("Schedule configured")

    def _run_morning_research(self) -> None:
        """Run morning research workflow."""
        self.logger.info("Running morning research")
        try:
            result = self.orchestrator.run_morning_workflow()
            if result.success:
                self.logger.info("Morning research completed successfully")
            else:
                self.logger.warning(f"Morning research had errors: {result.errors}")
        except Exception as e:
            self.logger.error(f"Morning research failed: {e}")

    def _run_morning_brief(self) -> None:
        """Run morning brief delivery."""
        self.logger.info("Running morning brief")

    def _run_learning(self) -> None:
        """Run learning workflow."""
        self.logger.info("Running learning workflow")
        try:
            result = self.orchestrator.run_learning_workflow()
            if result.success:
                self.logger.info("Learning workflow completed successfully")
            else:
                self.logger.warning(f"Learning workflow had errors: {result.errors}")
        except Exception as e:
            self.logger.error(f"Learning workflow failed: {e}")

    def _run_weekly_review(self) -> None:
        """Run weekly review."""
        self.logger.info("Running weekly review")
        try:
            result = self.orchestrator.run_weekly_review()
            if result.success:
                self.logger.info("Weekly review completed successfully")
            else:
                self.logger.warning(f"Weekly review had errors: {result.errors}")
        except Exception as e:
            self.logger.error(f"Weekly review failed: {e}")

    def _run_monthly_review(self) -> None:
        """Run monthly review."""
        self.logger.info("Running monthly review")
        try:
            result = self.orchestrator.run_monthly_review()
            if result.success:
                self.logger.info("Monthly review completed successfully")
            else:
                self.logger.warning(f"Monthly review had errors: {result.errors}")
        except Exception as e:
            self.logger.error(f"Monthly review failed: {e}")

    def run(self) -> None:
        """Run the scheduler loop."""
        self.logger.info("Starting Virtus scheduler")

        while True:
            schedule.run_pending()
            time.sleep(60)

    def run_once(self, task: str) -> None:
        """Run a specific task once."""
        tasks = {
            "morning_research": self._run_morning_research,
            "morning_brief": self._run_morning_brief,
            "learning": self._run_learning,
            "weekly_review": self._run_weekly_review,
            "monthly_review": self._run_monthly_review,
        }

        if task in tasks:
            tasks[task]()
        else:
            self.logger.error(f"Unknown task: {task}")


def main() -> None:
    """Main entry point for scheduler."""
    import yaml

    config = Config.from_env()
    errors = config.validate()
    if errors:
        print(f"Configuration errors: {errors}")
        return

    brand_dna_path = config.brain_path / "customers" / config.customer_id / "brand-dna.yaml"
    if brand_dna_path.exists():
        with open(brand_dna_path) as f:
            brand_dna = yaml.safe_load(f)
    else:
        brand_dna = {}

    orchestrator = VirtusOrchestrator(config, brand_dna)
    scheduler = VirtusScheduler(orchestrator)

    print("Virtus Scheduler started. Press Ctrl+C to stop.")
    try:
        scheduler.run()
    except KeyboardInterrupt:
        print("\nScheduler stopped.")


if __name__ == "__main__":
    main()
