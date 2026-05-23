"""Tests for Brain Layer - customer data persistence."""

from datetime import datetime
from pathlib import Path

import pytest

from src.brain import (
    BrainLayer,
    BrandDNA,
    ContentRecord,
    build_default_brand_dna,
    generate_content_id,
)


@pytest.fixture
def brain_root(tmp_path: Path) -> Path:
    """Create temporary brain root directory."""
    return tmp_path / "brain"


@pytest.fixture
def brain(brain_root: Path) -> BrainLayer:
    """Create BrainLayer instance."""
    return BrainLayer(brain_root=brain_root)


@pytest.fixture
def sample_brand_dna() -> BrandDNA:
    """Create sample brand DNA."""
    return BrandDNA(
        identity={
            "name": "テスト企業",
            "business": "AIコンサルティング",
            "primary_target_audience": "ひとり社長",
            "unique_value_proposition": "日本語特化AI",
        },
        voice={
            "tone": "プロフェッショナル × 親近感",
            "personality": ["率直", "数字に強い"],
            "preferred_phrases": ["率直に言うと", "本質は"],
            "avoid_phrases": ["絶対", "必ず"],
            "signature_phrases": ["これが結論です"],
        },
        content_strategy={
            "pillar_topics": ["AI活用", "業務自動化"],
            "primary_platforms": ["note", "X"],
            "publishing_frequency": {"note": "週2本", "x": "日5本"},
        },
        forbidden={
            "topics": ["政治", "宗教"],
            "expressions": ["100%", "魔法のような"],
            "practices": ["スパム送信"],
        },
        reference={
            "past_winning_content": [],
            "competitor_examples": [],
            "inspiration_sources": [],
        },
    )


class TestBrandDNA:
    """Tests for BrandDNA dataclass."""

    def test_to_dict(self, sample_brand_dna: BrandDNA) -> None:
        """Test conversion to dictionary."""
        data = sample_brand_dna.to_dict()

        assert data["identity"]["name"] == "テスト企業"
        assert "率直" in data["voice"]["personality"]
        assert "note" in data["content_strategy"]["primary_platforms"]

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {
            "identity": {"name": "FromDict企業"},
            "voice": {"tone": "カジュアル"},
            "content_strategy": {},
            "forbidden": {},
            "reference": {},
        }

        brand_dna = BrandDNA.from_dict(data)

        assert brand_dna.identity["name"] == "FromDict企業"
        assert brand_dna.voice["tone"] == "カジュアル"

    def test_roundtrip(self, sample_brand_dna: BrandDNA) -> None:
        """Test dict -> BrandDNA -> dict roundtrip."""
        data = sample_brand_dna.to_dict()
        restored = BrandDNA.from_dict(data)

        assert restored.to_dict() == data


class TestBrainLayer:
    """Tests for BrainLayer."""

    def test_init_customer(self, brain: BrainLayer) -> None:
        """Test customer directory initialization."""
        customer_path = brain.init_customer("test_001")

        assert customer_path.exists()
        assert (customer_path / "content").exists()
        assert (customer_path / "learning").exists()
        assert (customer_path / "logs").exists()

    def test_customer_exists(self, brain: BrainLayer) -> None:
        """Test customer existence check."""
        assert not brain.customer_exists("nonexistent")

        brain.init_customer("test_001")

        assert brain.customer_exists("test_001")

    def test_save_and_load_brand_dna(
        self,
        brain: BrainLayer,
        sample_brand_dna: BrandDNA,
    ) -> None:
        """Test brand DNA persistence."""
        brain.save_brand_dna("test_001", sample_brand_dna)

        loaded = brain.load_brand_dna("test_001")

        assert loaded is not None
        assert loaded.identity["name"] == "テスト企業"
        assert loaded.voice["tone"] == "プロフェッショナル × 親近感"

    def test_save_brand_dna_as_dict(self, brain: BrainLayer) -> None:
        """Test saving brand DNA from dictionary."""
        dna_dict = {
            "identity": {"name": "DictTest"},
            "voice": {"tone": "formal"},
        }

        brain.save_brand_dna("test_001", dna_dict)

        loaded = brain.load_brand_dna("test_001")

        assert loaded is not None
        assert loaded.identity["name"] == "DictTest"

    def test_load_brand_dna_dict(
        self,
        brain: BrainLayer,
        sample_brand_dna: BrandDNA,
    ) -> None:
        """Test loading brand DNA as dictionary."""
        brain.save_brand_dna("test_001", sample_brand_dna)

        loaded_dict = brain.load_brand_dna_dict("test_001")

        assert loaded_dict["identity"]["name"] == "テスト企業"
        assert isinstance(loaded_dict, dict)

    def test_load_nonexistent_brand_dna(self, brain: BrainLayer) -> None:
        """Test loading non-existent brand DNA."""
        assert brain.load_brand_dna("nonexistent") is None
        assert brain.load_brand_dna_dict("nonexistent") == {}


