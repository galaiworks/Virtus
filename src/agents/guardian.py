"""Guardian Agent - 95-point quality loop and compliance check."""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..skills import format_brand_dna
from .base import BaseAgent


@dataclass
class Violation:
    """A detected violation."""

    severity: str
    category: str
    description: str
    location: str = ""
    fix_suggestion: str = ""


@dataclass
class Evaluation:
    """An evaluation result."""

    total_score: int
    verdict: str
    axis_scores: dict[str, dict[str, Any]] = field(default_factory=dict)
    violations: list[Violation] = field(default_factory=list)
    feedback: str = ""
    raw_response: str = ""

    @property
    def force_reject(self) -> bool:
        """True if a critical violation requires immediate rejection."""
        return any(v.severity == "CRITICAL" for v in self.violations)

    @property
    def all_issues(self) -> list[str]:
        """Aggregate all issues across axes."""
        return [v.description for v in self.violations]


class Guardian(BaseAgent):
    """Guardian - quality assurance through 95-point loop."""

    THRESHOLD = 95
    MAX_RETRIES = 3

    EXCESSIVE_CLAIMS = [
        "100%",
        "絶対",
        "必ず",
        "完全",
        "誰でも稼げる",
        "業界No.1",
        "業界トップ",
        "世界最高",
        "日本一",
        "魔法のような",
        "夢のような",
    ]

    EVALUATION_WEIGHTS = {
        "outreach_email": {
            "brand_dna": 20,
            "legal_compliance": 35,
            "content_quality": 15,
            "target_fit": 10,
            "overpromise": 15,
            "hallucination": 5,
        },
        "note_article": {
            "brand_dna": 30,
            "legal_compliance": 15,
            "content_quality": 25,
            "target_fit": 15,
            "overpromise": 10,
            "hallucination": 5,
        },
        "x_post": {
            "brand_dna": 35,
            "legal_compliance": 20,
            "content_quality": 15,
            "target_fit": 15,
            "overpromise": 10,
            "hallucination": 5,
        },
        "default": {
            "brand_dna": 25,
            "legal_compliance": 25,
            "content_quality": 20,
            "target_fit": 15,
            "overpromise": 10,
            "hallucination": 5,
        },
    }

    def __init__(
        self,
        api_key: str,
        brand_dna: dict[str, Any],
        skills: list[str] | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model="claude-opus-4-7",
            brand_dna=brand_dna,
            skills=skills or [],
        )

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute a guardian evaluation."""
        task_type = task.get("task_type", "evaluate")
        context = task.get("context", {})

        if task_type == "evaluate":
            evaluation = self.evaluate(
                content=context.get("content", ""),
                content_type=context.get("content_type", "default"),
            )
            return self._evaluation_to_dict(evaluation)
        elif task_type == "evaluate_with_loop":
            return self.evaluate_with_loop(
                content=context.get("content", ""),
                content_type=context.get("content_type", "default"),
                agent_name=context.get("agent_name", "Drafter"),
                revise_fn=context.get("revise_fn"),
            )
        else:
            return {"error": f"Unknown task type: {task_type}"}

    def evaluate(self, content: str, content_type: str = "default") -> Evaluation:
        """Evaluate content against the 100-point matrix."""
        violations = self._check_legal_compliance(content, content_type)
        critical = [v for v in violations if v.severity == "CRITICAL"]

        if critical:
            return Evaluation(
                total_score=0,
                verdict="CRITICAL_VIOLATION",
                violations=critical,
                feedback="重大な法令違反を検出しました。配信停止。",
            )

        overpromise_violations = self._check_overpromise(content)
        violations.extend(overpromise_violations)

        evaluation = self._llm_evaluate(content, content_type, violations)
        evaluation.violations.extend(violations)

        return evaluation

    def evaluate_with_loop(
        self,
        content: str,
        content_type: str,
        agent_name: str,
        revise_fn: Callable[[str, str], str] | None = None,
    ) -> dict[str, Any]:
        """Run the 95-point quality loop."""
        retry_count = 0
        current_content = content
        history: list[Evaluation] = []

        while retry_count <= self.MAX_RETRIES:
            evaluation = self.evaluate(current_content, content_type)
            history.append(evaluation)

            if evaluation.force_reject:
                return {
                    "status": "escalated",
                    "reason": "critical_violation",
                    "content": current_content,
                    "evaluation": self._evaluation_to_dict(evaluation),
                    "history": [self._evaluation_to_dict(e) for e in history],
                }

            if evaluation.total_score >= self.THRESHOLD:
                if self._self_reflection(current_content, evaluation):
                    return {
                        "status": "approved",
                        "content": current_content,
                        "evaluation": self._evaluation_to_dict(evaluation),
                        "retry_count": retry_count,
                    }
                evaluation.feedback = "自己反省により再評価を要請: " + evaluation.feedback

            if revise_fn is None:
                return {
                    "status": "needs_revision",
                    "content": current_content,
                    "evaluation": self._evaluation_to_dict(evaluation),
                    "retry_count": retry_count,
                }

            current_content = revise_fn(current_content, evaluation.feedback)
            retry_count += 1

        final = history[-1] if history else None
        return {
            "status": "escalated",
            "reason": "max_retries_exceeded",
            "content": current_content,
            "evaluation": self._evaluation_to_dict(final) if final else None,
            "history": [self._evaluation_to_dict(e) for e in history],
        }

    def _check_legal_compliance(self, content: str, content_type: str) -> list[Violation]:
        """Check legal compliance."""
        violations = []

        if content_type in ("outreach_email", "newsletter", "line_broadcast"):
            if not self._has_unsubscribe_link(content):
                violations.append(
                    Violation(
                        severity="CRITICAL",
                        category="specified_email_law",
                        description="解除動線がない（特定電子メール法違反）",
                        fix_suggestion="メール末尾に解除リンクを追加してください",
                    )
                )
            if not self._has_sender_info(content):
                violations.append(
                    Violation(
                        severity="CRITICAL",
                        category="specified_email_law",
                        description="送信者情報がない（特定電子メール法違反）",
                        fix_suggestion="送信者氏名・住所・問合せ先を明記してください",
                    )
                )

        return violations

    def _check_overpromise(self, content: str) -> list[Violation]:
        """Check for excessive claims."""
        violations = []
        for claim in self.EXCESSIVE_CLAIMS:
            if claim in content:
                violations.append(
                    Violation(
                        severity="MAJOR",
                        category="overpromise",
                        description=f"過剰約束表現: {claim}",
                        fix_suggestion=f"「{claim}」を控えめな表現に変更",
                    )
                )
        return violations

    def _has_unsubscribe_link(self, content: str) -> bool:
        """Check if content has an unsubscribe link."""
        patterns = ["配信停止", "解除", "unsubscribe", "オプトアウト", "退会"]
        return any(p in content.lower() or p in content for p in patterns)

    def _has_sender_info(self, content: str) -> bool:
        """Check if content has sender information."""
        return bool(re.search(r"(送信者|発行者|問合せ|連絡先|住所)", content))

    def _llm_evaluate(
        self,
        content: str,
        content_type: str,
        existing_violations: list[Violation],
    ) -> Evaluation:
        """Use LLM to evaluate content quality."""
        brand_dna_text = format_brand_dna(self.brand_dna)
        weights = self.EVALUATION_WEIGHTS.get(content_type, self.EVALUATION_WEIGHTS["default"])

        system = f"""あなたは Virtus の Guardian エージェントです。

