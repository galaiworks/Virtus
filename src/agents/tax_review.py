"""税理士エージェント出力の Guardian 連携(quality-95.md / tax-compliance.md §6)。

TaxAccountant の出力を Guardian 95 点ループに通す。税務ドメインでは:

- **エスカレーション出力は「正しい安全側の挙動」** なので、独占業務を検出して停止した
  こと自体を合格(PASS)として扱う。逃げずに止めたことを咎めない。
- **通常出力は免責事項と過剰約束を厳格チェック**。免責が無ければ Guardian が
  force_reject する(独占業務との境界明示が必須)。

生成(TaxAccountant)と検証(Guardian)を分離する設計原則 #4 に従う。
"""

from __future__ import annotations

from typing import Any

from src.agents.base import AgentResult
from src.officina.governance.guardian_gate import GuardianGate
from src.officina.models import GateResult, GateType, Verdict


def result_to_review_text(result: AgentResult) -> str:
    """AgentResult を Guardian が採点できるテキストへ平坦化する。"""
    parts: list[str] = []
    out = result.output

    disclaimer = out.get("disclaimer")
    if disclaimer:
        parts.append(str(disclaimer))

    message = out.get("message")
    if message:
        parts.append(str(message))

    res = out.get("result")
    if isinstance(res, dict):
        for key in ("note", "message"):
            if res.get(key):
                parts.append(str(res[key]))
        # 主要な数値・科目も本文に含め、実体のあるコンテンツとして採点させる。
        parts.append(
            " ".join(
                f"{k}:{v}"
                for k, v in res.items()
                if k not in {"note", "message"} and not isinstance(v, (dict, list))
            )
        )
    elif res is not None:
        parts.append(str(res))

    return "\n".join(p for p in parts if p.strip())


def review_tax_result(result: AgentResult, guardian: GuardianGate) -> GateResult:
    """TaxAccountant の出力を Guardian で検証する。

    Args:
        result: ``TaxAccountant.execute`` の戻り値。
        guardian: 検証に用いる ``GuardianGate``(生成側と別インスタンス)。

    Returns:
        ``GateResult``。エスカレーション出力は安全側として PASS。
    """
    # 独占業務を検出して人間税理士へ回付した出力は「正しい挙動」。合格扱い。
    if result.content_type == "escalation":
        verdict = result.output.get("boundary_verdict", "escalate_to_zeirishi")
        return GateResult(
            gate_type=GateType.GUARDIAN,
            verdict=Verdict.PASS,
            score=100.0,
            reasons=[f"独占業務を正しくエスカレーション(boundary_verdict={verdict})"],
            details={"safe_escalation": True, "boundary_verdict": verdict},
        )

    text = result_to_review_text(result)
    return guardian.evaluate(text, content_type="tax_support")


def guardian_for(brand_dna: dict[str, Any] | None = None, llm: Any | None = None) -> GuardianGate:
    """税務レビュー用の GuardianGate を生成するショートカット。"""
    return GuardianGate(threshold=95, brand_dna=brand_dna or {}, llm=llm)