class TestContentManagement:
    """Tests for content record management."""

    def test_save_and_load_content(self, brain: BrainLayer) -> None:
        """Test content record persistence."""
        record = ContentRecord(
            content_id="content_20260523_001",
            content_type="note_article",
            title="テスト記事",
            content="これはテスト記事の本文です。",
            platform="note",
            created_at=datetime.now().isoformat(),
            guardian_score=96,
            metrics={"views": 100},
        )

        brain.save_content("test_001", record)

        loaded = brain.load_content("test_001", "content_20260523_001")

        assert loaded is not None
        assert loaded.title == "テスト記事"
        assert loaded.guardian_score == 96

    def test_list_content(self, brain: BrainLayer) -> None:
        """Test listing content records."""
        for i in range(3):
            record = ContentRecord(
                content_id=f"content_{i:03d}",
                content_type="note_article" if i % 2 == 0 else "x_post",
                title=f"記事{i}",
                content=f"本文{i}",
                platform="note" if i % 2 == 0 else "x",
                created_at=datetime.now().isoformat(),
            )
            brain.save_content("test_001", record)

        all_content = brain.list_content("test_001")
        assert len(all_content) == 3

        note_only = brain.list_content("test_001", content_type="note_article")
        assert len(note_only) == 2

        x_only = brain.list_content("test_001", platform="x")
        assert len(x_only) == 1

    def test_list_content_limit(self, brain: BrainLayer) -> None:
        """Test content listing with limit."""
        for i in range(10):
            record = ContentRecord(
                content_id=f"content_{i:03d}",
                content_type="note_article",
                title=f"記事{i}",
                content=f"本文{i}",
                platform="note",
                created_at=datetime.now().isoformat(),
            )
            brain.save_content("test_001", record)

        limited = brain.list_content("test_001", limit=5)
        assert len(limited) == 5


class TestLearningData:
    """Tests for learning data management."""

    def test_save_and_load_learning_data(self, brain: BrainLayer) -> None:
        """Test learning data persistence."""
        voice_analysis = {
            "tone_scores": {"professional": 0.8, "casual": 0.2},
            "common_phrases": ["率直に言うと", "本質は"],
            "analyzed_at": datetime.now().isoformat(),
        }

        brain.save_learning_data("test_001", "voice-analysis", voice_analysis)

        loaded = brain.load_learning_data("test_001", "voice-analysis")

        assert loaded is not None
        assert loaded["tone_scores"]["professional"] == 0.8

    def test_load_nonexistent_learning_data(self, brain: BrainLayer) -> None:
        """Test loading non-existent learning data."""
        assert brain.load_learning_data("test_001", "nonexistent") is None


class TestAuditLogs:
    """Tests for audit logging."""

    def test_append_and_read_logs(self, brain: BrainLayer) -> None:
        """Test audit log appending and reading."""
        brain.append_log(
            "test_001",
            "evaluations",
            {
                "content_id": "content_001",
                "score": 95,
                "verdict": "approved",
            },
        )
        brain.append_log(
            "test_001",
            "evaluations",
            {
                "content_id": "content_002",
                "score": 88,
                "verdict": "rejected",
            },
        )

        logs = brain.read_logs("test_001", "evaluations")

        assert len(logs) == 2
        assert logs[0]["content_id"] == "content_002"  # Most recent first
        assert "timestamp" in logs[0]

    def test_read_logs_limit(self, brain: BrainLayer) -> None:
        """Test reading logs with limit."""
        for i in range(20):
            brain.append_log("test_001", "evaluations", {"index": i})

        limited = brain.read_logs("test_001", "evaluations", limit=5)

        assert len(limited) == 5
        assert limited[0]["index"] == 19  # Most recent


class TestCustomerManagement:
    """Tests for customer data management."""

    def test_delete_customer(
        self,
        brain: BrainLayer,
        sample_brand_dna: BrandDNA,
    ) -> None:
        """Test customer data deletion."""
        brain.save_brand_dna("test_001", sample_brand_dna)
        assert brain.customer_exists("test_001")

        result = brain.delete_customer("test_001")

        assert result is True
        assert not brain.customer_exists("test_001")

    def test_delete_nonexistent_customer(self, brain: BrainLayer) -> None:
        """Test deleting non-existent customer."""
        result = brain.delete_customer("nonexistent")
        assert result is False

    def test_export_customer_data(
        self,
        brain: BrainLayer,
        sample_brand_dna: BrandDNA,
        tmp_path: Path,
    ) -> None:
        """Test customer data export."""
        brain.save_brand_dna("test_001", sample_brand_dna)
        brain.save_content(
            "test_001",
            ContentRecord(
                content_id="content_001",
                content_type="note_article",
                title="テスト",
                content="本文",
                platform="note",
                created_at=datetime.now().isoformat(),
            ),
        )

        export_dir = tmp_path / "exports"
        export_dir.mkdir()

        export_path = brain.export_customer_data("test_001", export_dir)

        assert export_path is not None
        assert export_path.exists()
        assert export_path.suffix == ".zip"


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_generate_content_id(self) -> None:
        """Test content ID generation."""
        id1 = generate_content_id()
        id2 = generate_content_id()

        assert id1.startswith("content_")
        assert id1 != id2

    def test_build_default_brand_dna(self) -> None:
        """Test default brand DNA template."""
        default_dna = build_default_brand_dna()

        assert "name" in default_dna.identity
        assert "tone" in default_dna.voice
        assert "pillar_topics" in default_dna.content_strategy
        assert "topics" in default_dna.forbidden
