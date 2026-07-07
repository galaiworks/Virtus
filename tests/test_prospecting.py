"""Prospecting (ソース + スコアリング) のテスト."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.prospecting.scoring import (
    LeadScore,
    matches_target_industry,
    score_release,
)
from src.prospecting.sources import PressRelease, PRTimesRSSSource

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "prtimes_sample.rdf"


def _make_release(
    title: str = "テスト",
    description: str = "",
    published_at: datetime | None = None,
    categories: tuple[str, ...] = (),
) -> PressRelease:
    return PressRelease(
        source_id=f"id_{title}",
        title=title,
        description=description,
        url=f"https://example.com/{title}",
        published_at=published_at or datetime.now(timezone.utc),
        company="テスト会社",
        categories=categories,
    )


def test_parse_rdf_extracts_three_items():
    """フィクスチャから 3 件パース."""
    text = FIXTURE_PATH.read_text(encoding="utf-8")
    releases = PRTimesRSSSource.parse_rss(text)
    assert len(releases) == 3
    assert releases[0].title.startswith("株式会社サンプル AI")
    assert releases[0].company == "株式会社サンプル AI"
    assert "AI" in releases[0].categories
    assert releases[0].published_at.tzinfo is not None


def test_score_release_detects_funding_revenue_and_hiring():
    """資金調達 + 売上 + 採用拡大の 3 シグナルを検出."""
    release = _make_release(
        title="株式会社サンプル AI、シリーズ A で 5 億円の資金調達",
        description="年商 12 億円規模を見据え、採用拡大を進めます。",
    )
    score = score_release(release)
    assert score.breakdown["funding"] == 25
    assert score.breakdown["revenue"] == 25
    assert score.breakdown["hiring"] == 15
    assert score.score == 65  # 25+25+15
    assert score.priority == "C"


def test_score_with_decision_maker_pushes_into_high_priority():
    """決済権者特定済みなら +15、80 点超で A 優先度."""
    release = _make_release(
        title="株式会社サンプル AI、シリーズ A で 5 億円の資金調達",
        description="年商 12 億円規模を見据え、採用拡大を進めます。",
    )
    score = score_release(release, decision_maker_identified=True)
    assert score.score == 80
    assert score.priority == "A"


def test_funding_amount_does_not_double_count_as_revenue():
    """調達額の「N 億円」を売上シグナルとして二重計上しない."""
    release = _make_release(
        title="株式会社サンプル、シリーズ A で 5 億円の資金調達",
        description="調達資金はプロダクト開発に充当します。",
    )
    score = score_release(release)
    assert score.breakdown["funding"] == 25
    assert score.breakdown["revenue"] == 0  # 年商/売上/ARR の明示がない
    assert score.score == 25


def test_score_low_signal_release_skipped():
    """シグナルなしのリリースはスキップ判定."""
    release = _make_release(
        title="株式会社レガシー、新製品の発表",
        description="新製品「○○」を発売します。",
    )
    score = score_release(release)
    assert score.score == 0
    assert score.priority == "skip"


def test_matches_target_industry_uses_categories():
    """カテゴリも業界判定に含む."""
    release = _make_release(
        title="製品 X 発売",
        description="",
        categories=("SaaS", "AI"),
    )
    assert matches_target_industry(release, ["SaaS"]) is True
    assert matches_target_industry(release, ["ヘルスケア"]) is False
    # 空リストは通過
    assert matches_target_industry(release, []) is True


def test_lead_score_priority_bands():
    """LeadScore.priority がスコアバンドに従う."""
    rel = _make_release()
    assert LeadScore(release=rel, score=95).priority == "S"
    assert LeadScore(release=rel, score=85).priority == "A"
    assert LeadScore(release=rel, score=75).priority == "B"
    assert LeadScore(release=rel, score=65).priority == "C"
    assert LeadScore(release=rel, score=50).priority == "skip"


def test_fetch_filters_by_period(monkeypatch):
    """fetch は period_hours より古いリリースを除外.

    フィクスチャは 2030 年 (未来) と 2020 年 (古い) の混在。
    実行時の「今」を基準に period_hours=24 で絞ると、未来分のみ残る.
    """
    rss_text = FIXTURE_PATH.read_text(encoding="utf-8")
    source = PRTimesRSSSource()

    class _StubResp:
        def __init__(self, body: str) -> None:
            self.text = body

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(source.client, "get", lambda url: _StubResp(rss_text))

    # 2030 年の 2 件は cutoff より新しい (未来)、2020 年は古い
    recent = source.fetch(period_hours=24)
    assert len(recent) == 2
    assert all(r.published_at.year == 2030 for r in recent)
    source.close()


def test_fetch_propagates_http_error(monkeypatch):
    """4xx/5xx は httpx の raise_for_status で例外伝播."""
    import httpx

    source = PRTimesRSSSource()

    class _ErrResp:
        text = ""

        def raise_for_status(self) -> None:
            raise httpx.HTTPStatusError("500", request=None, response=None)

    monkeypatch.setattr(source.client, "get", lambda url: _ErrResp())

    with pytest.raises(httpx.HTTPStatusError):
        source.fetch()
    source.close()
