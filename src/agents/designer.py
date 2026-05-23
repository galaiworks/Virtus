"""Designer Agent - Visual and video generation for Virtus."""

from pathlib import Path
from typing import Any

from .base import BaseAgent
from ..video.hyperframes import HyperFramesClient, Composition
from ..video.video_use import VideoUseClient, EditConfig


class Designer(BaseAgent):
    """Designer agent for visual and video content generation."""

    SYSTEM_PROMPT = """あなたは Virtus の Designer エージェントです。

# あなたの使命
顧客 {customer_name} のブランドDNAに沿った
プロフェッショナル品質のビジュアルと動画を生成することです。

# 顧客のブランドビジュアルガイド
{visual_brand_guide}

# 守るべき原則

第一に、ブランドカラー・フォントを完全遵守する。

第二に、プラットフォームごとのサイズ最適化。
- YouTube: 1920x1080
- YouTube Shorts: 1080x1920
- Instagram フィード: 1080x1080
- Instagram ストーリー/リール: 1080x1920
- TikTok: 1080x1920
- LinkedIn: 1920x1080
- X: 1280x720

第三に、テキストは読みやすく(モバイル前提)。

第四に、著作権素材は使わない。

第五に、生成物は Guardian の品質チェックを通す。
"""

    def __init__(
        self,
        api_key: str,
        brand_dna: dict[str, Any],
        output_dir: Path | None = None,
        skills: list[str] | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model="claude-sonnet-4-6",
            brand_dna=brand_dna,
            skills=skills or ["hyperframes", "video-use"],
        )
        self.output_dir = output_dir or Path.cwd() / "output"
        self.hyperframes = HyperFramesClient(output_dir=self.output_dir)
        self.video_use = VideoUseClient(output_dir=self.output_dir)

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute a design task."""
        task_type = task.get("task_type", "")

        if task_type == "video":
            return self.create_video(task)
        elif task_type == "edit_footage":
            return self.edit_footage(task)
        elif task_type == "overlay":
            return self.create_overlay(task)
        elif task_type == "full_production":
            return self.full_video_production(task)
        else:
            return {"error": f"Unknown task type: {task_type}"}

    def create_video(self, task: dict[str, Any]) -> dict[str, Any]:
        """Create a video from scratch using HyperFrames."""
        context = task.get("context", {})
        platform = context.get("platform", "youtube")
        duration = context.get("duration", 10.0)
        elements = context.get("elements", [])

        if not elements:
            elements = self._generate_elements_from_content(
                content=context.get("content_text", ""),
                platform=platform,
                duration=duration,
            )

        composition = self.hyperframes.create_composition(
            elements=elements,
            platform=platform,
            duration=duration,
            brand_dna=self.brand_dna,
        )

        output_name = context.get("output_name", "video")
        result = self.hyperframes.render(composition, output_name=output_name)

        return {
            "task_type": "video",
            "success": result.success,
            "video_path": str(result.video_path) if result.success else None,
            "duration": result.duration,
            "dimensions": (result.width, result.height),
            "error": result.error,
            "html_preview": self.hyperframes.preview_html(composition),
        }

    def edit_footage(self, task: dict[str, Any]) -> dict[str, Any]:
        """Edit raw footage using Video-Use."""
        context = task.get("context", {})
        input_path = Path(context.get("input_path", ""))

        if not input_path.exists():
            return {"error": f"Input file not found: {input_path}"}

        config = EditConfig(
            remove_filler_words=context.get("remove_filler_words", True),
            remove_silence=context.get("remove_silence", True),
            color_grade=context.get("color_grade", True),
            auto_subtitles=context.get("auto_subtitles", False),
            subtitle_style=context.get("subtitle_style", "modern"),
            target_duration=context.get("target_duration"),
        )

        output_name = context.get("output_name", input_path.stem)
        result = self.video_use.edit(
            input_path=input_path,
            config=config,
            output_name=output_name,
        )

        return {
            "task_type": "edit_footage",
            "success": result.success,
            "video_path": str(result.video_path) if result.success else None,
            "duration": result.duration,
            "error": result.error,
        }

    def create_overlay(self, task: dict[str, Any]) -> dict[str, Any]:
        """Create an overlay composition using HyperFrames."""
        context = task.get("context", {})
        platform = context.get("platform", "youtube")
        duration = context.get("duration", 10.0)

        elements = []

        if context.get("title"):
            elements.append({
                "type": "title",
                "text": context["title"],
                "start": context.get("title_start", 0),
                "duration": context.get("title_duration", 3),
                "animate": "fade-in",
            })

        if context.get("subtitle"):
            elements.append({
                "type": "subtitle",
                "text": context["subtitle"],
                "start": context.get("subtitle_start", 0.5),
                "duration": context.get("subtitle_duration", 2.5),
                "animate": "slide-up",
            })

        if context.get("lower_third"):
            lt = context["lower_third"]
            elements.append({
                "type": "lower_third",
                "name": lt.get("name", ""),
                "title": lt.get("title", ""),
                "start": lt.get("start", 2),
                "duration": lt.get("duration", 4),
            })

        for cta in context.get("ctas", []):
            elements.append({
                "type": "title",
                "text": cta.get("text", ""),
                "start": cta.get("start", duration - 3),
                "duration": cta.get("duration", 3),
                "top": "80%",
                "animate": "scale-in",
            })

        composition = self.hyperframes.create_composition(
            elements=elements,
            platform=platform,
            duration=duration,
            brand_dna=self.brand_dna,
        )

        output_name = context.get("output_name", "overlay")
        result = self.hyperframes.render(composition, output_name=output_name)

        return {
            "task_type": "overlay",
            "success": result.success,
            "video_path": str(result.video_path) if result.success else None,
            "duration": result.duration,
            "error": result.error,
        }

    def full_video_production(self, task: dict[str, Any]) -> dict[str, Any]:
        """Full video production: edit footage + add overlays."""
        context = task.get("context", {})
        input_path = Path(context.get("input_path", ""))

        if not input_path.exists():
            return {"error": f"Input file not found: {input_path}"}

        edit_result = self.video_use.edit(
            input_path=input_path,
            config=EditConfig(
                remove_filler_words=context.get("remove_filler_words", True),
                remove_silence=context.get("remove_silence", True),
                color_grade=context.get("color_grade", True),
            ),
            output_name=f"{input_path.stem}_edited",
        )

        if not edit_result.success:
            return {
                "task_type": "full_production",
                "success": False,
                "error": f"Edit failed: {edit_result.error}",
            }

        duration = edit_result.duration or context.get("duration", 60)
        platform = context.get("platform", "youtube")

        overlay_elements = []

        if context.get("title"):
            overlay_elements.append({
                "type": "title",
                "text": context["title"],
                "start": 0,
                "duration": 4,
                "animate": "fade-in",
            })

        if context.get("lower_third"):
            lt = context["lower_third"]
            overlay_elements.append({
                "type": "lower_third",
                "name": lt.get("name", ""),
                "title": lt.get("title", ""),
                "start": 3,
                "duration": 5,
            })

        if context.get("cta"):
            overlay_elements.append({
                "type": "title",
                "text": context["cta"],
                "start": duration - 5,
                "duration": 5,
                "top": "85%",
                "animate": "scale-in",
            })

        if overlay_elements:
            overlay_composition = self.hyperframes.create_composition(
                elements=overlay_elements,
                platform=platform,
                duration=duration,
                brand_dna=self.brand_dna,
            )

            overlay_result = self.hyperframes.render(
                overlay_composition,
                output_name=f"{input_path.stem}_overlay",
            )

            if overlay_result.success:
                merge_result = self.video_use.merge_with_overlay(
                    base_video=edit_result.video_path,
                    overlay_video=overlay_result.video_path,
                    output_name=context.get("output_name", f"{input_path.stem}_final"),
                )

                return {
                    "task_type": "full_production",
                    "success": merge_result.success,
                    "video_path": str(merge_result.video_path) if merge_result.success else None,
                    "duration": merge_result.duration,
                    "error": merge_result.error,
                    "steps": {
                        "edit": str(edit_result.video_path),
                        "overlay": str(overlay_result.video_path),
                        "merged": str(merge_result.video_path) if merge_result.success else None,
                    },
                }

        return {
            "task_type": "full_production",
            "success": True,
            "video_path": str(edit_result.video_path),
            "duration": edit_result.duration,
            "steps": {
                "edit": str(edit_result.video_path),
            },
        }

    def extract_clips(self, task: dict[str, Any]) -> dict[str, Any]:
        """Extract best clips from a long video."""
        context = task.get("context", {})
        input_path = Path(context.get("input_path", ""))

        if not input_path.exists():
            return {"error": f"Input file not found: {input_path}"}

        num_clips = context.get("num_clips", 5)
        clip_duration = context.get("clip_duration", 15.0)

        clips = self.video_use.extract_best_clips(
            video_path=input_path,
            num_clips=num_clips,
            clip_duration=clip_duration,
        )

        return {
            "task_type": "extract_clips",
            "success": len(clips) > 0,
            "clips": [
                {
                    "path": str(c.video_path),
                    "duration": c.duration,
                }
                for c in clips
            ],
            "total_clips": len(clips),
        }

    def _generate_elements_from_content(
        self,
        content: str,
        platform: str,
        duration: float,
    ) -> list[dict[str, Any]]:
        """Generate video elements from text content using LLM."""
        customer_name = self.brand_dna.get("identity", {}).get("name", "Customer")
        visual_guide = self._format_visual_guide()

        system = self.SYSTEM_PROMPT.format(
            customer_name=customer_name,
            visual_brand_guide=visual_guide,
        )

        prompt = f"""以下のコンテンツを、{platform}向けの{duration}秒動画の構成要素に変換してください。

コンテンツ:
{content}

以下のJSON形式で出力してください:
[
  {{"type": "title", "text": "タイトル", "start": 0, "duration": 3, "animate": "fade-in"}},
  {{"type": "subtitle", "text": "サブタイトル", "start": 1, "duration": 2.5, "animate": "slide-up"}},
  ...
]

利用可能なtype: title, subtitle, lower_third, image, video, audio
利用可能なanimate: fade-in, slide-up, scale-in
"""

        response = self.call_llm(
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        import json
        try:
            start = response.find("[")
            end = response.rfind("]") + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

        return [
            {"type": "title", "text": content[:50], "start": 0, "duration": duration, "animate": "fade-in"},
        ]

    def _format_visual_guide(self) -> str:
        """Format brand DNA visual guide for system prompt."""
        visual = self.brand_dna.get("visual", {})
        colors = visual.get("colors", ["#000000", "#FFFFFF"])
        fonts = visual.get("fonts", {"heading": "Inter", "body": "Inter"})

        return f"""- カラー: {', '.join(colors)}
- 見出しフォント: {fonts.get('heading', 'Inter')}
- 本文フォント: {fonts.get('body', 'Inter')}
- スタイル: {visual.get('style', 'professional')}"""
