"""Designer - ビジュアル生成."""

from __future__ import annotations

from typing import Any

from .base import AgentResult, BaseAgent


class Designer(BaseAgent):
    """
    Designer エージェント (Sonnet 4.6)

    役割:
    - サムネイル生成
    - 図解生成（Nano Banana連携）
    - カルーセル画像生成
    - OGP画像生成
    - 提案書ビジュアル化
    """

    name = "designer"
    model_tier = "execution"

    def execute(self, task: dict[str, Any]) -> AgentResult:
        """Execute Designer task."""
        task_type = task.get("type", "thumbnail")

        handlers = {
            "thumbnail": self.create_thumbnail_spec,
            "infographic": self.create_infographic_spec,
            "carousel": self.create_carousel_spec,
            "ogp": self.create_ogp_spec,
            "proposal_visual": self.create_proposal_visual_spec,
        }

        handler = handlers.get(task_type)
        if not handler:
            return AgentResult(
                success=False,
                content=None,
                error=f"Unknown task type: {task_type}",
            )

        return handler(task)

    def create_thumbnail_spec(self, task: dict[str, Any]) -> AgentResult:
        """Create thumbnail specification for note/blog."""
        title = task.get("title", "")
        platform = task.get("platform", "note")

        brand_colors = self.brand_dna.get("visual", {}).get("colors", {})
        primary_color = brand_colors.get("primary", "#1a1a1a")
        accent_color = brand_colors.get("accent", "#0066cc")

        system_prompt = f"""{self.get_system_prompt()}

あなたはサムネイル画像の仕様書を作成します。

【出力形式】
JSON形式で以下を出力:
- headline: メインコピー（15文字以内）
- subheadline: サブコピー（任意）
- layout: レイアウト指定
- colors: 使用する色
- image_suggestions: 使用する画像・イラストの提案
- text_position: テキストの配置
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のコンテンツのサムネイル仕様を作成してください。

【タイトル】
{title}

【プラットフォーム】
{platform}

【ブランドカラー】
メイン: {primary_color}
アクセント: {accent_color}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "thumbnail", "platform": platform},
            )
        except Exception as e:
            self.logger.error(f"Thumbnail spec creation failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def create_infographic_spec(self, task: dict[str, Any]) -> AgentResult:
        """Create infographic specification."""
        topic = task.get("topic", "")
        data_points = task.get("data_points", [])

        system_prompt = f"""{self.get_system_prompt()}

あなたは図解（インフォグラフィック）の仕様書を作成します。

【出力形式】
- title: 図解タイトル
- structure: 図解の構造（フロー/比較/階層/etc）
- sections: 各セクションの内容
- visual_elements: 使用するアイコン・イラスト
- color_scheme: 配色
- layout_notes: レイアウト指示
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のテーマで図解仕様を作成してください。

【テーマ】
{topic}

【データポイント】
{data_points if data_points else 'なし'}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "infographic", "topic": topic},
            )
        except Exception as e:
            self.logger.error(f"Infographic spec creation failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def create_carousel_spec(self, task: dict[str, Any]) -> AgentResult:
        """Create Instagram carousel specification."""
        topic = task.get("topic", "")
        num_slides = task.get("num_slides", 5)

        system_prompt = f"""{self.get_system_prompt()}

あなたはInstagramカルーセルの仕様書を作成します。

【出力形式】
各スライドについて:
- slide_number: スライド番号
- headline: メインテキスト
- body: 本文（あれば）
- visual: ビジュアル要素
- cta: CTA（最終スライドのみ）
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のテーマで{num_slides}枚のカルーセル仕様を作成してください。

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
                metadata={"type": "carousel", "num_slides": num_slides},
            )
        except Exception as e:
            self.logger.error(f"Carousel spec creation failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def create_ogp_spec(self, task: dict[str, Any]) -> AgentResult:
        """Create OGP image specification."""
        title = task.get("title", "")
        description = task.get("description", "")

        system_prompt = f"""{self.get_system_prompt()}

あなたはOGP画像の仕様書を作成します。

【OGP要件】
- サイズ: 1200x630px
- テキストは大きく読みやすく
- ブランドロゴを含める

【出力形式】
- headline: メインコピー
- layout: レイアウト
- background: 背景
- branding: ブランド要素
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下のコンテンツのOGP画像仕様を作成してください。

【タイトル】
{title}

【説明】
{description}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "ogp"},
            )
        except Exception as e:
            self.logger.error(f"OGP spec creation failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def create_proposal_visual_spec(self, task: dict[str, Any]) -> AgentResult:
        """Create proposal visual specification."""
        proposal_content = task.get("proposal_content", "")
        client = task.get("client", {})

        system_prompt = f"""{self.get_system_prompt()}

あなたは提案書のビジュアル仕様を作成します。

【出力形式】
各ページについて:
- page_number: ページ番号
- title: ページタイトル
- content_summary: 内容要約
- visual_elements: 図表・グラフ・アイコン
- layout: レイアウト指示
"""

        messages = [
            {
                "role": "user",
                "content": f"""以下の提案書のビジュアル仕様を作成してください。

【クライアント】
{client.get('company_name', '不明')}

【提案書内容】
{proposal_content}
""",
            }
        ]

        try:
            content = self.call_llm(system_prompt, messages)
            return AgentResult(
                success=True,
                content=content,
                metadata={"type": "proposal_visual", "client": client},
            )
        except Exception as e:
            self.logger.error(f"Proposal visual spec creation failed: {e}")
            return AgentResult(success=False, content=None, error=str(e))

    def get_system_prompt(self) -> str:
        """Get Designer specific system prompt."""
        return f"""あなたは Virtus の Designer（ビジュアル生成）エージェントです。

あなたの役割:
- サムネイル・OGP画像仕様作成
- 図解・インフォグラフィック仕様作成
- カルーセル画像仕様作成
- 提案書ビジュアル化

以下のブランドDNAを完全に遵守してください:

{self.format_brand_dna()}

重要な原則:
- ブランドカラー・フォントを統一
- 視認性を重視
- 情報を整理して伝える
"""
