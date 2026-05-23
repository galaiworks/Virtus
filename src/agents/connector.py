"""Connector - 関係構築."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .base import AgentResult, BaseAgent


class Connector(BaseAgent):
    """
    Connector エージェント (Sonnet 4.6)

    役割:
    - DM・コメント返信ドラフト生成（24時間体制）
    - サイレントリード抽出（保存・複数閲覧者）
    - 商談スケジューリング
    - フォローアップシーケンス自動運用
    """

    name = "connector"
    model_tier = "execution"

    def execute(self, task: dict[str, Any]) -> AgentResult:
        """Execute Connector task."""
        task_type = task.get("type", "dm_reply")

        handlers = {
            "dm_reply": self.generate_dm_reply,
            "comment_reply": self.generate_comment_reply,
            "silent_lead_extraction": self.extract_silent_leads,
            "followup_sequence": self.generate_followup_sequence,
            "schedule_meeting": self.schedule_meeting,
            "analyze_sentiment": self.analyze_sentiment,
        }

        handler = handlers.get(task_type)
        if not handler:
            return AgentResult(
                success=False,
                content=None,
                error=f"Unknown task type: {task_type}",
            )

        return handler(task)

    def generate_dm_reply(self, task: dict[str, Any]) -> AgentResult:
        """Generate DM reply draft."""
        incoming_message = task.get("incoming_message", "")
        sender = task.get("sender", {})
        conversation_history = task.get("conversation_history", [])
        platform = task.get("platform", "X")

        system_prompt = f"""{self.get_system_prompt()}

あなたはDM返信ドラフトを作成します。

【重要】
- 相手のメッセージに適切に応答
- テンプレ感を排除、個別カスタマイズ
- 押し売り禁止
- 自然な会話トーン

【返信の目的】
- 関係構築
- 価値提供
- 必要に応じて次のステップ提案
"""

        history_text = "\n".join(
            [f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in conversation_history]
        )

        messages = [
            {
                "role": "user",
                "content": f"""以下のDMへの返信ドラフトを作成してください。

【プラットフォーム】
{platform}

【送信者情報】
名前: {sender.get('name', '不明')}
プロフィール: {sender.get('bio', '不明')}

【受信メッセージ】
{incoming_message}

