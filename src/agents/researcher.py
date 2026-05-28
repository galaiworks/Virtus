"""Researcher - 能動営業ターゲット探索エージェント."""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent
from src.brain.store import BrainStore
from src.prospecting.scoring import LeadScore, matches_target_industry, score_release
from src.prospecting.sources import ProspectingSource


class Researcher(BaseAgent):
    """探索・調査エージェント.

    Phase 1 では PR タイムズ等のプレスリリースを取得 → スコアリング → Brain に保存.
    LLM 呼び出しはオンデマンドで決済権者特定のリサーチ要約に使う想定 (今回は未使用).
    """

    SUPPORTED_TASKS = frozenset({"active_prospecting"})

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        brand_dna: dict[str, Any],
        sources: list[ProspectingSource],
        store: BrainStore,
        skills: list[str] | None = None,
        client: Any | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            brand_dna=brand_dna,
            skills=skills,
            client=client,
        )
        if not sources:
            raise ValueError("Researcher には最低 1 つのソースが必要です")
        self.sources = sources
        self.store = store

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        task_type = task.get("task_type")
        if task_type not in self.SUPPORTED_TASKS:
            raise ValueError(f"Researcher は task_type={task_type} をサポートしていません")
        return self.active_prospecting(task.get("context", {}))

    def active_prospecting(self, context: dict[str, Any]) -> dict[str, Any]:
        """PR タイムズ等から能動営業ターゲットを抽出.

        Args:
            context: {target_industries, period_hours, top_n, min_score}.

        Returns:
            {"leads": [...], "count": N, "skipped": M}.
        """
        target_industries = context.get("target_industries", [])
        period_hours = int(context.get("period_hours", 24))
        top_n = int(context.get("top_n", 50))
        min_score = int(context.get("min_score", 60))

        # 1. 各ソースから取得
        all_releases: list = []
        per_source_counts: dict[str, int] = {}
        for source in self.sources:
            releases = source.fetch(period_hours=period_hours)
            per_source_counts[source.name] = len(releases)
            all_releases.extend(releases)

        # 2. 業界フィルタ
        filtered = [
            r for r in all_releases if matches_target_industry(r, target_industries)
        ]

        # 3. スコアリング
        scored: list[LeadScore] = [
            score_release(r, target_industries=target_industries) for r in filtered
        ]

        # 4. min_score でカット & 上位 N 件
        qualified = sorted(
            (lead for lead in scored if lead.score >= min_score),
            key=lambda lead: (lead.score, lead.release.published_at),
            reverse=True,
        )[:top_n]

        # 5. Brain に保存
        for lead in qualified:
            self.store.upsert_lead(source="prospecting", lead=lead)

        # 6. 監査ログ
        self.store.log_audit(
            agent="Researcher",
            action="active_prospecting",
            payload={
                "fetched": per_source_counts,
                "after_industry_filter": len(filtered),
                "after_scoring": len(scored),
                "qualified": len(qualified),
                "target_industries": target_industries,
                "period_hours": period_hours,
                "min_score": min_score,
                "top_n": top_n,
            },
        )

        return {
            "leads": [
                {
                    "score": lead.score,
                    "priority": lead.priority,
                    "title": lead.release.title,
                    "url": lead.release.url,
                    "company": lead.release.company,
                    "breakdown": lead.breakdown,
                    "matched_industries": list(lead.matched_industries),
                    "published_at": lead.release.published_at.isoformat(),
                }
                for lead in qualified
            ],
            "count": len(qualified),
            "skipped": len(scored) - len(qualified),
            "fetched_by_source": per_source_counts,
        }
