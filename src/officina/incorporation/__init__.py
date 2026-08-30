"""法人設立・助成金・節税の伴走層(クロエ)。

`docs/chloe-service-roadmap.md` の Phase 1 実装。

構成:
- ``state``: 意思決定・ウォッチリスト・回収額台帳の単一の真実(B-7)
- ``rules``: 判断の型(インボイス・資本金・役員報酬・家族分散)
- ``grants``: 助成金/補助金の適格性判定・締切逆算・週次モニタ(B-8)
- ``escalation``: escalation.md の Level 1〜4 へのマッピング(B-6)
"""

from __future__ import annotations

from src.officina.incorporation.escalation import (
    EscalationTrigger,
    check_escalations,
)
from src.officina.incorporation.grants import (
    Eligibility,
    GrantProgram,
    GrantStatus,
    default_programs,
    evaluate_eligibility,
    weekly_check,
)
from src.officina.incorporation.rules import (
    capital_advice,
    family_split_advice,
    invoice_advice,
    officer_comp_advice,
)
from src.officina.incorporation.state import (
    Decision,
    IncorporationState,
    ValueEntry,
)

__all__ = [
    "Decision",
    "Eligibility",
    "EscalationTrigger",
    "GrantProgram",
    "GrantStatus",
    "IncorporationState",
    "ValueEntry",
    "capital_advice",
    "check_escalations",
    "default_programs",
    "evaluate_eligibility",
    "family_split_advice",
    "invoice_advice",
    "officer_comp_advice",
    "weekly_check",
]
