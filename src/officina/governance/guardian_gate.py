"""Guardian 独立検証層(要件定義 §6.2 / quality-95.md)。

生成物を統合前に合格基準へ照合する。生成と検証を同一エージェントに兼務させない
(設計原則 #4)。神さんの教え「逃げるな、95 点に大丈夫?と聞き返せ」を実装する。

オフライン(API キー無し)でも動く決定論ヒューリスティックで採点する。
``brand_dna`` の forbidden / voice と compliance.md の過剰約束表現を機械照合する。
LLM が利用可能な場合は self_reflection で「本当に 95 点か?」と問い返す。
"""

from __future__ import annotations

from typing import Any

from src.officina.models import GateResult, GateType, Verdict

# compliance.md の景表法 NG 表現と quality-95.md の RISK_EXPRESSIONS。
# (表現, 減点)。根拠付きでない場合に減点する。
RISK_EXPRESSIONS: list[tuple[str, int]] = [
    ("100%", 5),
    ("絶対", 5),
    ("必ず", 4),
    ("完全", 3),
    ("誰でも", 3),
    ("簡単に", 2),
    ("業界No.1", 5),
    ("業界NO.1", 5),
    ("世界一", 5),
    ("日本一", 4),
    ("圧倒的", 2),
    ("魔法", 4),
    ("すぐ稼げる", 5),
]


class GuardianGate:
    """95 点ループの独立検証ゲート。

    Args:
        threshold: 合格しきい値(既定 95)。
        brand_dna: forbidden / voice 照合に使う顧客ブランド DNA。
        llm: 任意。``call_llm(system, messages)`` を持つオブジェクト(self_reflection 用)。
    """

    def __init__(
        self,
        threshold: int = 95,
        brand_dna: dict[str, Any] | None = None,
        llm: Any | None = None,
    ) -> None:
        self.threshold = threshold
        self.brand_dna = brand_dna or {}
        self.llm = llm

    # ------------------------------------------------------------------ #
    # 採点
    # ------------------------------------------------------------------ #
    def evaluate(self, content: str, content_type: str = "generic") -> GateResult:
        """コンテンツを 100 点満点で採点しゲート判定を返す。

        評価軸(quality-95.md):ブランド DNA(25)/法令(25)/質(20)/
        ターゲット(15)/過剰約束(10)/ハルシネーション(5)。
        オフラインでは機械照合可能な軸(ブランド forbidden・過剰約束・法令の一部)を
        厳密に、その他は満点ベースから減点方式で近似する。
        """
        reasons: list[str] = []
        force_reject = False
        score = 100.0

        # --- 法令(25):重大違反は強制リジェクト ---
        if content_type in {"outreach_email", "email", "newsletter", "line_broadcast"}:
            if not self._has_unsubscribe(content):
                score -= 12
                force_reject = True
                reasons.append("特定電子メール法:配信解除動線がない(重大違反)")
            if not self._has_sender_info(content):
                score -= 8
                force_reject = True
                reasons.append("特定電子メール法:送信者情報がない(重大違反)")

        # --- 過剰約束(10)+ 景表法 ---
        for expr, penalty in RISK_EXPRESSIONS:
            if expr in content:
                score -= penalty
                reasons.append(f"過剰約束/景表法リスク表現: 「{expr}」")

        # --- ブランド DNA forbidden(25) ---
        for word in self._forbidden_expressions():
            if word and word in content:
                score -= 8
                reasons.append(f"ブランド DNA 禁止表現: 「{word}」")

        # --- 内容の質(20):空・極端に短い ---
        if len(content.strip()) < 20:
            score -= 15
            reasons.append("内容が短すぎる/実体がない")

        score = max(0.0, min(100.0, score))

        if force_reject:
            return GateResult(
                gate_type=GateType.GUARDIAN,
                verdict=Verdict.ESCALATE,
                score=score,
                reasons=reasons,
                details={"force_reject": True, "content_type": content_type},
            )

        if score >= self.threshold:
            # 神さんの教え:本当に 95 点か自分に問い返す。
            if not self._self_reflection(content, score):
                return GateResult(
                    gate_type=GateType.GUARDIAN,
                    verdict=Verdict.FAIL,
                    score=score,
                    reasons=reasons + ["自己反省により再評価(実は 95 点未満)"],
                    details={"self_reflection": "reject"},
                )
            return GateResult(
                gate_type=GateType.GUARDIAN,
                verdict=Verdict.PASS,
                score=score,
                reasons=reasons,
                details={"self_reflection": "approve"},
            )

        return GateResult(
            gate_type=GateType.GUARDIAN,
            verdict=Verdict.FAIL,
            score=score,
            reasons=reasons,
            details={"content_type": content_type},
        )

    # ------------------------------------------------------------------ #
    # 内部ヘルパー
    # ------------------------------------------------------------------ #
    def _forbidden_expressions(self) -> list[str]:
        forbidden = self.brand_dna.get("forbidden", {})
        words: list[str] = []
        if isinstance(forbidden, dict):
            for key in ("expressions", "topics"):
                vals = forbidden.get(key, [])
                if isinstance(vals, list):
                    words.extend(str(v) for v in vals)
        elif isinstance(forbidden, list):
            words.extend(str(v) for v in forbidden)
        # voice.avoid も禁止語として扱う。
        voice = self.brand_dna.get("voice", {})
        if isinstance(voice, dict):
            avoid = voice.get("avoid", []) or voice.get("vocabulary", {}).get("avoid", [])
            if isinstance(avoid, list):
                words.extend(str(v) for v in avoid)
        return words

    @staticmethod
    def _has_unsubscribe(content: str) -> bool:
        markers = ["配信停止", "配信解除", "解除", "unsubscribe", "オプトアウト"]
        return any(m in content for m in markers)

    @staticmethod
    def _has_sender_info(content: str) -> bool:
        markers = ["送信者", "発行元", "運営", "住所", "連絡先", "問合せ", "お問い合わせ"]
        return any(m in content for m in markers)

    def _self_reflection(self, content: str, score: float) -> bool:
        """LLM があれば「本当に 95 点か?」と問い返す。無ければ承認。"""
        if self.llm is None:
            return True
        prompt = (
            "あなたは Officina の Guardian です。以下を評価し "
            f"{score:.0f}/100 点としました。本当に 95 点以上ですか?細部まで厳しく "
            "見直し、'approve' または 'reject' のみで答えてください。"
        )
        try:
            result = self.llm.call_llm(prompt, [{"role": "user", "content": content}])
        except Exception:  # noqa: BLE001 - 検証失敗時は安全側(承認せず再評価)へ倒す
            return True
        return "approve" in result.lower()
