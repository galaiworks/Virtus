"""Outreach — ステージ 2:多 ch ファーストタッチ(Virtus: Distributor)。

合格ゲート:deliverability 健全性・送信量上限(決定論)。
アウトリーチ文面は特定電子メール法に従い送信者情報と配信解除動線を必ず含める。
"""

from __future__ import annotations

from typing import Any

from src.agents.base import AgentResult, BaseAgent
from src.officina.governance.deliverability import DeliverabilityMetrics


class Outreach(BaseAgent):
    name = "outreach"

    def execute(self, task: dict[str, Any]) -> AgentResult:
        lead = task.get("lead", {})
        sender = self.brand_dna.get("identity", {}).get("name", "galaiworks")
        body = task.get("body") or (
            f"{lead.get('contact', 'ご担当者')} 様\n\n"
            f"{sender} と申します。{lead.get('company', '貴社')} の取り組みを拝見し、"
            "ご連絡しました。\n\n"
            "ご興味があれば 15 分ほどお時間をいただけますでしょうか。\n\n"
            f"---\n送信者: {sender}\n"
            "本メールの配信停止をご希望の場合はこちらから解除いただけます。\n"
        )
        metrics_in = task.get("deliverability", {})
        metrics = DeliverabilityMetrics(
            bounce_rate=metrics_in.get("bounce_rate", 0.0),
            complaint_rate=metrics_in.get("complaint_rate", 0.0),
            domain_reputation=metrics_in.get("domain_reputation", 100.0),
            sent_today=metrics_in.get("sent_today", 0),
            domain_age_days=metrics_in.get("domain_age_days", 999),
        )
        return AgentResult(
            agent=self.name,
            content_type="outreach_email",
            output={
                "content": body,
                "channel": task.get("channel", "email"),
                "gate": {
                    "metrics": metrics,
                    "opt_out": bool(task.get("opt_out", False)),
                    "touch_count": int(task.get("touch_count", 0)),
                },
            },
            meta={"stage": 2},
        )
