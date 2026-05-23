"""Drafter Agent - All content writing."""

import json
import re
from typing import Any

from .base import BaseAgent
from ..skills import SkillLoader, format_brand_dna


class Drafter(BaseAgent):
    """Drafter agent for all text content generation."""

    DEFAULT_SKILLS = ["garai-tone", "dream-writing", "impact-v2-0r"]

    TASK_OPTIMIZATION = {
        "note_article": {
            "target_length": 2500,
            "seo_priority": "high",
            "image_count": "3-5",
        },
        "x_post": {
            "target_length": 130,
            "hashtag_count": "1-3",
        },
        "instagram_carousel": {
            "slide_count": "7-10",
        },
        "outreach_email": {
            "personalization_level": "max",
        },
        "youtube_script": {
            "target_length": 1500,
        },
        "proposal": {
            "target_length": 3000,
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
            model="claude-sonnet-4-6",
            brand_dna=brand_dna,
            skills=skills or self.DEFAULT_SKILLS,
        )

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute a writing task."""
        task_type = task.get("task_type", "")
        context = task.get("context", {})

        if task_type == "note_article":
            return self.write_note_article(context)
        elif task_type == "x_post":
            return self.write_x_post(context)
        elif task_type == "outreach_email":
            return self.write_outreach_email(context)
        elif task_type == "proposal":
            return self.write_proposal(context)
        elif task_type == "instagram_carousel":
            return self.write_instagram_carousel(context)
        elif task_type == "youtube_script":
            return self.write_youtube_script(context)
        else:
            return self.write_generic(task_type, context)

    def refine(self, content: str, feedback: str, content_type: str = "generic") -> str:
        """Refine content based on Guardian feedback."""
        system = self._build_system_prompt(content_type)
        prompt = f"""以下のコンテンツを Guardian からのフィードバックに基づいて修正してください。

# 元のコンテンツ
{content}

# Guardian からのフィードバック
{feedback}

修正版のみを出力してください（説明不要）。"""

        return self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

    def write_note_article(self, context: dict[str, Any]) -> dict[str, Any]:
        """Write a note article."""
        topic = context.get("topic", "")
        target_audience = context.get("target_audience", "")
        length_target = context.get("length_target", 2500)

        system = self._build_system_prompt("note_article")
        prompt = f"""以下の条件で note 記事を執筆してください。

# トピック
{topic}

# ターゲット読者
{target_audience}

# 目標文字数
{length_target}文字

# 出力形式（JSON）
{{
  "title": "記事タイトル(60文字以内、SEO最適化)",
  "description": "メタディスクリプション(120文字以内)",
  "keywords": ["キーワード1", "キーワード2"],
  "content": "記事本文（マークダウン形式）",
  "estimated_reading_time": "5分",
  "suggested_images": [
    {{"position": "h2-1の後", "description": "画像の指示書"}}
  ]
}}

galaiworks の Garai Tone と IMPACT v2.0R フレームワークを適用してください。"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8000,
        )

        data = self._extract_json(response) or {
            "title": topic,
            "content": response,
            "description": "",
            "keywords": [],
        }

        return {
            "task_type": "note_article",
            "success": True,
            "output": data,
        }

    def write_x_post(self, context: dict[str, Any]) -> dict[str, Any]:
        """Write an X (Twitter) post."""
        topic = context.get("topic", "")
        count = context.get("count", 1)

        system = self._build_system_prompt("x_post")
        prompt = f"""以下のトピックで X 投稿を {count} 件生成してください。

# トピック
{topic}

# 出力形式（JSON配列）
[
  {{
    "text": "投稿本文(140文字以内)",
    "hashtags": ["#タグ1", "#タグ2"],
    "thread_continuation": false,
    "visual_suggestion": "画像/動画の有無、内容",
    "best_time": "投稿推奨時刻"
  }}
]

Garai Tone を適用、結論先出し、数字活用。"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        posts = self._extract_json(response) or []

        return {
            "task_type": "x_post",
            "success": bool(posts),
            "output": posts,
        }

    def write_outreach_email(self, context: dict[str, Any]) -> dict[str, Any]:
        """Write a personalized outreach email."""
        recipient = context.get("recipient", {})
        purpose = context.get("purpose", "初回アプローチ")
        sender_info = context.get("sender_info", {})

        system = self._build_system_prompt("outreach_email")
        prompt = f"""以下の宛先に個別カスタマイズの営業メールを書いてください。

# 宛先情報
{json.dumps(recipient, ensure_ascii=False, indent=2)}

# 目的
{purpose}

# 送信者情報（特定電子メール法対応に必須）
{json.dumps(sender_info, ensure_ascii=False, indent=2)}

# 出力形式（JSON）
{{
  "subject": "件名(40文字以内)",
  "body": "メール本文（送信者情報・解除動線含む）",
  "cta": {{"primary": "CTA文言", "url": "URL"}},
  "follow_up_plan": {{"day_3": "...", "day_7": "..."}}
}}