# 神さんの教えを実装する
「逃げるな、95点に大丈夫?と聞き返せ」

あなたは妥協を許してはいけません。
「これで本当に95点ですか?」と常に問い続けてください。

# 顧客のブランドDNA
{brand_dna_text}

# 評価軸（100点満点・このコンテンツタイプの重み）
{json.dumps(weights, ensure_ascii=False, indent=2)}

# 既に検出された違反
{json.dumps([{"severity": v.severity, "category": v.category, "desc": v.description} for v in existing_violations], ensure_ascii=False, indent=2)}

# 重要原則
第一に、95点未満は絶対に APPROVED しない。
第二に、軽微違反でも累積で配点を下げる。「ぱっと見問題ない」では不十分。
第三に、改善指示は具体的に。「全体的にもう少し」ではなく「第3段落の語尾を○○に」。"""

        prompt = f"""以下のコンテンツを評価してください。

# コンテンツタイプ
{content_type}

# コンテンツ
{content}

# 出力形式（JSON）
{{
  "total_score": 87,
  "verdict": "APPROVED|REJECTED|CRITICAL_VIOLATION",
  "axis_scores": {{
    "brand_dna": {{"score": 22, "max": 25, "issues": ["..."]}},
    "legal_compliance": {{"score": 24, "max": 25, "issues": []}},
    "content_quality": {{"score": 18, "max": 20, "issues": ["..."]}},
    "target_fit": {{"score": 13, "max": 15, "issues": []}},
    "overpromise": {{"score": 10, "max": 10, "issues": []}},
    "hallucination": {{"score": 5, "max": 5, "issues": []}}
  }},
  "violations": [
    {{"severity": "MAJOR", "category": "...", "description": "...", "location": "...", "fix_suggestion": "..."}}
  ],
  "feedback_to_agent": "具体的な改善指示"
}}"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
        )

        return self._parse_evaluation(response)

    def _parse_evaluation(self, response: str) -> Evaluation:
        """Parse LLM response into Evaluation."""
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            data = json.loads(response[start:end]) if start != -1 else {}
        except json.JSONDecodeError:
            return Evaluation(
                total_score=0,
                verdict="REJECTED",
                feedback="評価レスポンスの解析失敗",
                raw_response=response,
            )

        violations = [
            Violation(
                severity=v.get("severity", "MINOR"),
                category=v.get("category", ""),
                description=v.get("description", ""),
                location=v.get("location", ""),
                fix_suggestion=v.get("fix_suggestion", ""),
            )
            for v in data.get("violations", [])
        ]

        return Evaluation(
            total_score=data.get("total_score", 0),
            verdict=data.get("verdict", "REJECTED"),
            axis_scores=data.get("axis_scores", {}),
            violations=violations,
            feedback=data.get("feedback_to_agent", ""),
            raw_response=response,
        )

    def _self_reflection(self, content: str, evaluation: Evaluation) -> bool:
        """Self-reflection - ask 'is this really 95?'"""
        if evaluation.total_score < self.THRESHOLD + 2:
            prompt = f"""このコンテンツを {evaluation.total_score}/100 点と評価しました。

本当に 95 点以上ですか?「ぱっと見で問題ない」レベルでは不十分です。
細部まで厳しく見直してください。

特にチェックすべき点:
- ブランドDNA完全一致か
- 一文でも「自分らしくない」表現はないか
- 過剰約束、誇張、煽りはないか
- 法令違反のリスクは皆無か
- 読者の心を本当に動かすか

# コンテンツ
{content}

# 評価
{json.dumps(evaluation.axis_scores, ensure_ascii=False, indent=2)}

判断（"approve" または "reject"）と理由を1行で答えてください。
"""
            response = self.call_llm(
                system="あなたは厳しい品質審査官です。",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
            )
            return "approve" in response.lower()

        return True

    def _evaluation_to_dict(self, evaluation: Evaluation | None) -> dict[str, Any]:
        """Convert Evaluation to serializable dict."""
        if evaluation is None:
            return {}
        return {
            "total_score": evaluation.total_score,
            "verdict": evaluation.verdict,
            "axis_scores": evaluation.axis_scores,
            "violations": [
                {
                    "severity": v.severity,
                    "category": v.category,
                    "description": v.description,
                    "location": v.location,
                    "fix_suggestion": v.fix_suggestion,
                }
                for v in evaluation.violations
            ],
            "feedback": evaluation.feedback,
        }
