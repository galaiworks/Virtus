"""Video-Use integration for AI-powered video editing."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EditResult:
    """Result of a Video-Use edit operation."""

    video_path: Path
    duration: float
    success: bool
    transcript: str | None = None
    error: str | None = None


@dataclass
class EditConfig:
    """Configuration for video editing."""

    remove_filler_words: bool = True
    remove_silence: bool = True
    silence_threshold_db: float = -40.0
    min_silence_duration: float = 0.5
    color_grade: bool = True
    auto_subtitles: bool = False
    subtitle_style: str = "modern"
    target_duration: float | None = None
    fade_audio_at_cuts: bool = True


class VideoUseClient:
    """Client for Video-Use AI video editing."""

    FILLER_WORDS_JA = [
        "えー",
        "えーと",
        "あの",
        "あのー",
        "まあ",
        "なんか",
        "その",
        "そのー",
        "ちょっと",
        "やっぱり",
        "やっぱ",
        "みたいな",
        "っていうか",
        "まぁ",
    ]

    FILLER_WORDS_EN = [
        "um",
        "uh",
        "like",
        "you know",
        "basically",
        "actually",
        "literally",
        "right",
        "so",
        "well",
        "I mean",
    ]

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or Path.cwd() / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def edit(
        self,
        input_path: Path,
        config: EditConfig | None = None,
        output_name: str | None = None,
    ) -> EditResult:
        """Edit a video using Video-Use."""
        config = config or EditConfig()
        output_name = output_name or f"{input_path.stem}_edited"
        output_path = self.output_dir / f"{output_name}.mp4"

        try:
            result = subprocess.run(
                [
                    "npx",
                    "video-use",
                    "edit",
                    str(input_path),
                    "-o",
                    str(output_path),
                    "--remove-filler" if config.remove_filler_words else "",
                    "--remove-silence" if config.remove_silence else "",
                    f"--silence-threshold={config.silence_threshold_db}"
                    if config.remove_silence
                    else "",
                    "--color-grade" if config.color_grade else "",
                    "--subtitles" if config.auto_subtitles else "",
                    f"--subtitle-style={config.subtitle_style}" if config.auto_subtitles else "",
                    f"--target-duration={config.target_duration}" if config.target_duration else "",
                    "--fade-cuts" if config.fade_audio_at_cuts else "",
                ],
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode != 0:
                return EditResult(
                    video_path=output_path,
                    duration=0.0,
                    success=False,
                    error=result.stderr,
                )

            duration = self._get_video_duration(output_path)

            return EditResult(
                video_path=output_path,
                duration=duration,
                success=True,
            )

        except subprocess.TimeoutExpired:
            return EditResult(
                video_path=output_path,
                duration=0.0,
                success=False,
                error="Edit timeout exceeded (600s)",
            )
        except FileNotFoundError:
            return self._edit_with_ffmpeg_fallback(input_path, config, output_path)

    def _edit_with_ffmpeg_fallback(
        self,
        input_path: Path,
        config: EditConfig,
        output_path: Path,
    ) -> EditResult:
        """Fallback to FFmpeg-based editing if Video-Use is not available."""
        try:
            filters = []

            if config.remove_silence:
                filters.append(
                    f"silenceremove=start_periods=1:start_silence={config.min_silence_duration}"
                    f":start_threshold={config.silence_threshold_db}dB"
                )

            if config.color_grade:
                filters.append("eq=contrast=1.1:brightness=0.05:saturation=1.1")

            filter_str = ",".join(filters) if filters else "null"

            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(input_path),
                "-vf",
                filter_str,
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                str(output_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode != 0:
                return EditResult(
                    video_path=output_path,
                    duration=0.0,
                    success=False,
                    error=f"FFmpeg error: {result.stderr}",
                )

            duration = self._get_video_duration(output_path)

            return EditResult(
                video_path=output_path,
                duration=duration,
                success=True,
            )

        except FileNotFoundError:
            return EditResult(
                video_path=output_path,
                duration=0.0,
                success=False,
                error="Neither Video-Use nor FFmpeg found. Install one of them.",
            )

    def transcribe(self, video_path: Path) -> str | None:
        """Transcribe video audio using Whisper."""
        try:
            result = subprocess.run(
                [
                    "npx",
                    "video-use",
                    "transcribe",
                    str(video_path),
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get("text", "")

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return None

    def extract_best_clips(
        self,
        video_path: Path,
        num_clips: int = 5,
        clip_duration: float = 15.0,
    ) -> list[EditResult]:
        """Extract the best clips from a video."""
        clips = []

        try:
            result = subprocess.run(
                [
                    "npx",
                    "video-use",
                    "extract-clips",
                    str(video_path),
                    f"--num={num_clips}",
                    f"--duration={clip_duration}",
                    "--output-dir",
                    str(self.output_dir),
                ],
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                for clip_info in data.get("clips", []):
                    clip_path = Path(clip_info["path"])
                    clips.append(
                        EditResult(
                            video_path=clip_path,
                            duration=clip_info.get("duration", clip_duration),
                            success=True,
                        )
                    )

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return clips

    def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration using ffprobe."""
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "json",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                return float(data.get("format", {}).get("duration", 0.0))

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return 0.0

    def merge_with_overlay(
        self,
        base_video: Path,
        overlay_video: Path,
        output_name: str = "merged",
    ) -> EditResult:
        """Merge base video with an overlay video (e.g., HyperFrames output)."""
        output_path = self.output_dir / f"{output_name}.mp4"

        try:
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(base_video),
                "-i",
                str(overlay_video),
                "-filter_complex",
                "[0:v][1:v]overlay=0:0:enable='between(t,0,999)'[outv]",
                "-map",
                "[outv]",
                "-map",
                "0:a?",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                str(output_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode != 0:
                return EditResult(
                    video_path=output_path,
                    duration=0.0,
                    success=False,
                    error=f"FFmpeg merge error: {result.stderr}",
                )

            duration = self._get_video_duration(output_path)

            return EditResult(
                video_path=output_path,
                duration=duration,
                success=True,
            )

        except FileNotFoundError:
            return EditResult(
                video_path=output_path,
                duration=0.0,
                success=False,
                error="FFmpeg not found",
            )
