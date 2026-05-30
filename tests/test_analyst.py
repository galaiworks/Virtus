"""Analyst のテスト."""

from __future__ import annotations

from datetime import datetime, timezone

from src.agents.analyst import Analyst
from src.brain.store import BrainStore
from src.prospecting.scoring import LeadScore
from src.prospecting.sources import PressRelease
from tests.conftest import set_client_response


def _seed(store: BrainStore) -> None:
    base = datetime(2030, 5, 25, 10, 0, tzinfo=timezone.utc)
    for i, score in enumerate([95, 85, 65, 55]):
        rel = PressRelease(
            source_id=f"id_{i}",
            title=f"リリース {i} (スコア {score})",
            description="",
            url=f"https://example.com/{i}",
            published_at=base,
            company="会社",
            categories=("SaaS",),
        )
        store.upsert_lead("prospecting", LeadScore(release=rel, score=score))
    store.log_audit("Researcher", "active_prospecting", {"qualified": 4})
    store.log_audit("Guardian", "evaluate", {"score": 96})


def test_kpi_snapshot_aggregates_deterministically(
    galaiworks_brand_dna, fake_anthropic_client
):
    """KPI スナップショットは集計のみで LLM を呼ばない."""
    store = BrainStore()
    _seed(store)
    analyst = Analyst(
        api_key="x",
        model="claude-sonnet-4-6",
        brand_dna=galaiworks_brand_dna,
        store=store,
        client=fake_anthropic_client,
    )

    result = analyst.execute({"task_type": "kpi_snapshot"})

    assert result["leads"]["total"] == 4
    assert result["leads"]["by_priority"] == {"S": 1, "A": 1, "C": 1, "skip": 1}
    assert result["leads"]["average_score"] == 75.0
    assert "リリース 0" in result["leads"]["top_5_titles"][0]
    assert result["audit"]["total_events"] == 2
    assert result["audit"]["by_agent"] == {"Researcher": 1, "Guardian": 1}
    # LLM は呼ばれない
    fake_anthropic_client.messages.create.assert_not_called()
    store.close()


def test_monthly_review_includes_snapshot_in_user_message(
    galaiworks_brand_dna, fake_anthropic_client
):
    """月次レビューはスナップショットを含めて LLM に渡す."""
    set_client_response(fake_anthropic_client, "## 要約\n好調")
    store = BrainStore()
    _seed(store)
    analyst = Analyst(
        api_key="x",
        model="claude-sonnet-4-6",
        brand_dna=galaiworks_brand_dna,
        store=store,
        client=fake_anthropic_client,
    )

    result = analyst.execute(
        {
            "task_type": "monthly_review",
            "context": {
                "prior_month_summary": "前月 80 件",
                "kpi_targets": {"june_cash_target": 2_500_000},
            },
        }
    )

    assert result["report"].startswith("## 要約")
    assert "average_score" in str(result["snapshot"])
    user_msg = fake_anthropic_client.messages.create.call_args.kwargs["messages"][0][
        "content"
    ]
    assert "前月 80 件" in user_msg
    assert "2500000" in user_msg or "2,500,000" in user_msg
    store.close()
