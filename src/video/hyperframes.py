"""HyperFrames integration for Virtus video generation."""

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Composition:
    """HyperFrames composition data."""

    html: str
    width: int = 1920
    height: int = 1080
    fps: int = 30
    duration: float = 10.0


@dataclass
class RenderResult:
    """Result of a HyperFrames render operation."""

    video_path: Path
    duration: float
    width: int
    height: int
    success: bool
    error: str | None = None


class HyperFramesClient:
    """Client for HyperFrames video generation."""

    PLATFORM_DIMENSIONS = {
        "youtube": (1920, 1080),
        "youtube_shorts": (1080, 1920),
        "instagram_feed": (1080, 1080),
        "instagram_story": (1080, 1920),
        "instagram_reel": (1080, 1920),
        "tiktok": (1080, 1920),
        "linkedin": (1920, 1080),
        "x_video": (1280, 720),
    }

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or Path.cwd() / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_composition(
        self,
        elements: list[dict[str, Any]],
        platform: str = "youtube",
        duration: float = 10.0,
        brand_dna: dict[str, Any] | None = None,
    ) -> Composition:
        """Create a HyperFrames composition from elements."""
        width, height = self.PLATFORM_DIMENSIONS.get(platform, (1920, 1080))

        colors = ["#000000", "#FFFFFF"]
        fonts = {"heading": "Inter", "body": "Inter"}
        if brand_dna:
            visual = brand_dna.get("visual", {})
            colors = visual.get("colors", colors)
            fonts = visual.get("fonts", fonts)

        html = self._generate_html(
            elements=elements,
            width=width,
            height=height,
            duration=duration,
            colors=colors,
            fonts=fonts,
        )

        return Composition(
            html=html,
            width=width,
            height=height,
            duration=duration,
        )

    def _generate_html(
        self,
        elements: list[dict[str, Any]],
        width: int,
        height: int,
        duration: float,
        colors: list[str],
        fonts: dict[str, str],
    ) -> str:
        """Generate HyperFrames HTML composition."""
        primary_color = colors[0] if colors else "#000000"
        secondary_color = colors[1] if len(colors) > 1 else "#FFFFFF"
        heading_font = fonts.get("heading", "Inter")
        body_font = fonts.get("body", "Inter")

        elements_html = []
        for elem in elements:
            elem_html = self._element_to_html(elem)
            if elem_html:
                elements_html.append(elem_html)

        return f'''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    @import url('https://fonts.googleapis.com/css2?family={heading_font.replace(" ", "+")}:wght@400;700&family={body_font.replace(" ", "+")}:wght@400;700&display=swap');

    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    :root {{
      --primary: {primary_color};
      --secondary: {secondary_color};
      --font-heading: '{heading_font}', sans-serif;
      --font-body: '{body_font}', sans-serif;
    }}

    #stage {{
      width: {width}px;
      height: {height}px;
      background: var(--primary);
      position: relative;
      overflow: hidden;
    }}

    .title {{
      font-family: var(--font-heading);
      color: var(--secondary);
      font-size: 72px;
      font-weight: 700;
      text-align: center;
      position: absolute;
    }}

    .subtitle {{
      font-family: var(--font-body);
      color: var(--secondary);
      font-size: 36px;
      text-align: center;
      position: absolute;
    }}

    .lower-third {{
      position: absolute;
      bottom: 80px;
      left: 60px;
      background: var(--secondary);
      padding: 20px 40px;
      font-family: var(--font-body);
      color: var(--primary);
    }}
  </style>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
</head>
<body>
  <div id="stage"
       data-composition-id="virtus-video"
       data-start="0"
       data-width="{width}"
       data-height="{height}">

{chr(10).join(elements_html)}

  </div>

  <script>
    const tl = gsap.timeline({{ paused: true }});
    window.__hfGsap = {{ tl }};

    // Register animations
    document.querySelectorAll('[data-animate]').forEach(el => {{
      const animType = el.dataset.animate;
      const start = parseFloat(el.dataset.start) || 0;
      const duration = parseFloat(el.dataset.animDuration) || 1;

      if (animType === 'fade-in') {{
        gsap.set(el, {{ opacity: 0 }});
        tl.to(el, {{ opacity: 1, duration }}, start);
      }} else if (animType === 'slide-up') {{
        gsap.set(el, {{ y: 100, opacity: 0 }});
        tl.to(el, {{ y: 0, opacity: 1, duration, ease: 'power2.out' }}, start);
      }} else if (animType === 'scale-in') {{
        gsap.set(el, {{ scale: 0, opacity: 0 }});
        tl.to(el, {{ scale: 1, opacity: 1, duration, ease: 'back.out(1.7)' }}, start);
      }}
    }});
  </script>
</body>
</html>'''

    def _element_to_html(self, elem: dict[str, Any]) -> str:
        """Convert an element dict to HTML."""
        elem_type = elem.get("type", "text")
        start = elem.get("start", 0)
        duration = elem.get("duration", 5)
        animate = elem.get("animate", "fade-in")
        anim_duration = elem.get("anim_duration", 0.5)

        if elem_type == "title":
            text = elem.get("text", "")
            top = elem.get("top", "40%")
            left = elem.get("left", "50%")
            transform = elem.get("transform", "translate(-50%, -50%)")
            return f'''    <div class="title"
         data-start="{start}"
         data-duration="{duration}"
         data-animate="{animate}"
         data-anim-duration="{anim_duration}"
         style="top: {top}; left: {left}; transform: {transform};">
      {text}
    </div>'''

        elif elem_type == "subtitle":
            text = elem.get("text", "")
            top = elem.get("top", "55%")
            left = elem.get("left", "50%")
            transform = elem.get("transform", "translate(-50%, -50%)")
            return f'''    <div class="subtitle"
         data-start="{start}"
         data-duration="{duration}"
         data-animate="{animate}"
         data-anim-duration="{anim_duration}"
         style="top: {top}; left: {left}; transform: {transform};">
      {text}
    </div>'''

        elif elem_type == "lower_third":
            name = elem.get("name", "")
            title = elem.get("title", "")
            return f'''    <div class="lower-third"
         data-start="{start}"
         data-duration="{duration}"
         data-animate="slide-up"
         data-anim-duration="{anim_duration}">
      <div style="font-weight: 700; font-size: 24px;">{name}</div>
      <div style="font-size: 18px; opacity: 0.8;">{title}</div>
    </div>'''

        elif elem_type == "video":
            src = elem.get("src", "")
            track = elem.get("track_index", 0)
            return f'''    <video
         data-start="{start}"
         data-duration="{duration}"
         data-track-index="{track}"
         src="{src}"
         muted
         playsinline
         style="width: 100%; height: 100%; object-fit: cover;">
    </video>'''

        elif elem_type == "image":
            src = elem.get("src", "")
            style = elem.get("style", "")
            return f'''    <img
         data-start="{start}"
         data-duration="{duration}"
         data-animate="{animate}"
         data-anim-duration="{anim_duration}"
         src="{src}"
         style="{style}" />'''

        elif elem_type == "audio":
            src = elem.get("src", "")
            volume = elem.get("volume", 1.0)
            track = elem.get("track_index", 10)
            return f'''    <audio
         data-start="{start}"
         data-duration="{duration}"
         data-track-index="{track}"
         data-volume="{volume}"
         src="{src}">
    </audio>'''

        return ""

    def render(
        self,
        composition: Composition,
        output_name: str = "output",
    ) -> RenderResult:
        """Render a composition to MP4.

        HyperFrames expects a project directory containing index.html.
        We create one and invoke the CLI from inside it.
        """
        output_path = self.output_dir / f"{output_name}.mp4"

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            html_path = project_dir / "index.html"
            html_path.write_text(composition.html)

            try:
                result = subprocess.run(
                    [
                        "npx",
                        "hyperframes",
                        "render",
                        "--output",
                        str(output_path),
                    ],
                    cwd=str(project_dir),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                if result.returncode != 0:
                    return RenderResult(
                        video_path=output_path,
                        duration=composition.duration,
                        width=composition.width,
                        height=composition.height,
                        success=False,
                        error=result.stderr or result.stdout,
                    )

                return RenderResult(
                    video_path=output_path,
                    duration=composition.duration,
                    width=composition.width,
                    height=composition.height,
                    success=True,
                )

            except subprocess.TimeoutExpired:
                return RenderResult(
                    video_path=output_path,
                    duration=composition.duration,
                    width=composition.width,
                    height=composition.height,
                    success=False,
                    error="Render timeout exceeded (300s)",
                )
            except FileNotFoundError:
                return RenderResult(
                    video_path=output_path,
                    duration=composition.duration,
                    width=composition.width,
                    height=composition.height,
                    success=False,
                    error="HyperFrames CLI not found. Run: npx skills add heygen-com/hyperframes",
                )

    def preview_html(self, composition: Composition) -> str:
        """Return the HTML for preview purposes."""
        return composition.html
