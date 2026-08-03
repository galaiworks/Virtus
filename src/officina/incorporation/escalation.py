"""クロエのエスカレーション判定(設計レビュー B-6)。

`.claude/rules/escalation.md` の Level 1〜4 へ、設立支援固有の事象を
マッピングする。通知計画の生成は既存の
``src.officina.governance.hitl.escalate`` を再利用する
(通知チャネルの定義を二重管理しないため)。

Level の割り当て方針:
- Level 2:判断がつかず専門家確認を促すべきもの(24 時間以内)
- Level 3:放置すると金銭的損失・制度の取り逃しが確定するもの(4 時間以内)
- Level 4:法令・否認リスクに直結するもの(1 時間以内)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from src.officina.governance.hitl import escalate

#: 締切までの残日数がこれ以下で未着手なら Level 3。
DEADLINE_CRITICAL_DAYS = 7

#: 締切までの残日数がこれ以下なら Level 2(注意喚起)。
DEADLINE_WARNING_DAYS = 14

#: 準備に着手済みとみなすステータス。
_IN_PROGRESS_STATUSES = {"preparing", "applied", "adopted", "closed", "rejected"}


@dataclass
class EscalationTrigger:
    """エスカレーション 1 件。"""

    level: int
    reason: str
    details: dict[str, Any] = field(default_factory=dict)

    def notify(self) -> dict[str, Any]:
        """通知計画を生成する(既存の escalate を再利用)。"""
        return escalate(self.level, self.reason, self.details)


def check_deadlines(
    watchlist: dict[str, dict[str, Any]],
    *,
    today: date | None = None,
) -> list[EscalationTrigger]:
    """助成金の締切が迫っているのに未着手のものを検出する。

    Args:
        watchlist: ``{key: {"name", "deadline"(ISO 文字列), "status"}}``。
        today: 判定基準日。

    Returns:
        ``EscalationTrigger`` のリスト。
    """
    base = today or date.today()
    triggers: list[EscalationTrigger] = []

    for key, item in watchlist.items():
        deadline_raw = item.get("deadline")
        if not deadline_raw:
            continue
        try:
            deadline = date.fromisoformat(str(deadline_raw))
        except ValueError:
            continue

        days_left = (deadline - base).days
        status = str(item.get("status", "watching"))
        name = str(item.get("name", key))

        if days_left < 0 or status in _IN_PROGRESS_STATUSES:
            continue

        details = {"key": key, "name": name, "deadline": deadline.isoformat(), "days_left": days_left}

        if days_left <= DEADLINE_CRITICAL_DAYS:
            triggers.append(
                EscalationTrigger(
                    level=3,
                    reason=f"補助金締切まで残り {days_left} 日で未着手: {name}",
                    details=details,
                )
            )
        elif days_left <= DEADLINE_WARNING_DAYS:
            triggers.append(
                EscalationTrigger(
                    level=2,
                    reason=f"補助金締切が近づいている(残り {days_left} 日): {name}",
                    details=details,
                )
            )

    triggers.sort(key=lambda t: -t.level)
    return triggers


def check_social_insurance_gap(profile: dict[str, Any]) -> list[EscalationTrigger]:
    """退職日と社会保険加入日の空白(無保険期間)を検出する。

    Args:
        profile: ``employment`` / ``resignation_date`` / ``establishment_date`` を持つ。

    Returns:
        ``EscalationTrigger`` のリスト。
    """
    if str(profile.get("employment", "")).lower() != "full_time":
        return []

    resignation = _parse_date(profile.get("resignation_date"))
    establishment = _parse_date(profile.get("establishment_date"))
    if resignation is None or establishment is None:
        return [
            EscalationTrigger(
                level=2,
                reason="専業化にあたり退職日または設立日が未確定(社保の空白リスク)",
                details={
                    "resignation_date": profile.get("resignation_date"),
                    "establishment_date": profile.get("establishment_date"),
                },
            )
        ]

    gap_days = (establishment - resignation).days
    if gap_days > 1:
        return [
            EscalationTrigger(
                level=3,
                reason=f"退職から設立まで {gap_days} 日の社会保険の空白が発生する",
                details={
                    "resignation_date": resignation.isoformat(),
                    "establishment_date": establishment.isoformat(),
                    "gap_days": gap_days,
                    "remedy": "任意継続または国民健康保険でつなぐ",
                },
            )
        ]
    return []


def check_substance_risk(
    family_salaries: list[dict[str, Any]] | None,
) -> list[EscalationTrigger]:
    """実態のない家族給与(架空人件費)のリスクを検出する。

    Args:
        family_salaries: 各要素に ``relation`` / ``salary_jpy`` / ``can_work_on`` を持つ。

    Returns:
        ``EscalationTrigger`` のリスト。Level 4(否認リスク直結)。
    """
    triggers: list[EscalationTrigger] = []
    for member in family_salaries or []:
        salary = int(member.get("salary_jpy", 0) or 0)
        duties = str(member.get("can_work_on", "") or "").strip()
        if salary > 0 and not duties:
            triggers.append(
                EscalationTrigger(
                    level=4,
                    reason=(
                        f"従事実態が未確認のまま {member.get('relation', '家族')} へ "
                        f"年 {salary:,} 円の給与を設定しようとしている(否認リスク)"
                    ),
                    details={
                        "relation": member.get("relation"),
                        "salary_jpy": salary,
                        "remedy": "実際の職務内容と稼働を先に確定させる",
                    },
                )
            )
    return triggers


def check_escalations(
    state: Any,
    *,
    today: date | None = None,
) -> list[EscalationTrigger]:
    """状態全体を走査してエスカレーションを検出する。

    Args:
        state: ``IncorporationState``(``profile`` と ``watchlist`` を参照)。
        today: 判定基準日。

    Returns:
        Level の高い順に並べた ``EscalationTrigger`` のリスト。
    """
    profile: dict[str, Any] = getattr(state, "profile", {}) or {}
    watchlist: dict[str, dict[str, Any]] = getattr(state, "watchlist", {}) or {}

    triggers: list[EscalationTrigger] = []
    triggers.extend(check_substance_risk(profile.get("family_salaries")))
    triggers.extend(check_deadlines(watchlist, today=today))
    triggers.extend(check_social_insurance_gap(profile))
    triggers.sort(key=lambda t: -t.level)
    return triggers


def _parse_date(value: Any) -> date | None:
    """ISO 文字列または ``date`` を ``date`` へ正規化する。"""
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None
