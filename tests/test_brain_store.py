"""Brain SQLite ストアのテスト."""

from __future__ import annotations

from datetime import datetime, timezone

from src.brain.store import BrainStore
from src.prospecting.scoring import LeadScore
from src.prospecting.sources import PressRelease


def _make_lead(source_id: str, score: int, title: str = "テスト") -> LeadScore:
    release = PressRelease(
        source_id=source_id,
        title=title,
        description="desc",
        url=f"https://example.com/{source_id}",
        published_at=datetime(2030, 5, 25, 10, 0, tzinfo=timezone.utc),
        company="テスト株式会社",
        categories=("SaaS",),
    )
    return LeadScore(
        release=release,
        score=score,
        breakdown={"revenue": 25, "funding": 25},
        matched_industries=("SaaS",),
    )


def test_upsert_and_query_top_leads():
    """upsert → top_leads がスコア降順で返る."""
    with BrainStore() as store:
        store.upsert_lead("prospecting", _make_lead("a", 65))
        store.upsert_lead("prospecting", _make_lead("b", 85))
        store.upsert_lead("prospecting", _make_lead("c", 55))  # min_score 未満

        top = store.top_leads(limit=10, min_score=60)
        scores = [row["score"] for row in top]
        assert scores == [85, 65]
        assert all(row["status"] == "new" for row in top)


def test_upsert_updates_existing_row():
    """同じ (source, source_id) は更新される."""
    with BrainStore() as store:
        store.upsert_lead("prospecting", _make_lead("a", 65, title="旧"))
        store.upsert_lead("prospecting", _make_lead("a", 88, title="新"))

        assert store.count_leads() == 1
        top = store.top_leads(min_score=0)
        assert top[0]["score"] == 88
        assert top[0]["title"] == "新"
        # created_at は維持、updated_at は更新される
        assert top[0]["created_at"] <= top[0]["updated_at"]


def test_log_audit_and_recent():
    """監査ログ書き込みと取得."""
    with BrainStore() as store:
        store.log_audit(
            agent="Researcher",
            action="active_prospecting",
            payload={"qualified": 12},
        )
        store.log_audit(
            agent="Guardian",
            action="evaluate",
            payload={"score": 96},
            content_id="content_xyz",
        )
        recent = store.recent_audit(limit=10)
        assert len(recent) == 2
        # 新しい順
        assert recent[0]["agent"] == "Guardian"
        assert recent[0]["payload"] == {"score": 96}
        assert recent[1]["agent"] == "Researcher"


def test_persistence_to_disk(tmp_path):
    """ディスクに永続化、再オープンで読める."""
    db = tmp_path / "brain.db"
    store = BrainStore(db_path=db)
    store.upsert_lead("prospecting", _make_lead("a", 90))
    store.close()

    reopened = BrainStore(db_path=db)
    top = reopened.top_leads(min_score=80)
    assert len(top) == 1
    assert top[0]["score"] == 90
    reopened.close()