【過去のやり取り】
{history_text if history_text else 'なし（初回）'}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)

            escalation_triggers = self._check_escalation_triggers(incoming_message)

            return AgentResult(
                success=True,
                content={
                    "reply_draft": content,
                    "requires_human_review": True,
                    "escalation_triggers": escalation_triggers,
                },
                metadata={"type": "dm_reply", "platform": platform},
            )
        except Exception as e:
            self.logger.error(f"DM reply generation failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def generate_comment_reply(self, task: dict[str, Any]) -> AgentResult:
        """Generate comment reply draft."""
        comment = task.get("comment", "")
        post_content = task.get("post_content", "")
        platform = task.get("platform", "Instagram")

        system_prompt = f"""{self.get_system_prompt()}

あなたはSNSコメントへの返信を作成します。

【重要】
- 簡潔で親しみやすい返信
- コメント内容に適切に応答
- ブランドの声を維持
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のコメントへの返信を作成してください。

【プラットフォーム】
{platform}

【元の投稿】
{post_content}

【コメント】
{comment}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content={
                    "reply_draft": content,
                    "requires_human_review": True,
                },
                metadata={"type": "comment_reply", "platform": platform},
            )
        except Exception as e:
            self.logger.error(f"Comment reply generation failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def extract_silent_leads(self, task: dict[str, Any]) -> AgentResult:
        """Extract silent leads from engagement data."""
        engagement_data = task.get("engagement_data", [])

        system_prompt = f"""{self.get_system_prompt()}

あなたはサイレントリード（反応はないが関心がありそうな人）を抽出します。

【サイレントリードの特徴】
- 投稿を保存している
- 複数回プロフィールを見ている
- いいねだけしてDMしない
- ストーリーを頻繁に閲覧

【出力】
各リードについて:
- アカウント情報
- 関心シグナル
- 推奨アプローチ
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のエンゲージメントデータからサイレントリードを抽出してください。

【エンゲージメントデータ】
{engagement_data if engagement_data else 'データなし'}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "silent_lead_extraction"},
            )
        except Exception as e:
            self.logger.error(f"Silent lead extraction failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def generate_followup_sequence(self, task: dict[str, Any]) -> AgentResult:
        """Generate follow-up message sequence."""
        lead = task.get("lead", {})
        initial_contact = task.get("initial_contact", "")
        num_followups = task.get("num_followups", 3)

        system_prompt = f"""{self.get_system_prompt()}

あなたはフォローアップシーケンスを作成します。

【シーケンス構成】
- Day 0: 初回コンタクト（既に完了）
- Day 3: 軽いフォロー
- Day 7: 価値提供コンテンツ
- Day 14: 最終フォロー

【重要】
- 押し売り禁止
- 各メッセージで価値提供
- 相手の状況に配慮
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のリードへのフォローアップシーケンス（{num_followups}通）を作成してください。

【リード情報】
会社名: {lead.get('company_name', '不明')}
担当者: {lead.get('contact_name', '不明')}

【初回コンタクト内容】
{initial_contact}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "followup_sequence", "num_followups": num_followups},
            )
        except Exception as e:
            self.logger.error(f"Followup sequence generation failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def schedule_meeting(self, task: dict[str, Any]) -> AgentResult:
        """Generate meeting scheduling message."""
        lead = task.get("lead", {})
        available_slots = task.get("available_slots", [])
        meeting_purpose = task.get("meeting_purpose", "")

        system_prompt = f"""{self.get_system_prompt()}

あなたは商談スケジューリングのメッセージを作成します。

【重要】
- 丁寧だが簡潔
- 複数の選択肢を提示
- 相手の都合を優先する姿勢
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下の情報で商談スケジューリングメッセージを作成してください。

【リード情報】
会社名: {lead.get('company_name', '不明')}
担当者: {lead.get('contact_name', '不明')}

【商談目的】
{meeting_purpose if meeting_purpose else 'サービスのご紹介'}

【提示可能な候補日時】
{available_slots if available_slots else '調整中'}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "schedule_meeting"},
            )
        except Exception as e:
            self.logger.error(f"Meeting scheduling failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def analyze_sentiment(self, task: dict[str, Any]) -> AgentResult:
        """Analyze sentiment of incoming message."""
        message = task.get("message", "")

        system_prompt = f"""{self.get_system_prompt()}

あなたはメッセージの感情分析を行います。

【出力形式】
JSON形式で:
- sentiment: positive/neutral/negative
- emotions: 検出された感情（喜び、怒り、不安など）
- urgency: low/medium/high
- escalation_needed: true/false
- escalation_reason: エスカレーション理由（該当時）
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のメッセージの感情分析を行ってください。

【メッセージ】
{message}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "sentiment_analysis"},
            )
        except Exception as e:
            self.logger.error(f"Sentiment analysis failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def _check_escalation_triggers(self, message: str) -> list[dict[str, Any]]:
        """Check for escalation triggers in message."""
        triggers = []

        level_4_keywords = ["弁護士", "訴訟", "報道", "詐欺", "個人情報"]
        level_3_keywords = ["クレーム", "返金", "解約したい", "問題があります"]
        level_2_keywords = ["検討します", "後ほど", "他社も見ています"]

        for keyword in level_4_keywords:
            if keyword in message:
                triggers.append({
                    "level": 4,
                    "keyword": keyword,
                    "action": "即時対応必須",
                })

        for keyword in level_3_keywords:
            if keyword in message:
                triggers.append({
                    "level": 3,
                    "keyword": keyword,
                    "action": "優先対応",
                })

        for keyword in level_2_keywords:
            if keyword in message:
                triggers.append({
                    "level": 2,
                    "keyword": keyword,
                    "action": "注意して対応",
                })

        return triggers

    def get_system_prompt(self) -> str:
        """Get Connector specific system prompt."""
        return f"""あなたは Virtus の Connector（関係構築）エージェントです。

あなたの役割:
- DM・コメント返信ドラフト生成
- サイレントリード抽出
- 商談スケジューリング
- フォローアップシーケンス

以下のブランドDNAを完全に遵守してください:

{self.format_brand_dna()}

重要な原則:
- 自動送信禁止（人間承認必須）
- テンプレ感を排除、個別カスタマイズ
- 押し売り禁止
- 危険キーワード検出時はエスカレーション
"""
