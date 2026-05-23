"""Drafter - 全コンテンツ執筆."""

from __future__ import annotations

from typing import Any

from .base import AgentResult, BaseAgent


class Drafter(BaseAgent):
    """
    Drafter エージェント (Sonnet 4.6)

    役割:
    - note記事、ブログ
    - X投稿、Instagram、LinkedIn投稿
    - メルマガ、LINE配信
    - YouTube台本
    - 営業メール、提案書、商談シナリオ
    - LP文章、ステップメール、ホワイトペーパー
    """

    name = "drafter"
    model_tier = "execution"

    def execute(self, task: dict[str, Any]) -> AgentResult:
        """Execute Drafter task."""
        task_type = task.get("type", "note_article")

        handlers = {
            "note_article": self.write_note_article,
            "x_post": self.write_x_post,
            "x_thread": self.write_x_thread,
            "instagram_post": self.write_instagram_post,
            "linkedin_post": self.write_linkedin_post,
            "newsletter": self.write_newsletter,
            "youtube_script": self.write_youtube_script,
            "outreach_email": self.write_outreach_email,
            "proposal": self.write_proposal,
            "dm_reply": self.write_dm_reply,
        }

        handler = handlers.get(task_type)
        if not handler:
            return AgentResult(
                success=False,
                content=None,
                error=f"Unknown task type: {task_type}",
            )

        return handler(task)

    def write_note_article(self, task: dict[str, Any]) -> AgentResult:
        """Write note article with SEO optimization."""
        topic = task.get("topic", "")
        keywords = task.get("keywords", [])
        research = task.get("research", "")

        system_prompt = f"""{self.get_system_prompt()}

あなたはnote記事を執筆します。

【使用するフレームワーク】
IMPACT v2.0R:
- Insight: 読者の気づきを促す導入
- Mechanism: なぜそうなるかのメカニズム
- Proof: 証拠・事例
- Application: 実践方法
- Conclusion: まとめ
- Transition: 次のアクションへの誘導

【SEO要件】
- キーワードを自然に含める
- 見出し（##, ###）を適切に使用
- 読みやすい段落分け

【文字数】
2000-4000文字
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のテーマでnote記事を執筆してください。

【テーマ】
{topic}

【SEOキーワード】
{', '.join(keywords) if keywords else '指定なし'}

【リサーチ情報】
{research if research else 'なし'}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "note_article", "topic": topic, "keywords": keywords},
            )
        except Exception as e:
            self.logger.error(f"Note article writing failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def write_x_post(self, task: dict[str, Any]) -> AgentResult:
        """Write single X (Twitter) post."""
        topic = task.get("topic", "")
        style = task.get("style", "insight")

        system_prompt = f"""{self.get_system_prompt()}

あなたはX（Twitter）投稿を作成します。

【投稿スタイル】
- insight: 気づきを与える
- tip: 実用的なヒント
- story: ストーリー形式
- question: 問いかけ

【制約】
- 280文字以内
- 改行を効果的に使用
- エンゲージメントを意識
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のテーマでX投稿を作成してください。

【テーマ】
{topic}

