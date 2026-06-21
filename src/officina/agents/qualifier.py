"""Qualifier — ステージ 3:返信トリアージ・一次対応(Virtus: Connector)。

合格ゲート:分類信頼度しきい値・曖昧時は人間エスカレーション。
escalation.md の危険ワードを検出したら即エスカレーション。
"""

from __future__ import annotations

from typing import Any

from src.agents.base import AgentResult, BaseAgent

#: escalation.md 由来の危険ワード -> エスカレーションレベル。
DANGER_WORDS: dict[str, int] = {
    "弁護士": 4,
    "訴訟": 4,
    "詐欺": 4,
    "個人情報": 4,
    "クレーム": 3,
    "返金": 3,
    "解約": 3,
}

POSITIVE = ["興味", "話を聞き", "資料", "詳しく", "ミーティング", "打ち合わせ"]
NEGATIVE = ["不要", "興味ありません", "結構です", "送らないで"]


class Qualifier(BaseAgent):
    name = "qualifier"

    def execute(self, task: dict[str, Any]) -> AgentResult:
        text = task.get("reply_text", "")
        intent = "neutral"
        confidence = 0.5
        escalation_level = 0

        for word, level in DANGER_WORDS.items():
            if word in text:
                escalation_level = max(escalation_level, level)

        if any(p in text for p in POSITIVE):
            intent, confidence = "interested", 0.9
        elif any(n in text for n in NEGATIVE):
            intent, confidence = "not_interested", 0.85

        return AgentResult(
            agent=self.name,
            content_type="classification",
            output={
                "intent": intent,
                "content": text,
                "gate": {
                    "confidence": confidence,
                    "escalation_level": escalation_level,
                },
            },
            meta={"stage": 3},
        )
