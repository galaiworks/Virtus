"""Virtus Onboarding - Brand DNA construction from customer hearing."""

from dataclasses import dataclass, field
from typing import Any

from anthropic import Anthropic

from .brain import BrainLayer, BrandDNA


@dataclass
class HearingQuestion:
    """A single hearing question."""

    id: str
    category: str
    question: str
    help_text: str = ""
    required: bool = True


@dataclass
class HearingResponse:
    """Response to a hearing question."""

    question_id: str
    answer: str
    notes: str = ""


@dataclass
class HearingSession:
    """Active hearing session state."""

    customer_id: str
    responses: list[HearingResponse] = field(default_factory=list)
    current_index: int = 0
    completed: bool = False


HEARING_QUESTIONS: list[HearingQuestion] = [
    HearingQuestion(
        id="identity_1",
        category="Identity",
        question="ビジネス名は何ですか？",
        help_text="正式名称をお答えください",
    ),
    HearingQuestion(
        id="identity_2",
        category="Identity",
        question="何をしているか30秒で説明すると？",
        help_text="エレベーターピッチのように簡潔に",
    ),
    HearingQuestion(
        id="identity_3",
        category="Identity",
        question="主要顧客は誰ですか？",
        help_text="理想的な顧客像を具体的に",
    ),
    HearingQuestion(
        id="identity_4",
        category="Identity",
        question="競合は誰ですか？",
        help_text="直接競合、間接競合を含めて",
    ),
    HearingQuestion(
        id="identity_5",
        category="Identity",
        question="あなたの独自性は何ですか？",
        help_text="競合と比較しての差別化ポイント",
    ),
    HearingQuestion(
        id="voice_1",
        category="Voice",
        question="普段の話し方は丁寧/カジュアル/混合のどれですか？",
        help_text="コンテンツでのトーンを決める参考に",
    ),
    HearingQuestion(
        id="voice_2",
        category="Voice",
        question="好む言葉、口癖は何ですか？",
        help_text="よく使うフレーズを3-5個",
    ),
    HearingQuestion(
        id="voice_3",
        category="Voice",
        question="絶対使わない言葉は何ですか？",
        help_text="ブランドイメージに合わない表現",
    ),
    HearingQuestion(
        id="voice_4",
        category="Voice",
        question="自分の発信を一言で表すと？",
        help_text="キャッチフレーズ的なもの",
    ),
    HearingQuestion(
        id="voice_5",
        category="Voice",
        question="親近感を出すフレーズは？",
        help_text="読者との距離を縮める表現",
    ),
    HearingQuestion(
        id="voice_6",
        category="Voice",
        question="プロフェッショナル感を出すフレーズは？",
        help_text="専門性をアピールする表現",
    ),
    HearingQuestion(
        id="voice_7",
        category="Voice",
        question="過去の自分の発信で「これは自分らしい」と感じたものは？",
        help_text="URLやテキストを共有してください",
    ),
    HearingQuestion(
        id="voice_8",
        category="Voice",
        question="過去の自分の発信で「これは自分らしくない」と感じたものは？",
        help_text="NGパターンの参考に",
    ),
    HearingQuestion(
        id="strategy_1",
        category="Content Strategy",
        question="主要トピック3つは何ですか？",
        help_text="メインで発信したいテーマ",
    ),
    HearingQuestion(
        id="strategy_2",
        category="Content Strategy",
        question="副次トピック3つは何ですか？",
        help_text="サブで扱いたいテーマ",
    ),
    HearingQuestion(
        id="strategy_3",
        category="Content Strategy",
        question="メインプラットフォームは？",
        help_text="note、X、YouTube、LinkedIn、Instagram等",
    ),
    HearingQuestion(
        id="strategy_4",
        category="Content Strategy",
        question="投稿頻度は？",
        help_text="プラットフォームごとの理想頻度",
    ),
    HearingQuestion(
        id="strategy_5",
        category="Content Strategy",
        question="過去にバズった/反応が良かった投稿は？",
        help_text="成功パターンの分析用",
    ),
    HearingQuestion(
        id="strategy_6",
        category="Content Strategy",
        question="過去に反応が悪かった投稿は？",
        help_text="避けるべきパターンの参考に",
    ),
    HearingQuestion(
        id="strategy_7",
        category="Content Strategy",
        question="競合の中で「これは真似したい」発信は？",
        help_text="参考にしたいスタイル",
    ),
    HearingQuestion(
        id="audience_1",
        category="Target Audience",
        question="想定読者の年齢層は？",
        help_text="メインターゲットの年代",
    ),
    HearingQuestion(
        id="audience_2",
        category="Target Audience",
        question="想定読者の業界・職種は？",
        help_text="具体的な職業や業界",
    ),
    HearingQuestion(
        id="audience_3",
        category="Target Audience",
        question="想定読者の年商規模は？",
        help_text="個人〜大企業のどのあたりか",
    ),
    HearingQuestion(
        id="audience_4",
        category="Target Audience",
        question="想定読者が抱える典型的な悩み3つは？",
        help_text="解決したい課題",
    ),
    HearingQuestion(
        id="audience_5",
        category="Target Audience",
        question="想定読者の行動パターン（どんな媒体を見るか）は？",
        help_text="情報収集の習慣",
    ),
    HearingQuestion(
        id="forbidden_1",
        category="Forbidden",
        question="扱いたくないトピックは？",
        help_text="避けるべき話題",
    ),
    HearingQuestion(
        id="forbidden_2",
        category="Forbidden",
        question="言いたくない表現は？",
        help_text="使用禁止のフレーズ",
    ),
    HearingQuestion(
        id="forbidden_3",
        category="Forbidden",
        question="競合との関わり方は？",
        help_text="言及可否、比較の方針等",
    ),
    HearingQuestion(
        id="goal_1",
        category="Goal",
        question="6ヶ月後の理想は？",
        help_text="短期目標",
    ),
    HearingQuestion(
        id="goal_2",
        category="Goal",
        question="1年後の理想は？",
        help_text="中期目標",
    ),
]


