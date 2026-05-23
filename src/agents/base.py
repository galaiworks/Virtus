"""Base Agent class for all Virtus agents."""

from abc import ABC, abstractmethod
from typing import Any

from anthropic import Anthropic


class BaseAgent(ABC):
    """Base class for all Virtus agents."""

    def __init__(
        self,
        api_key: str,
        model: str,
        brand_dna: dict[str, Any],
        skills: list[str] | None = None,
    ) -> None:
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.brand_dna = brand_dna
        self.skills = skills or []

    @abstractmethod
    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent's main task."""
        ...

    def call_llm(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ) -> str:
        """Call the LLM with the given system prompt and messages."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        return response.content[0].text

    def get_brand_colors(self) -> list[str]:
        """Extract brand colors from brand DNA."""
        visual = self.brand_dna.get("visual", {})
        return visual.get("colors", ["#000000", "#FFFFFF"])

    def get_brand_fonts(self) -> dict[str, str]:
        """Extract brand fonts from brand DNA."""
        visual = self.brand_dna.get("visual", {})
        return visual.get("fonts", {"heading": "Inter", "body": "Inter"})
