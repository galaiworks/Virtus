"""Configuration management for Virtus."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ModelConfig:
    """Model configuration for agents."""

    strategic: str = "claude-opus-4-7"
    execution: str = "claude-sonnet-4-6"
    batch: str = "claude-haiku-4-5"


@dataclass
class Config:
    """Virtus configuration."""

    api_key: str = ""
    customer_id: str = ""
    brain_path: Path = field(default_factory=lambda: Path("brain"))
    models: ModelConfig = field(default_factory=ModelConfig)
    max_tokens: int = 4096
    quality_threshold: int = 95
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> Config:
        """Load configuration from environment variables."""
        return cls(
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            customer_id=os.getenv("VIRTUS_CUSTOMER_ID", "default"),
            brain_path=Path(os.getenv("VIRTUS_BRAIN_PATH", "brain")),
        )

    @classmethod
    def from_yaml(cls, path: str | Path) -> Config:
        """Load configuration from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def get_model(self, tier: str) -> str:
        """Get model name by tier."""
        return getattr(self.models, tier, self.models.execution)

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        if not self.api_key:
            errors.append("ANTHROPIC_API_KEY is not set")
        if not self.customer_id:
            errors.append("Customer ID is not set")
        return errors