注意:
- 特定電子メール法の必須要件を満たすこと
- 解除動線をメール末尾に必須配置
- 「絶対」「必ず」等の過剰表現は使わない
- 個別カスタマイズを最大限"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        data = self._extract_json(response) or {"subject": "", "body": response}

        return {
            "task_type": "outreach_email",
            "success": True,
            "output": data,
        }

    def write_proposal(self, context: dict[str, Any]) -> dict[str, Any]:
        """Write a sales proposal."""
        customer = context.get("customer", {})
        challenge = context.get("challenge", "")
        budget = context.get("budget", "")

        system = self._build_system_prompt("proposal")
        prompt = f"""以下の商談向けに提案書を作成してください。

# 顧客情報
{json.dumps(customer, ensure_ascii=False, indent=2)}

# 顧客の課題
{challenge}

# 想定予算
{budget}

IMPACT v2.0R フレームワーク（Insight/Mechanism/Proof/Application/Conclusion/Transition）で構成。
DREAM WRITING の三層ニーズ分析を反映。

マークダウン形式で出力してください。"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8000,
        )

        return {
            "task_type": "proposal",
            "success": True,
            "output": {"content": response},
        }

    def write_instagram_carousel(self, context: dict[str, Any]) -> dict[str, Any]:
        """Write Instagram carousel content."""
        topic = context.get("topic", "")
        slide_count = context.get("slide_count", 8)

        system = self._build_system_prompt("instagram_carousel")
        prompt = f"""Instagram カルーセル投稿を {slide_count} スライドで作成してください。

# トピック
{topic}

# 出力形式（JSON）
{{
  "caption": "本文キャプション",
  "hashtags": ["#tag1", "#tag2"],
  "slides": [
    {{"slide_number": 1, "text": "スライド本文", "visual_direction": "ビジュアル指示"}}
  ]
}}

スライド1は強いフック、最終スライドはCTA。"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        data = self._extract_json(response) or {"slides": []}

        return {
            "task_type": "instagram_carousel",
            "success": True,
            "output": data,
        }

    def write_youtube_script(self, context: dict[str, Any]) -> dict[str, Any]:
        """Write YouTube video script."""
        topic = context.get("topic", "")
        duration = context.get("duration_seconds", 600)

        system = self._build_system_prompt("youtube_script")
        prompt = f"""YouTube 動画の台本を作成してください。

# トピック
{topic}

# 動画時間
{duration}秒

# 構成
- フック（最初の15秒で離脱防止）
- 本編（IMPACT v2.0R 適用）
- CTA（チャンネル登録、関連動画誘導）

マークダウン形式、各セクションにナレーション・画面表示・効果音指示を含む。"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=6000,
        )

        return {
            "task_type": "youtube_script",
            "success": True,
            "output": {"script": response},
        }

    def write_generic(
        self, task_type: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Generic writing fallback."""
        prompt_text = context.get("prompt", "")
        if not prompt_text:
            return {"task_type": task_type, "success": False, "error": "No prompt provided"}

        system = self._build_system_prompt(task_type)
        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt_text}],
        )

        return {
            "task_type": task_type,
            "success": True,
            "output": {"content": response},
        }

    def _build_system_prompt(self, content_type: str) -> str:
        """Build the system prompt for the given content type."""
        customer_name = self.brand_dna.get("identity", {}).get("name", "Customer")
        brand_dna_text = format_brand_dna(self.brand_dna)
        skills_text = SkillLoader.load_many(self.skills)
        optimization = self.TASK_OPTIMIZATION.get(content_type, {})

        return f"""あなたは Virtus の Drafter エージェントです。

# あなたの使命
顧客 {customer_name} のブランドDNAに完全に沿ったコンテンツを、
最高品質で執筆することです。

# 顧客のブランドDNA
{brand_dna_text}

# 適用するスキル(galaiworks独自IP)

{skills_text}

# このコンテンツタイプの最適化指針
{json.dumps(optimization, ensure_ascii=False, indent=2)}

# 守るべき原則

第一に、ブランドDNAの voice を完全に再現する。
顧客が自分で書いたとしか思えないレベルの一致が必須。

第二に、Garai Tone の構造を使いつつ、顧客のブランドDNAに合わせて変調する。

第三に、過剰な煽り・誇張禁止。
「絶対」「必ず」「100%」等の保証表現は使わない。

第四に、SEO 最適化(該当時)。

第五に、95 点未満の出力を Guardian に送らない。
自己レビュー後、確信が持てる出力のみ提出。"""

    def _extract_json(self, text: str) -> Any:
        """Extract JSON from LLM response."""
        for pattern in [r"```json\s*(.+?)\s*```", r"```\s*(.+?)\s*```"]:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start = text.find(start_char)
            end = text.rfind(end_char) + 1
            if start != -1 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    continue

        return None
