"""Tests for Designer agent."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.designer import Designer
from src.video.hyperframes import Composition, HyperFramesClient, RenderResult
from src.video.video_use import EditConfig, VideoUseClient


@pytest.fixture
def brand_dna() -> dict:
    """Sample brand DNA for testing."""
    return {
        "identity": {
            "name": "TestBrand",
        },
        "visual": {
            "colors": ["#1a1a2e", "#eaeaea"],
            "fonts": {
                "heading": "Noto Sans JP",
                "body": "Noto Sans JP",
            },
            "style": "professional",
        },
    }


@pytest.fixture
def designer(brand_dna: dict) -> Designer:
    """Create a Designer instance for testing."""
    return Designer(
        api_key="test-api-key",
        brand_dna=brand_dna,
        output_dir=Path("/tmp/virtus-test"),
    )


class TestHyperFramesClient:
    """Tests for HyperFramesClient."""

    def test_create_composition(self, brand_dna: dict) -> None:
        """Test composition creation."""
        client = HyperFramesClient()

        elements = [
            {"type": "title", "text": "Test Title", "start": 0, "duration": 3},
            {"type": "subtitle", "text": "Subtitle", "start": 1, "duration": 2},
        ]

        composition = client.create_composition(
            elements=elements,
            platform="youtube",
            duration=10.0,
            brand_dna=brand_dna,
        )

        assert isinstance(composition, Composition)
        assert composition.width == 1920
        assert composition.height == 1080
        assert "Test Title" in composition.html
        assert "Subtitle" in composition.html
        assert "#1a1a2e" in composition.html

    def test_platform_dimensions(self) -> None:
        """Test platform-specific dimensions."""
        client = HyperFramesClient()

        youtube = client.create_composition([], platform="youtube")
        assert youtube.width == 1920
        assert youtube.height == 1080

        tiktok = client.create_composition([], platform="tiktok")
        assert tiktok.width == 1080
        assert tiktok.height == 1920

        instagram_feed = client.create_composition([], platform="instagram_feed")
        assert instagram_feed.width == 1080
        assert instagram_feed.height == 1080

    def test_element_types(self, brand_dna: dict) -> None:
        """Test different element types."""
        client = HyperFramesClient()

        elements = [
            {"type": "title", "text": "Main Title", "start": 0, "duration": 3},
            {"type": "subtitle", "text": "Sub", "start": 1, "duration": 2},
            {"type": "lower_third", "name": "John Doe", "title": "CEO", "start": 2, "duration": 4},
            {"type": "video", "src": "video.mp4", "start": 0, "duration": 10},
            {"type": "audio", "src": "music.mp3", "start": 0, "duration": 10, "volume": 0.5},
        ]

        composition = client.create_composition(
            elements=elements,
            brand_dna=brand_dna,
        )

        assert "Main Title" in composition.html
        assert "John Doe" in composition.html
        assert "CEO" in composition.html
        assert "video.mp4" in composition.html
        assert "music.mp3" in composition.html


class TestVideoUseClient:
    """Tests for VideoUseClient."""

    def test_edit_config_defaults(self) -> None:
        """Test EditConfig default values."""
        config = EditConfig()

        assert config.remove_filler_words is True
        assert config.remove_silence is True
        assert config.color_grade is True
        assert config.auto_subtitles is False

    @patch("subprocess.run")
    def test_get_video_duration(self, mock_run: MagicMock) -> None:
        """Test video duration extraction."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"format": {"duration": "120.5"}}',
        )

        client = VideoUseClient()
        duration = client._get_video_duration(Path("/tmp/test.mp4"))

        assert duration == 120.5


class TestDesigner:
    """Tests for Designer agent."""

    def test_init(self, designer: Designer) -> None:
        """Test Designer initialization."""
        assert designer.model == "claude-sonnet-4-6"
        assert "hyperframes" in designer.skills
        assert "video-use" in designer.skills

    def test_get_brand_colors(self, designer: Designer) -> None:
        """Test brand color extraction."""
        colors = designer.get_brand_colors()
        assert colors == ["#1a1a2e", "#eaeaea"]

    def test_get_brand_fonts(self, designer: Designer) -> None:
        """Test brand font extraction."""
        fonts = designer.get_brand_fonts()
        assert fonts["heading"] == "Noto Sans JP"
        assert fonts["body"] == "Noto Sans JP"

    def test_execute_unknown_task(self, designer: Designer) -> None:
        """Test handling of unknown task types."""
        result = designer.execute({"task_type": "unknown"})
        assert "error" in result

    @patch.object(HyperFramesClient, "render")
    @patch.object(HyperFramesClient, "create_composition")
    def test_create_video(
        self,
        mock_create: MagicMock,
        mock_render: MagicMock,
        designer: Designer,
    ) -> None:
        """Test video creation."""
        mock_create.return_value = Composition(
            html="<html>test</html>",
            width=1920,
            height=1080,
        )
        mock_render.return_value = RenderResult(
            video_path=Path("/tmp/output.mp4"),
            duration=10.0,
            width=1920,
            height=1080,
            success=True,
        )

        result = designer.execute(
            {
                "task_type": "video",
                "context": {
                    "platform": "youtube",
                    "duration": 10.0,
                    "elements": [
                        {"type": "title", "text": "Test", "start": 0, "duration": 3},
                    ],
                },
            }
        )

        assert result["success"] is True
        assert result["task_type"] == "video"
        assert "video_path" in result

    @patch.object(VideoUseClient, "edit")
    def test_edit_footage_file_not_found(
        self,
        mock_edit: MagicMock,
        designer: Designer,
    ) -> None:
        """Test editing with non-existent file."""
        result = designer.execute(
            {
                "task_type": "edit_footage",
                "context": {
                    "input_path": "/nonexistent/file.mp4",
                },
            }
        )

        assert "error" in result
        assert "not found" in result["error"]

    def test_format_visual_guide(self, designer: Designer) -> None:
        """Test visual guide formatting."""
        guide = designer._format_visual_guide()

        assert "#1a1a2e" in guide
        assert "Noto Sans JP" in guide
        assert "professional" in guide
