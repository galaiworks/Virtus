"""Guardian - 品質保証・95点ループ."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .base import AgentResult, BaseAgent


@dataclass
class Violation:
    """Quality violation."""

    severity: str  # CRITICAL, MAJOR, MINOR
    category: str
    description: str
    location: str | None = None
    suggestion: str | None = None


@dataclass
class QualityEvaluation:
    """Quality evaluation result."""

    total_score: int
    axis_scores: dict[str, int]
    violations: list[Violation] = field(default_factory=list)
    feedback: str = ""
    approved: bool = False
    force_reject: bool = False


class Guardian(BaseAgent):
    """
    Guardian エージェント (Opus 4.7)

    役割:
    - 全出力の95点品質ループ
    - ブランドDNA違反検出
    - 法令遵守チェック
    - 過剰約束防止
    - 誤情報フィルタ
    """

    name = "guardian"
    model_tier = "strategic"

    QUALITY_THRESHOLD = 95
    MAX_RETRIES = 3

    EXCESSIVE_CLAIMS = [
        ("100%", 5),
        ("絶対", 5),
        ("必ず", 4),
        ("完全", 3),
        ("誰でも", 3),
        ("簡単に", 2),
        ("業界No.1", 5),
        ("世界一", 5),
        ("圧倒的", 2),
        ("魔法のような", 5),
        ("夢のような", 4),
    ]

    def execute(self, task: dict[str, Any]) -> AgentResult:
        """Execute Guardian task."""
        task_type = task.get("type", "evaluate")

        handlers = {
            "evaluate": self.evaluate_content,
            "quality_loop": self.run_quality_loop,
            "compliance_check": self.check_compliance,
            "brand_check": self.check_brand_compliance,
        }

        handler = handlers.get(task_type)
        if not handler:
            return AgentResult(
                success=False,
                content=None,
                error=f"Unknown task type: {task_type}",
            )

        return handler(task)

    def evaluate_content(self, task: dict[str, Any]) -> AgentResult:
        """Evaluate content quality."""
        content = task.get("content", "")
        content_type = task.get("content_type", "general")

        evaluation = self._comprehensive_evaluation(content, content_type)

        return AgentResult(
            success=True,
            content={
                "total_score": evaluation.total_score,
                "axis_scores": evaluation.axis_scores,
                "violations": [
                    {
                        "severity": v.severity,
                        "category": v.category,
                        "description": v.description,
                        "suggestion": v.suggestion,
                    }
                    for v in evaluation.violations
                ],
                "approved": evaluation.approved,
                "force_reject": evaluation.force_reject,
                "feedback": evaluation.feedback,
            },
            metadata={"type": "evaluate", "content_type": content_type},
        )

    def run_quality_loop(self, task: dict[str, Any]) -> AgentResult:
        """Run the 95-point quality loop."""
        content = task.get("content", "")
        content_type = task.get("content_type", "general")
        source_agent = task.get("source_agent", "unknown")
        refine_callback = task.get("refine_callback")

        evaluation_history = []
        current_content = content
        retry_count = 0

        while retry_count <= self.MAX_RETRIES:
            evaluation = self._comprehensive_evaluation(current_content, content_type)
            evaluation_history.append({
                "retry": retry_count,
                "score": evaluation.total_score,
                "violations": len(evaluation.violations),
            })

            if evaluation.force_reject:
                return AgentResult(
                    success=False,
                    content={
                        "status": "force_rejected",
                        "reason": "critical_violation",
                        "violations": [v.description for v in evaluation.violations if v.severity == "CRITICAL"],
                        "history": evaluation_history,
                    },
                    metadata={"type": "quality_loop", "escalate": True},
                )

            if evaluation.total_score >= self.QUALITY_THRESHOLD:
                if self._self_reflection(current_content, evaluation):
                    return AgentResult(
                        success=True,
                        content={
                            "status": "approved",
                            "final_content": current_content,
                            "final_score": evaluation.total_score,
                            "history": evaluation_history,
                        },
                        metadata={"type": "quality_loop"},
                    )

            if retry_count >= self.MAX_RETRIES:
                break

            if refine_callback:
                current_content = refine_callback(current_content, evaluation.feedback)
            else:
                break

            retry_count += 1

        return AgentResult(
            success=False,
            content={
                "status": "max_retries_exceeded",
                "final_content": current_content,
                "final_score": evaluation.total_score,
                "feedback": evaluation.feedback,
                "history": evaluation_history,
            },
            metadata={"type": "quality_loop", "escalate": True},
        )

    def check_compliance(self, task: dict[str, Any]) -> AgentResult:
        """Check legal compliance."""
        content = task.get("content", "")
        content_type = task.get("content_type", "general")

        violations = self._check_legal_compliance(content, content_type)

        critical = [v for v in violations if v.severity == "CRITICAL"]
        major = [v for v in violations if v.severity == "MAJOR"]
        minor = [v for v in violations if v.severity == "MINOR"]

        score_deduction = len(major) * 5 + len(minor) * 1

        return AgentResult(
            success=len(critical) == 0,
            content={
                "passed": len(critical) == 0 and score_deduction <= 5,
                "critical_violations": len(critical),
                "major_violations": len(major),
                "minor_violations": len(minor),
                "score_deduction": score_deduction,
                "details": [
                    {
                        "severity": v.severity,
                        "category": v.category,
                        "description": v.description,
                    }
                    for v in violations
                ],
            },
            metadata={"type": "compliance_check"},
        )

    def check_brand_compliance(self, task: dict[str, Any]) -> AgentResult:
        """Check brand DNA compliance."""
        content = task.get("content", "")

        violations = self._check_brand_dna_compliance(content)

        return AgentResult(
            success=len(violations) == 0,
            content={
                "violations": [
                    {
                        "category": v.category,
                        "description": v.description,
                        "suggestion": v.suggestion,
                    }
                    for v in violations
                ],
            },
            metadata={"type": "brand_check"},
        )

    def _comprehensive_evaluation(self, content: str, content_type: str) -> QualityEvaluation:
        """Perform comprehensive content evaluation."""
        violations = []

        brand_score = self._evaluate_brand_dna(content, violations)
        legal_score = self._evaluate_legal_compliance(content, content_type, violations)
        quality_score = self._evaluate_content_quality(content, violations)
        target_score = self._evaluate_target_fit(content, violations)
        overpromise_score = self._evaluate_overpromise(content, violations)
        hallucination_score = self._evaluate_hallucination(content, violations)

        axis_scores = {
            "brand_dna": brand_score,
            "legal": legal_score,
            "quality": quality_score,
            "target_fit": target_score,
            "overpromise": overpromise_score,
            "hallucination": hallucination_score,
        }

        total_score = sum(axis_scores.values())

        critical_violations = [v for v in violations if v.severity == "CRITICAL"]
        force_reject = len(critical_violations) > 0

        feedback = self._generate_feedback(violations, axis_scores)

        return QualityEvaluation(
            total_score=total_score,
            axis_scores=axis_scores,
            violations=violations,
            feedback=feedback,
            approved=total_score >= self.QUALITY_THRESHOLD and not force_reject,
            force_reject=force_reject,
        )

    def _evaluate_brand_dna(self, content: str, violations: list[Violation]) -> int:
        """Evaluate brand DNA compliance (25 points max)."""
        score = 25

        forbidden = self.brand_dna.get("forbidden", [])
        if isinstance(forbidden, dict):
            forbidden_words = forbidden.get("expressions", [])
        else:
            forbidden_words = forbidden

        for word in forbidden_words:
            if word in content:
                score -= 5
                violations.append(Violation(
                    severity="MAJOR",
                    category="brand_dna",
                    description=f"禁止語使用: {word}",
                    suggestion=f"「{word}」を削除または言い換えてください",
                ))

        return max(0, score)

    def _evaluate_legal_compliance(
        self, content: str, content_type: str, violations: list[Violation]
    ) -> int:
        """Evaluate legal compliance (25 points max)."""
        score = 25

        legal_violations = self._check_legal_compliance(content, content_type)
        for v in legal_violations:
            if v.severity == "CRITICAL":
                score = 0
            elif v.severity == "MAJOR":
                score -= 10
            else:
                score -= 2
            violations.append(v)

        return max(0, score)

    def _evaluate_content_quality(self, content: str, violations: list[Violation]) -> int:
        """Evaluate content quality (20 points max)."""
        score = 20

        if len(content) < 100:
            score -= 5
            violations.append(Violation(
                severity="MINOR",
                category="quality",
                description="コンテンツが短すぎます",
            ))

        return max(0, score)

    def _evaluate_target_fit(self, content: str, violations: list[Violation]) -> int:
        """Evaluate target audience fit (15 points max)."""
        score = 15
        return score

    def _evaluate_overpromise(self, content: str, violations: list[Violation]) -> int:
        """Evaluate for overpromises (10 points max)."""
        score = 10

        for expression, penalty in self.EXCESSIVE_CLAIMS:
            if expression in content:
                score -= penalty
                violations.append(Violation(
                    severity="MAJOR" if penalty >= 4 else "MINOR",
                    category="overpromise",
                    description=f"過剰約束の可能性: {expression}",
                    suggestion=f"「{expression}」を控えめな表現に変更してください",
                ))

        return max(0, score)

    def _evaluate_hallucination(self, content: str, violations: list[Violation]) -> int:
        """Evaluate for potential hallucinations (5 points max)."""
        score = 5

        stats_pattern = r'\d+%|\d+万|\d+億'
        stats = re.findall(stats_pattern, content)

        for stat in stats:
            if "出典" not in content and "参照" not in content and "調査" not in content:
                if score > 0:
                    score -= 1
                    violations.append(Violation(
                        severity="MINOR",
                        category="hallucination",
                        description=f"ソースなしの統計: {stat}",
                        suggestion="統計データにはソースを明記してください",
                    ))

        return max(0, score)

    def _check_legal_compliance(self, content: str, content_type: str) -> list[Violation]:
        """Check for legal compliance violations."""
        violations = []

        if content_type in ["email", "newsletter", "line"]:
            if "配信解除" not in content and "配信停止" not in content:
                violations.append(Violation(
                    severity="CRITICAL",
                    category="specified_email_law",
                    description="配信解除動線がありません（特定電子メール法違反）",
                    suggestion="配信解除リンクまたは手順を追加してください",
                ))

        medical_claims = ["治る", "治療", "予防効果", "医学的"]
        for claim in medical_claims:
            if claim in content:
                violations.append(Violation(
                    severity="CRITICAL",
                    category="pharma_law",
                    description=f"医療効果の訴求: {claim}（薬機法違反の可能性）",
                    suggestion="医療効果を暗示する表現を削除してください",
                ))

        return violations

    def _check_brand_dna_compliance(self, content: str) -> list[Violation]:
        """Check for brand DNA violations."""
        violations = []

        forbidden = self.brand_dna.get("forbidden", [])
        if isinstance(forbidden, dict):
            forbidden_words = forbidden.get("expressions", [])
        else:
            forbidden_words = forbidden

        for word in forbidden_words:
            if word in content:
                violations.append(Violation(
                    severity="MAJOR",
                    category="brand_dna",
                    description=f"禁止語使用: {word}",
                ))

        return violations

    def _generate_feedback(self, violations: list[Violation], axis_scores: dict[str, int]) -> str:
        """Generate specific feedback for improvement."""
        if not violations:
            return "品質基準を満たしています。"

        feedback_parts = ["【改善が必要な点】\n"]

        for v in violations:
            severity_icon = {"CRITICAL": "🔴", "MAJOR": "🟡", "MINOR": "🔵"}.get(v.severity, "")
            feedback_parts.append(f"{severity_icon} [{v.category}] {v.description}")
            if v.suggestion:
                feedback_parts.append(f"   → 提案: {v.suggestion}")

        low_scores = [
            (axis, score, max_score)
            for axis, score in axis_scores.items()
            for max_score in [{"brand_dna": 25, "legal": 25, "quality": 20, "target_fit": 15, "overpromise": 10, "hallucination": 5}.get(axis, 0)]
            if score < max_score * 0.8
        ]

        if low_scores:
            feedback_parts.append("\n【低スコアの軸】")
            for axis, score, max_score in low_scores:
                feedback_parts.append(f"- {axis}: {score}/{max_score}")

        return "\n".join(feedback_parts)

    def _self_reflection(self, content: str, evaluation: QualityEvaluation) -> bool:
        """Self-reflection: Is this really 95+ points?"""
        system_prompt = """あなたは Virtus の Guardian です。