【スタイル】
{style}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "x_post", "topic": topic, "style": style},
            )
        except Exception as e:
            self.logger.error(f"X post writing failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def write_x_thread(self, task: dict[str, Any]) -> AgentResult:
        """Write X thread (multiple connected posts)."""
        topic = task.get("topic", "")
        num_posts = task.get("num_posts", 5)

        system_prompt = f"""{self.get_system_prompt()}

あなたはXスレッド（連続投稿）を作成します。

【構成】
1. フック（興味を引く導入）
2. 本論（{num_posts - 2}ツイート）
3. まとめ + CTA

【制約】
- 各ツイート280文字以内
- スレッド全体で価値を提供
- 最後に保存・RTを促す
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のテーマで{num_posts}連投のスレッドを作成してください。

【テーマ】
{topic}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "x_thread", "topic": topic, "num_posts": num_posts},
            )
        except Exception as e:
            self.logger.error(f"X thread writing failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def write_instagram_post(self, task: dict[str, Any]) -> AgentResult:
        """Write Instagram post caption."""
        topic = task.get("topic", "")
        post_type = task.get("post_type", "carousel")

        system_prompt = f"""{self.get_system_prompt()}

あなたはInstagram投稿のキャプションを作成します。

【投稿タイプ】
- carousel: カルーセル（複数画像）
- reel: リール（短尺動画）
- single: 単一画像

【構成】
1. フック（1行目で興味を引く）
2. 本文（価値提供）
3. CTA（保存・フォロー促進）
4. ハッシュタグ（10-15個）
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のテーマでInstagram投稿キャプションを作成してください。

【テーマ】
{topic}

【投稿タイプ】
{post_type}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "instagram_post", "topic": topic},
            )
        except Exception as e:
            self.logger.error(f"Instagram post writing failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def write_linkedin_post(self, task: dict[str, Any]) -> AgentResult:
        """Write LinkedIn post."""
        topic = task.get("topic", "")

        system_prompt = f"""{self.get_system_prompt()}

あなたはLinkedIn投稿を作成します。

【トーン】
- プロフェッショナル
- 洞察を共有
- 議論を促す

【構成】
1. フック（最初の2行で引き込む）
2. ストーリーまたは洞察
3. 学びのポイント
4. 問いかけ（エンゲージメント促進）
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のテーマでLinkedIn投稿を作成してください。

【テーマ】
{topic}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "linkedin_post", "topic": topic},
            )
        except Exception as e:
            self.logger.error(f"LinkedIn post writing failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def write_newsletter(self, task: dict[str, Any]) -> AgentResult:
        """Write newsletter/email content."""
        topic = task.get("topic", "")
        newsletter_type = task.get("newsletter_type", "weekly")

        system_prompt = f"""{self.get_system_prompt()}

あなたはメルマガ/LINE配信を作成します。

【DREAM WRITINGフレームワーク】
- Desire: 欲求を刺激
- Reality: 現状の課題
- Evidence: 証拠・事例
- Action: 具体的アクション
- Motivation: 動機付け

【必須要素】
- 配信解除リンクの案内
- 送信者情報
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のテーマでメルマガを作成してください。

【テーマ】
{topic}

【配信タイプ】
{newsletter_type}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "newsletter", "topic": topic},
            )
        except Exception as e:
            self.logger.error(f"Newsletter writing failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def write_youtube_script(self, task: dict[str, Any]) -> AgentResult:
        """Write YouTube video script."""
        topic = task.get("topic", "")
        duration = task.get("duration", 10)

        system_prompt = f"""{self.get_system_prompt()}

あなたはYouTube台本を作成します。

【構成】
1. フック（最初の10秒で引き込む）
2. 本編（価値提供）
3. まとめ
4. CTA（チャンネル登録、関連動画）

【タイムライン】
{duration}分の動画として構成してください。
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のテーマで{duration}分のYouTube台本を作成してください。

【テーマ】
{topic}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "youtube_script", "topic": topic, "duration": duration},
            )
        except Exception as e:
            self.logger.error(f"YouTube script writing failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def write_outreach_email(self, task: dict[str, Any]) -> AgentResult:
        """Write personalized outreach email."""
        prospect = task.get("prospect", {})
        research = task.get("research", "")

        system_prompt = f"""{self.get_system_prompt()}

あなたは営業メール（初回アプローチ）を作成します。

【重要】
- 個別カスタマイズ（テンプレ感排除）
- 相手の課題に言及
- 押し売り禁止
- 価値提供優先

【構成】
1. パーソナライズされた導入
2. 共感ポイント
3. 提供できる価値
4. 軽いCTA（返信を促す）

【法令遵守】
- 送信者情報を含める
- 配信解除方法を記載
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下の見込み客への営業メールを作成してください。

【見込み客情報】
会社名: {prospect.get('company_name', '不明')}
決済権者: {prospect.get('decision_maker', '不明')}
役職: {prospect.get('title', '不明')}

【リサーチ情報】
{research if research else 'なし'}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "outreach_email", "prospect": prospect},
            )
        except Exception as e:
            self.logger.error(f"Outreach email writing failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def write_proposal(self, task: dict[str, Any]) -> AgentResult:
        """Write business proposal."""
        client = task.get("client", {})
        service = task.get("service", "")
        research = task.get("research", "")

        system_prompt = f"""{self.get_system_prompt()}

あなたは提案書ドラフトを作成します。

【構成】
1. エグゼクティブサマリー
2. 課題の整理
3. 提案内容
4. 期待される成果
5. 実施スケジュール
6. 投資金額
7. 次のステップ

【重要】
- 過剰約束禁止
- 具体的な数字を含める
- 顧客の言葉で課題を表現
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下の情報で提案書を作成してください。

【クライアント情報】
会社名: {client.get('company_name', '不明')}
担当者: {client.get('contact_person', '不明')}
業界: {client.get('industry', '不明')}

【提案サービス】
{service if service else '情報なし'}

【リサーチ情報】
{research if research else 'なし'}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "proposal", "client": client},
            )
        except Exception as e:
            self.logger.error(f"Proposal writing failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def write_dm_reply(self, task: dict[str, Any]) -> AgentResult:
        """Write DM reply draft."""
        incoming_message = task.get("incoming_message", "")
        context = task.get("context", "")
        platform = task.get("platform", "X")

        system_prompt = f"""{self.get_system_prompt()}

あなたはDM返信ドラフトを作成します。

【重要】
- 相手のメッセージに適切に応答
- ブランドの声を維持
- 自然な会話トーン
- 押し売り禁止
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のDMへの返信を作成してください。

【プラットフォーム】
{platform}

【受信メッセージ】
{incoming_message}

【過去のやり取り】
{context if context else 'なし'}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "dm_reply", "platform": platform},
            )
        except Exception as e:
            self.logger.error(f"DM reply writing failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def refine(self, content: str, feedback: str) -> str:
        """Refine content based on Guardian feedback."""
        system_prompt = f"""{self.get_system_prompt()}

あなたはGuardianからのフィードバックをもとにコンテンツを改善します。

【重要】
- フィードバックの指摘を全て反映
- ブランドDNAを維持
- 品質95点以上を目指す
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のコンテンツをフィードバックに基づいて改善してください。

【元のコンテンツ】
{content}

【Guardianからのフィードバック】
{feedback}
""",
            }
        ]

        return self.call_llm(system_prompt, messages)

    def get_system_prompt(self) -> str:
        """Get Drafter specific system prompt."""
        return f"""あなたは Virtus の Drafter（全コンテンツ執筆）エージェントです。

あなたの役割:
- note記事、SNS投稿、メルマガ
- 営業メール、提案書
- すべてのテキストコンテンツ生成

以下のブランドDNAを完全に遵守してください:

{self.format_brand_dna()}

使用するスキル:
- Garai Tone: galaiworks執筆スタイル
- DREAM WRITING: 読者を行動に導くフレームワーク
- IMPACT v2.0R: 6セクション構造

重要な原則:
- 顧客の声で書く
- 過剰約束禁止
- SEO最適化（note記事）
- 法令遵守
"""
