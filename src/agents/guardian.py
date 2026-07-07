"""Guardian - 95 点品質ループによる全出力チェック."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from src.agents.base import BaseAgent
from src.brand_dna import forbidden_expressions

THRESHOLD = 95
MAX_RETRIES = 3

# ルールベースで即時 CRITICAL にするのは文脈に依らず違反確実な表現のみ。
# 「完全」「圧倒的」等の文脈依存表現は LLM の過剰約束軸 (減点方式) に委ねる。
EXCESSIVE_CLAIMS_PATTERN = re.compile(
    r"100\s*[%％]"
    r"|１００\s*[%％]"
    r"|絶対"
    r"|必ず(?!しも)"
    r"|誰でも(?:簡単に)?稼げる"
    r"|業界\s*No\.?\s*1"
    r"|業界ナンバーワン"
    r"|世界一"
    r"|世界最高"
    r"|日本一"
    r"|魔法のよう"
)

EVALUATION_SYSTEM = """あなたは Virtus の Guardian です。
神さんの教え「逃げるな、95 点に大丈夫?と聞き返せ」を実装する評価者です。

以下の 6 軸でコンテンツを採点してください。配点合計 100 点。

| 軸 | 配点 |
|----|------|
| ブランド DNA 遵守 | 25 |
| 法令遵守 | 25 |
| 内容の質 | 20 |
| ターゲット適合 | 15 |
| 過剰約束チェック | 10 |
| ハルシネーション検出 | 5 |

# ブランド DNA
{brand_dna}

# 禁止表現
{forbidden}

# 出力形式 (厳密に JSON のみを返してください)

```json
{{
  "brand_dna": {{"score": 0-25, "issues": ["..."]}},
  "legal": {{"score": 0-25, "issues": ["..."]}},
  "quality": {{"score": 0-20, "issues": ["..."]}},
  "target_fit": {{"score": 0-15, "issues": ["..."]}},
  "overpromise": {{"score": 0-10, "issues": ["..."]}},
  "hallucination": {{"score": 0-5, "issues": ["..."]}},
  "total": 0-100,
  "verdict": "APPROVED" or "REJECTED" or "CRITICAL_VIOLATION",
  "self_reflection_passed": true or false,
  "feedback": "改善のための具体的指示"
}}
```

self_reflection_passed は神さんの教えに従い、95 点以上の場合に
「本当に 95 点ですか?」と自問した結果。微塵でも疑念があれば false。
"""


@dataclass
class GuardianVerdict:
    """Guardian の評価結果."""

    total_score: int
    verdict: str  # "APPROVED" | "REJECTED" | "CRITICAL_VIOLATION"
    axis_scores: dict[str, int] = field(default_factory=dict)
    issues: dict[str, list[str]] = field(default_factory=dict)
    self_reflection_passed: bool = False
    feedback: str = ""
    retry_count: int = 0

    @property
    def force_reject(self) -> bool:
        """重大違反による強制リジェクト."""
        return self.verdict == "CRITICAL_VIOLATION"

    @property
    def approved(self) -> bool:
        """承認されたか (閾値超え + 自己反省通過)."""
        return (
            self.total_score >= THRESHOLD
            and self.self_reflection_passed
            and not self.force_reject
        )


class Guardian(BaseAgent):
    """品質保証エージェント.

    95 点ループ + 自己反省 + 重大違反検出.
    """

    SUPPORTED_TASKS = frozenset({"evaluate"})

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """評価タスクを実行."""
        task_type = task.get("task_type")
        if task_type not in self.SUPPORTED_TASKS:
            raise ValueError(f"Guardian は task_type={task_type} をサポートしていません")
        verdict = self.evaluate(
            content=task["content"],
            content_type=task.get("content_type", "general"),
        )
        return {
            "task_type": "evaluate",
            "verdict": verdict.verdict,
            "total_score": verdict.total_score,
            "approved": verdict.approved,
            "feedback": verdict.feedback,
            "axis_scores": verdict.axis_scores,
            "issues": verdict.issues,
        }

    def evaluate(self, content: str, content_type: str = "general") -> GuardianVerdict:
        """6 軸 + 自己反省で評価.

        Args:
            content: 評価対象のテキスト.
            content_type: コンテンツ種別 (将来のルール分岐用).

        Returns:
            GuardianVerdict.
        """
        # 1. ルールベースの即時違反検出 (LLM 呼ぶ前のショートサーキット)
        immediate_violations = self._rule_based_check(content)
        if immediate_violations:
            return GuardianVerdict(
                total_score=0,
                verdict="CRITICAL_VIOLATION",
                issues={"rule_based": immediate_violations},
                feedback="ルールベース検出による即時リジェクト: "
                + ", ".join(immediate_violations),
                self_reflection_passed=False,
            )

        # 2. LLM による 6 軸評価 (出力破損時は 1 回だけ再評価)
        system = EVALUATION_SYSTEM.format(
            brand_dna=self.brand_dna_block(),
            forbidden=", ".join(forbidden_expressions(self.brand_dna)) or "(なし)",
        )
        messages = [
            {
                "role": "user",
                "content": (
                    f"以下のコンテンツ (種別: {content_type}) を評価し、"
                    f"指定 JSON 形式のみで返してください。\n\n"
                    f"---\n{content}\n---"
                ),
            }
        ]
        raw = self.call_llm(system=system, messages=messages)
        try:
            parsed = self._parse_json(raw)
        except (ValueError, json.JSONDecodeError):
            raw = self.call_llm(system=system, messages=messages)
            parsed = self._parse_json(raw)
        return self._verdict_from_parsed(parsed)

    @staticmethod
    def _rule_based_check(content: str) -> list[str]:
        """ルールベースで重大表現を検出."""
        hits: list[str] = []
        for match in EXCESSIVE_CLAIMS_PATTERN.finditer(content):
            hits.append(f"過剰約束検出: '{match.group(0).strip()}'")
        return hits

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        """LLM の出力から JSON ブロックを抽出してパース."""
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError(f"Guardian の LLM 出力に JSON が見つかりません: {raw[:200]}")
        return json.loads(match.group(0))

    @staticmethod
    def _verdict_from_parsed(parsed: dict[str, Any]) -> GuardianVerdict:
        """パース済み辞書から GuardianVerdict を構築."""
        axis_keys = (
            "brand_dna",
            "legal",
            "quality",
            "target_fit",
            "overpromise",
            "hallucination",
        )
        axis_scores: dict[str, int] = {}
        issues: dict[str, list[str]] = {}
        for key in axis_keys:
            axis = parsed.get(key, {})
            axis_scores[key] = int(axis.get("score", 0))
            issues[key] = list(axis.get("issues", []))

        total = int(parsed.get("total", sum(axis_scores.values())))
        verdict = str(parsed.get("verdict", "REJECTED"))
        return GuardianVerdict(
            total_score=total,
            verdict=verdict,
            axis_scores=axis_scores,
            issues=issues,
            self_reflection_passed=bool(parsed.get("self_reflection_passed", False)),
            feedback=str(parsed.get("feedback", "")),
        )
