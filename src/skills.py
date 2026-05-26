"""Skill loader for galaiworks proprietary IPs."""

from pathlib import Path
from typing import Any

SKILLS_DIR = Path(__file__).parent.parent / ".claude" / "skills"


class SkillLoader:
    """Load skill definitions from .claude/skills/."""

    @staticmethod
    def load(skill_name: str) -> str:
        """Load a skill definition as text."""
        skill_path = SKILLS_DIR / skill_name / "SKILL.md"
        if skill_path.exists():
            return skill_path.read_text(encoding="utf-8")
        return f"# Skill: {skill_name}\n(SKILL.md not found at {skill_path})"

    @staticmethod
    def load_many(skill_names: list[str]) -> str:
        """Load multiple skills concatenated."""
        parts = []
        for name in skill_names:
            parts.append(f"## Skill: {name}\n\n{SkillLoader.load(name)}")
        return "\n\n---\n\n".join(parts)

    @staticmethod
    def available() -> list[str]:
        """List available skills."""
        if not SKILLS_DIR.exists():
            return []
        return sorted(p.name for p in SKILLS_DIR.iterdir() if p.is_dir())


def format_brand_dna(brand_dna: dict[str, Any]) -> str:
    """Format brand DNA dict as readable text for system prompts."""
    parts = []

    identity = brand_dna.get("identity", {})
    if identity:
        parts.append("# Identity")
        for k, v in identity.items():
            parts.append(f"- {k}: {v}")

    voice = brand_dna.get("voice", {})
    if voice:
        parts.append("\n# Voice")
        parts.append(f"- tone: {voice.get('tone', '')}")
        vocab = voice.get("vocabulary", {})
        if vocab:
            preferred = vocab.get("preferred", [])
            avoid = vocab.get("avoid", [])
            if preferred:
                parts.append(f"- preferred: {', '.join(preferred)}")
            if avoid:
                parts.append(f"- avoid: {', '.join(avoid)}")
        sig = voice.get("signature_phrases", [])
        if sig:
            parts.append(f"- signature_phrases: {', '.join(sig)}")

    forbidden = brand_dna.get("forbidden", {})
    if forbidden:
        parts.append("\n# Forbidden")
        for k, v in forbidden.items():
            if isinstance(v, list):
                parts.append(f"- {k}: {', '.join(v)}")
            else:
                parts.append(f"- {k}: {v}")

    return "\n".join(parts)