以下のコンテンツを評価し、本当に95点以上かを再確認します。

「ぱっと見で問題ない」レベルでは不十分です。
細部まで厳しく見直し、本当に承認すべきか判断してください。

特にチェックすべき点:
- ブランドDNAと完全に一致しているか?
- 一文でも「自分らしくない」表現はないか?
- 過剰約束、誇張、煽りはないか?
- 法令違反のリスクは皆無か?

回答は "approve" または "reject" のみ。"""

        messages = [
            {
                "role": "user",
                "content": f"""このコンテンツは{evaluation.total_score}点と評価されました。
本当に95点以上ですか?

【コンテンツ】
{content[:2000]}...
""",
            }
        ]

        try:
            response = self.call_llm(system_prompt, messages, max_tokens=100)
            return "approve" in response.lower()
        except Exception as e:
            self.logger.error(f"Self-reflection failed: {e}")
            return True

    def get_system_prompt(self) -> str:
        """Get Guardian specific system prompt."""
        return f"""あなたは Virtus の Guardian（品質保証）エージェントです。

あなたの役割:
- 全出力の95点品質チェック
- ブランドDNA違反検出
- 法令遵守チェック
- 過剰約束防止
- 誤情報フィルタ

以下のブランドDNAを完全に遵守してください:

{self.format_brand_dna()}

重要な原則（神さんの教え）:
- 95点未満は絶対に通さない
- 「これで本当に95点ですか?」と自分に問い返す
- 妥協禁止
- 具体的な改善指示を出す
"""
