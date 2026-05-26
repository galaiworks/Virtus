"""Virtus Brain Layer - Customer data persistence and brand DNA management.

BYOK原則: 顧客データはローカルのみ保存、galaiworksサーバーには永続保存しない。
"""

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass
class BrandDNA:
    """Customer brand DNA structure."""

    identity: dict[str, Any] = field(default_factory=dict)
    voice: dict[str, Any] = field(default_factory=dict)
    content_strategy: dict[str, Any] = field(default_factory=dict)
    forbidden: dict[str, Any] = field(default_factory=dict)
    reference: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "identity": self.identity,
            "voice": self.voice,
            "content_strategy": self.content_strategy,
            "forbidden": self.forbidden,
            "reference": self.reference,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BrandDNA":
        """Create from dictionary."""
        return cls(
            identity=data.get("identity", {}),
            voice=data.get("voice", {}),
            content_strategy=data.get("content_strategy", {}),
            forbidden=data.get("forbidden", {}),
            reference=data.get("reference", {}),
        )


@dataclass
class ContentRecord:
    """Record of generated content."""

    content_id: str
    content_type: str
    title: str
    content: str
    platform: str
    created_at: str
    published_at: str | None = None
    guardian_score: int | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


class BrainLayer:
    """Manages customer-specific data persistence.

    Directory structure:
    brain/customers/{customer_id}/
    ├── brand-dna.yaml         # Brand DNA configuration
    ├── content/               # Generated content history
    │   ├── {content_id}.json
    │   └── ...
    ├── learning/              # Learning data and patterns
    │   ├── voice-analysis.json
    │   └── patterns.json
    └── logs/                  # Audit logs
        ├── evaluations.jsonl
        └── escalations.jsonl
    """

    def __init__(self, brain_root: Path | None = None) -> None:
        self.brain_root = brain_root or Path.cwd() / "brain"
        self.customers_dir = self.brain_root / "customers"

    def _customer_path(self, customer_id: str) -> Path:
        """Get customer directory path."""
        return self.customers_dir / customer_id

    def customer_exists(self, customer_id: str) -> bool:
        """Check if customer data exists."""
        return self._customer_path(customer_id).exists()

    def init_customer(self, customer_id: str) -> Path:
        """Initialize customer data directory."""
        customer_path = self._customer_path(customer_id)
        customer_path.mkdir(parents=True, exist_ok=True)

        (customer_path / "content").mkdir(exist_ok=True)
        (customer_path / "learning").mkdir(exist_ok=True)
        (customer_path / "logs").mkdir(exist_ok=True)

        return customer_path

    def save_brand_dna(self, customer_id: str, brand_dna: BrandDNA | dict[str, Any]) -> Path:
        """Save brand DNA to customer directory."""
        customer_path = self.init_customer(customer_id)
        dna_path = customer_path / "brand-dna.yaml"

        data = brand_dna.to_dict() if isinstance(brand_dna, BrandDNA) else brand_dna

        with open(dna_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        return dna_path

    def load_brand_dna(self, customer_id: str) -> BrandDNA | None:
        """Load brand DNA from customer directory."""
        dna_path = self._customer_path(customer_id) / "brand-dna.yaml"

        if not dna_path.exists():
            return None

        with open(dna_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return BrandDNA.from_dict(data) if data else None

    def load_brand_dna_dict(self, customer_id: str) -> dict[str, Any]:
        """Load brand DNA as dictionary (for agent initialization)."""
        brand_dna = self.load_brand_dna(customer_id)
        return brand_dna.to_dict() if brand_dna else {}

    def save_content(self, customer_id: str, record: ContentRecord) -> Path:
        """Save content record."""
        customer_path = self.init_customer(customer_id)
        content_dir = customer_path / "content"
        content_path = content_dir / f"{record.content_id}.json"

        data = {
            "content_id": record.content_id,
            "content_type": record.content_type,
            "title": record.title,
            "content": record.content,
            "platform": record.platform,
            "created_at": record.created_at,
            "published_at": record.published_at,
            "guardian_score": record.guardian_score,
            "metrics": record.metrics,
        }

        with open(content_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return content_path

    def load_content(self, customer_id: str, content_id: str) -> ContentRecord | None:
        """Load a specific content record."""
        content_path = self._customer_path(customer_id) / "content" / f"{content_id}.json"

        if not content_path.exists():
            return None

        with open(content_path, encoding="utf-8") as f:
            data = json.load(f)

        return ContentRecord(**data)

    def list_content(
        self,
        customer_id: str,
        content_type: str | None = None,
        platform: str | None = None,
        limit: int = 100,
    ) -> list[ContentRecord]:
        """List content records with optional filtering."""
        content_dir = self._customer_path(customer_id) / "content"

        if not content_dir.exists():
            return []

        records = []
        for content_file in sorted(content_dir.glob("*.json"), reverse=True):
            if len(records) >= limit:
                break

            with open(content_file, encoding="utf-8") as f:
                data = json.load(f)

            if content_type and data.get("content_type") != content_type:
                continue
            if platform and data.get("platform") != platform:
                continue

            records.append(ContentRecord(**data))

        return records

    def save_learning_data(self, customer_id: str, data_type: str, data: dict[str, Any]) -> Path:
        """Save learning/analysis data."""
        customer_path = self.init_customer(customer_id)
        learning_dir = customer_path / "learning"
        data_path = learning_dir / f"{data_type}.json"

        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return data_path

    def load_learning_data(self, customer_id: str, data_type: str) -> dict[str, Any] | None:
        """Load learning/analysis data."""
        data_path = self._customer_path(customer_id) / "learning" / f"{data_type}.json"

        if not data_path.exists():
            return None

        with open(data_path, encoding="utf-8") as f:
            return json.load(f)

    def append_log(self, customer_id: str, log_type: str, entry: dict[str, Any]) -> None:
        """Append to audit log (JSONL format)."""
        customer_path = self.init_customer(customer_id)
        log_path = customer_path / "logs" / f"{log_type}.jsonl"

        entry_with_timestamp = {
            "timestamp": datetime.now().isoformat(),
            **entry,
        }

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry_with_timestamp, ensure_ascii=False) + "\n")

    def read_logs(
        self,
        customer_id: str,
        log_type: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Read audit logs (most recent first)."""
        log_path = self._customer_path(customer_id) / "logs" / f"{log_type}.jsonl"

        if not log_path.exists():
            return []

        entries = []
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))

        return list(reversed(entries[-limit:]))

    def delete_customer(self, customer_id: str) -> bool:
        """Delete all customer data (use with caution)."""
        customer_path = self._customer_path(customer_id)

        if not customer_path.exists():
            return False

        shutil.rmtree(customer_path)
        return True

    def export_customer_data(self, customer_id: str, export_path: Path) -> Path | None:
        """Export all customer data for portability."""
        customer_path = self._customer_path(customer_id)

        if not customer_path.exists():
            return None

        export_file = export_path / f"{customer_id}_export.zip"
        shutil.make_archive(
            str(export_file).replace(".zip", ""),
            "zip",
            customer_path,
        )

        return export_file


def generate_content_id() -> str:
    """Generate unique content ID."""
    import uuid

    return f"content_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def build_default_brand_dna() -> BrandDNA:
    """Build a default brand DNA template."""
    return BrandDNA(
        identity={
            "name": "",
            "business": "",
            "primary_target_audience": "",
            "unique_value_proposition": "",
        },
        voice={
            "tone": "",
            "personality": [],
            "preferred_phrases": [],
            "avoid_phrases": [],
            "signature_phrases": [],
        },
        content_strategy={
            "pillar_topics": [],
            "primary_platforms": [],
            "publishing_frequency": {},
        },
        forbidden={
            "topics": [],
            "expressions": [],
            "practices": [],
        },
        reference={
            "past_winning_content": [],
            "competitor_examples": [],
            "inspiration_sources": [],
        },
    )