class OnboardingFlow:
    """Manages the customer onboarding process."""

    def __init__(
        self,
        api_key: str,
        brain: BrainLayer | None = None,
    ) -> None:
        self.client = Anthropic(api_key=api_key)
        self.brain = brain or BrainLayer()
        self.questions = HEARING_QUESTIONS
        self.sessions: dict[str, HearingSession] = {}

    def start_session(self, customer_id: str) -> HearingSession:
        """Start a new hearing session."""
        session = HearingSession(customer_id=customer_id)
        self.sessions[customer_id] = session
        return session

    def get_session(self, customer_id: str) -> HearingSession | None:
        """Get existing session."""
        return self.sessions.get(customer_id)

    def get_current_question(self, customer_id: str) -> HearingQuestion | None:
        """Get the current question for a session."""
        session = self.get_session(customer_id)
        if not session or session.completed:
            return None
        if session.current_index >= len(self.questions):
            return None
        return self.questions[session.current_index]

    def submit_answer(
        self,
        customer_id: str,
        answer: str,
        notes: str = "",
    ) -> dict[str, Any]:
        """Submit an answer to the current question."""
        session = self.get_session(customer_id)
        if not session:
            return {"error": "No active session"}

        current_question = self.get_current_question(customer_id)
        if not current_question:
            return {"error": "No more questions"}

        response = HearingResponse(
            question_id=current_question.id,
            answer=answer,
            notes=notes,
        )
        session.responses.append(response)
        session.current_index += 1

        if session.current_index >= len(self.questions):
            session.completed = True
            return {
                "status": "completed",
                "message": "ヒアリング完了。ブランドDNAを生成します。",
            }

        next_question = self.get_current_question(customer_id)
        return {
            "status": "continue",
            "progress": f"{session.current_index}/{len(self.questions)}",
            "next_question": {
                "id": next_question.id,
                "category": next_question.category,
                "question": next_question.question,
                "help_text": next_question.help_text,
            }
            if next_question
            else None,
        }

    def get_progress(self, customer_id: str) -> dict[str, Any]:
        """Get session progress."""
        session = self.get_session(customer_id)
        if not session:
            return {"error": "No active session"}

        return {
            "current": session.current_index,
            "total": len(self.questions),
            "completed": session.completed,
            "percentage": int((session.current_index / len(self.questions)) * 100),
        }

    def generate_brand_dna(self, customer_id: str) -> BrandDNA | None:
        """Generate brand DNA from hearing responses using LLM."""
        session = self.get_session(customer_id)
        if not session or not session.completed:
            return None

        responses_text = self._format_responses(session.responses)

        prompt = f"""以下のヒアリング回答から、ブランドDNAを生成してください。

## ヒアリング回答
{responses_text}

## 出力形式
以下のYAML形式で出力してください:

```yaml
identity:
  name: "ビジネス名"
  business: "事業内容"
  primary_target_audience: "主要ターゲット"
  secondary_target_audience: "副次ターゲット"
  unique_value_proposition: "独自価値提案"
  core_competencies:
    - "強み1"
    - "強み2"

voice:
  tone: "トーン説明"
  personality:
    - "特徴1"
    - "特徴2"
  preferred_phrases:
    - "好みフレーズ1"
    - "好みフレーズ2"
  avoid_phrases:
    - "避けるフレーズ1"
  signature_phrases:
    - "シグネチャーフレーズ1"

content_strategy:
  pillar_topics:
    - "主要トピック1"
    - "主要トピック2"
  secondary_topics:
    - "副次トピック1"
  primary_platforms:
    - "platform1"
  publishing_frequency:
    platform1: "頻度"

forbidden:
  topics:
    - "禁止トピック1"
  expressions:
    - "禁止表現1"
  practices:
    - "禁止行為1"

reference:
  past_winning_content: []
  competitor_examples: []
  inspiration_sources: []

goals:
  short_term: "6ヶ月目標"
  mid_term: "1年目標"
```

回答に基づいて具体的な値を埋めてください。
"""

        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        yaml_content = self._extract_yaml(response.content[0].text)
        brand_dna = self._parse_brand_dna(yaml_content)

        if brand_dna:
            self.brain.save_brand_dna(customer_id, brand_dna)

        return brand_dna

    def _format_responses(self, responses: list[HearingResponse]) -> str:
        """Format responses for LLM prompt."""
        lines = []
        for resp in responses:
            question = next((q for q in self.questions if q.id == resp.question_id), None)
            if question:
                lines.append(f"### {question.category}: {question.question}")
                lines.append(f"回答: {resp.answer}")
                if resp.notes:
                    lines.append(f"補足: {resp.notes}")
                lines.append("")
        return "\n".join(lines)

    def _extract_yaml(self, text: str) -> str:
        """Extract YAML content from LLM response."""
        if "```yaml" in text:
            start = text.find("```yaml") + 7
            end = text.find("```", start)
            return text[start:end].strip()
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            return text[start:end].strip()
        return text.strip()

    def _parse_brand_dna(self, yaml_content: str) -> BrandDNA | None:
        """Parse YAML content into BrandDNA."""
        import yaml

        try:
            data = yaml.safe_load(yaml_content)
            if not data:
                return None
            return BrandDNA.from_dict(data)
        except Exception:
            return None


def analyze_past_content(
    api_key: str,
    content_samples: list[str],
) -> dict[str, Any]:
    """Analyze past content to extract voice characteristics.

    This supplements the hearing process by analyzing actual writing samples.
    """
    client = Anthropic(api_key=api_key)

    samples_text = "\n\n---\n\n".join(content_samples[:5])

    prompt = f"""以下のコンテンツサンプルを分析し、書き手の特徴を抽出してください。

## サンプル
{samples_text}

## 分析項目
1. トーン（フォーマル度、親近感、専門性）
2. よく使うフレーズ・表現パターン
3. 文章の構造（導入、展開、結論のパターン）
4. 特徴的な言い回し
5. 避けている表現

JSON形式で出力してください:
```json
{{
  "tone_analysis": {{
    "formality": 0.0-1.0,
    "warmth": 0.0-1.0,
    "expertise": 0.0-1.0
  }},
  "common_phrases": ["phrase1", "phrase2"],
  "structure_patterns": ["pattern1"],
  "unique_expressions": ["expression1"],
  "avoided_expressions": ["avoided1"]
}}
```
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    import json

    text = response.content[0].text
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        json_str = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        json_str = text[start:end].strip()
    else:
        json_str = text.strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return {"error": "Failed to parse analysis"}
