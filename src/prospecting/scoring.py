"""能動営業ターゲットのスコアリング.

active-prospecting スキルの 6 軸ルーブリックを実装.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.prospecting.sources import PressRelease

_REVENUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"売上高?\s*[\d,，]+\s*(億|百万|千万|万)\s*円"),
    re.compile(r"年商\s*[\d,，]+\s*(億|百万|千万|万)\s*円"),
    re.compile(r"ARR\s*[\d,，]+\s*(億|百万|千万|万)\s*円"),
    re.compile(r"[\d,，]+\s*億\s*円"),
)

_FUNDING_KEYWORDS = (
    "資金調達",
    "Series A",
    "シリーズ A",
    "Series B",
    "シリーズ B",
    "Series C",
    "シードラウンド",
    "プレシリーズ",
    "出資",
    "ラウンド",
)

_HIRING_KEYWORDS = (
    "採用拡大",
    "人員増",
    "増員",
    "採用強化",
    "新規採用",
    "募集中",
    "人材募集",
)

_INDUSTRY_TOP_KEYWORDS = (
    "業界トップ",
    "業界 No.1",
    "業界第 1 位",
    "国内最大",
    "シェア 1 位",
    "リーディングカンパニー",
    "リーディング企業",
)


@dataclass
class LeadScore:
    """1 件のプレスリリースに対するスコア結果."""

    release: PressRelease
    score: int
    breakdown: dict[str, int] = field(default_factory=dict)
    matched_industries: tuple[str, ...] = field(default_factory=tuple)

    @property
    def priority(self) -> str:
        """スキル定義に従う優先度バンド."""
        if self.score >= 90:
            return "S"
        if self.score >= 80:
            return "A"
        if self.score >= 70:
            return "B"
        if self.score >= 60:
            return "C"
        return "skip"


def score_release(
    release: PressRelease,
    target_industries: list[str] | None = None,
    decision_maker_identified: bool = False,
) -> LeadScore:
    """1 件のプレスリリースをスコアリング.

    Args:
        release: プレスリリース.
        target_industries: 顧客のターゲット業界キーワード.
        decision_maker_identified: 別途 LinkedIn 等で決済権者特定済みか.

    Returns:
        LeadScore.
    """
    target_industries = target_industries or []
    text = f"{release.title}\n{release.description}"

    breakdown = {
        "revenue": _score_revenue(text),
        "funding": _score_funding(text),
        "hiring": _score_hiring(text),
        "press_frequency": 0,  # 集計レイヤで後付け
        "industry_top": _score_industry_top(text),
        "decision_maker": 15 if decision_maker_identified else 0,
    }

    matched_industries = tuple(
        industry
        for industry in target_industries
        if industry and industry in text
    )

    score = sum(breakdown.values())
    return LeadScore(
        release=release,
        score=min(score, 100),
        breakdown=breakdown,
        matched_industries=matched_industries,
    )


def matches_target_industry(
    release: PressRelease, target_industries: list[str]
) -> bool:
    """業界キーワードのいずれかが本文・カテゴリに含まれるか."""
    if not target_industries:
        return True
    haystacks = [
        release.title,
        release.description,
        *release.categories,
    ]
    blob = "\n".join(haystacks)
    return any(industry and industry in blob for industry in target_industries)


def _score_revenue(text: str) -> int:
    """売上シグナルを検出 (max 25)."""
    return 25 if any(p.search(text) for p in _REVENUE_PATTERNS) else 0


def _score_funding(text: str) -> int:
    """資金調達シグナルを検出 (max 25)."""
    return 25 if any(kw in text for kw in _FUNDING_KEYWORDS) else 0


def _score_hiring(text: str) -> int:
    """採用シグナルを検出 (max 15)."""
    return 15 if any(kw in text for kw in _HIRING_KEYWORDS) else 0


def _score_industry_top(text: str) -> int:
    """業界トップ層シグナルを検出 (max 10)."""
    return 10 if any(kw in text for kw in _INDUSTRY_TOP_KEYWORDS) else 0
