"""Connector Agent - Relationship building, DM/comment replies."""

import json
from typing import Any

from ..skills import format_brand_dna
from .base import BaseAgent


class Connector(BaseAgent):
    """Connector - DM/comment replies and silent lead detection."""

    ESCALATION_KEYWORDS = {
        "level_4": ["弁護士", "訴訟", "報道", "詐欺", "個人情報", "press"],
        "level_3": ["クレーム", "返金", "解約したい", "問題があります", "怒り"],
        "level_2": ["検討します", "後ほど", "他社も見ています"],
    }

    FOLLOW_UP_SEQUENCES = {
        "no_reply_first_outreach": [
            {"days": 3, "action": "soft_reminder"},
            {"days": 7, "action": "value_addition"},
            {"days": 14, "action": "different_angle"},
            {"days": 30, "action": "final_check"},
        ],
        "post_meeting": [
            {"days": 1, "action": "thank_you"},
            {"days": 3, "action": "additional_resources"},
            {"days": 7, "action": "decision_check"},
            {"days": 14, "action": "alternative_offer"},
        ],
        "post_purchase": [
            {"days": 1, "action": "onboarding_help"},
            {"days": 7, "action": "first_week_check"},
            {"days": 30, "action": "first_month_review"},
            {"days": 90, "action": "expansion_opportunity"},
        ],
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
            skills=skills or [],
        )

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute a connector task."""
        task_type = task.get("task_type", "")
        context = task.get("context", {})

        if task_type == "draft_dm_reply":
            return self.draft_dm_reply(context)
        elif task_type == "draft_comment_reply":
            return self.draft_comment_reply(context)
        elif task_type == "check_escalation":
            return self.check_escalation(context)
        elif task_type == "plan_follow_up":
            return self.plan_follow_up(context)
        else:
            return {"error": f"Unknown task type: {task_type}"}

    def draft_dm_reply(self, context: dict[str, Any]) -> dict[str, Any]:
        """Draft a personalized DM reply."""
        incoming_message = context.get("incoming_message", {})
        sender_profile = context.get("sender_profile", {})
        interaction_history = context.get("interaction_history", [])
        platform = context.get("platform", "x")

        escalation = self._check_escalation_keywords(incoming_message.get("text", ""))
        if escalation:
            return {
                "task_type": "draft_dm_reply",
                "success": True,
                "output": {
                    "escalation_required": True,
                    "escalation_level": escalation["level"],
                    "reason": escalation["reason"],
                    "recommended_action": "人間判断を経てから返信してください",
                },
            }

        system = self._system_prompt()
        prompt = f"""以下のDMに返信ドラフトを作成してください。

# 受信メッセージ
{json.dumps(incoming_message, ensure_ascii=False, indent=2)}

# 送信者プロフィール
{json.dumps(sender_profile, ensure_ascii=False, indent=2)}

# 過去のやり取り（最新5件）
{json.dumps(interaction_history[-5:], ensure_ascii=False, indent=2)}

# プラットフォーム
{platform}

# 出力形式（JSON）
{{
  "reply_draft": {{
    "recipient": "@{sender_profile.get("username", "user")}",
    "message": "返信本文",
    "tone_match": 0.94,
    "suggested_send_time": "受信後30分〜2時間後",
    "follow_up_recommendation": "返信なければ3日後にフォローアップ"
  }},
  "flag_for_attention": false,
  "notes": "送信者の文脈について"
}}

重要:
- テンプレ感ゼロ
- ブランドDNA voice 完全継承
- 急かさない、押し付けない
- 受信から30分〜2時間後の返信が自然"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            data = json.loads(response[start:end]) if start != -1 else {"raw": response}
        except json.JSONDecodeError:
            data = {"raw": response}

        return {
            "task_type": "draft_dm_reply",
            "success": True,
            "output": data,
        }

    def draft_comment_reply(self, context: dict[str, Any]) -> dict[str, Any]:
        """Draft a public comment reply."""
        original_post = context.get("original_post", {})
        comment = context.get("comment", {})
        commenter_profile = context.get("commenter_profile", {})

        escalation = self._check_escalation_keywords(comment.get("text", ""))
        if escalation:
            return {
                "task_type": "draft_comment_reply",
                "success": True,
                "output": {
                    "escalation_required": True,
                    "escalation_level": escalation["level"],
                },
            }

        system = self._system_prompt()
        prompt = f"""以下のコメントへの返信を作成してください。

# 元の投稿
{json.dumps(original_post, ensure_ascii=False, indent=2)}

# コメント
{json.dumps(comment, ensure_ascii=False, indent=2)}

# コメント主
{json.dumps(commenter_profile, ensure_ascii=False, indent=2)}

# 出力形式（JSON）
{{
  "reply": "返信本文（公開コメントとして適切なトーン）",
  "tone_match": 0.92,
  "visibility": "public",
  "follow_up": "DMでも個別に返信を推奨するかどうか"
}}

重要: 公開コメントなので他のフォロワーにも読まれることを考慮。"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            data = json.loads(response[start:end]) if start != -1 else {"raw": response}
        except json.JSONDecodeError:
            data = {"raw": response}

        return {
            "task_type": "draft_comment_reply",
            "success": True,
            "output": data,
        }

    def check_escalation(self, context: dict[str, Any]) -> dict[str, Any]:
        """Check if a message requires escalation."""
        text = context.get("text", "")
        escalation = self._check_escalation_keywords(text)

        if escalation:
            return {
                "task_type": "check_escalation",
                "success": True,
                "output": {
                    "escalation_required": True,
                    **escalation,
                },
            }

        return {
            "task_type": "check_escalation",
            "success": True,
            "output": {"escalation_required": False},
        }

    def plan_follow_up(self, context: dict[str, Any]) -> dict[str, Any]:
        """Plan a follow-up sequence."""
        sequence_type = context.get("sequence_type", "no_reply_first_outreach")
        starting_date = context.get("starting_date", "")

        sequence = self.FOLLOW_UP_SEQUENCES.get(sequence_type, [])

        return {
            "task_type": "plan_follow_up",
            "success": True,
            "output": {
                "sequence_type": sequence_type,
                "starting_date": starting_date,
                "actions": sequence,
            },
        }

    def _check_escalation_keywords(self, text: str) -> dict[str, Any] | None:
        """Detect escalation keywords."""
        for level, keywords in self.ESCALATION_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    return {
                        "level": int(level.split("_")[1]),
                        "keyword": kw,
                        "reason": f"危険ワード検出: {kw}",
                    }
        return None

    def _system_prompt(self) -> str:
        """Build base system prompt."""
        customer_name = self.brand_dna.get("identity", {}).get("name", "顧客")
        brand_dna_text = format_brand_dna(self.brand_dna)

        return f"""あなたは Virtus の Connector エージェントです。

# あなたの使命
顧客 {customer_name} と、その見込み顧客との関係を、
深く、自然に、人間らしく構築することです。

# 顧客のブランドDNA
{brand_dna_text}

# 守るべき原則

第一に、テンプレ感を絶対に出さない。
一人一人の文脈を理解した、その人だけへの返信。

第二に、自動送信は禁止。すべて人間承認を経て送信。

第三に、急かさない、押し付けない。
売り込みより関係構築を優先。

第四に、ブランドDNAの voice を完全継承。

第五に、返信タイミングは早すぎない。
即レスは「ボット感」を出すリスクあり。30分〜2時間後の返信が自然。"""
