"""Base agent class for all Virtus agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from anthropic import Anthropic

from ..utils.logger import get_logger


@dataclass
class AgentResult:
    """Result from agent execution."""

    success: bool
    content: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class BaseAgent(ABC):
    """Base class for all Virtus agents."""

    name: str = "base"
    model_tier: str = "execution"

    def __init__(
        self,
        api_key: str,
        model: str,
        brand_dna: dict[str, Any],
        skills: list[str] | None = None,
        max_tokens: int = 4096,
    ):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.brand_dna = brand_dna
        self.skills = skills or []
        self.max_tokens = max_tokens
        self.logger = get_logger(f"virtus.{self.name}")

    @abstractmethod
    def execute(self, task: dict[str, Any]) -> AgentResult:
        """Execute the agent's main task."""
        ...

    def call_llm(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
    ) -> str:
        """Call the LLM with given system prompt and messages."""
        self.logger.debug(f"Calling LLM with {len(messages)} messages")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens or self.max_tokens,
            system=system,
            messages=messages,
        )

        content = response.content[0].text
        self.logger.debug(f"LLM response: {len(content)} chars")
        return content

    def format_brand_dna(self) -> str:
        """Format brand DNA for system prompt."""
        if not self.brand_dna:
            return "No brand DNA configured."

        parts = []

        if identity := self.brand_dna.get("identity"):
            parts.append(f"【Identity】\n{self._format_dict(identity)}")

        if voice := self.brand_dna.get("voice"):
            parts.append(f"【Voice】\n{self._format_dict(voice)}")

        if forbidden := self.brand_dna.get("forbidden"):
            if isinstance(forbidden, list):
                parts.append(f"【Forbidden】\n- " + "\n- ".join(forbidden))
            else:
                parts.append(f"【Forbidden】\n{self._format_dict(forbidden)}")

        return "\n\n".join(parts)

    def _format_dict(self, d: dict[str, Any], indent: int = 0) -> str:
        """Format dictionary for display."""
        lines = []
        prefix = "  " * indent
        for key, value in d.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(self._format_dict(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:")
                for item in value:
                    lines.append(f"{prefix}  - {item}")
            else:
                lines.append(f"{prefix}{key}: {value}")
        return "\n".join(lines)

    def get_system_prompt(self) -> str:
        """Get the base system prompt. Override in subclasses."""
        return f"""あなたは Virtus の {self.name} エージェントです。

以下のブランドDNAを完全に遵守してください:

{self.format_brand_dna()}

常に最高品質の出力を心がけてください。"""
