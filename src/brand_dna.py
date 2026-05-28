"""ブランド DNA のロードとシリアライズ."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_brand_dna(path: str | Path) -> dict[str, Any]:
    """ブランド DNA YAML をロード.

    Args:
        path: brand-dna.yml のパス.

    Returns:
        パース済み辞書.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"brand-dna ファイルが存在しません: {p}")
    with p.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"brand-dna は dict である必要があります: {p}")
    return data


def format_brand_dna(brand_dna: dict[str, Any]) -> str:
    """ブランド DNA をシステムプロンプト埋め込み用に整形."""
    return yaml.safe_dump(brand_dna, allow_unicode=True, sort_keys=False)


def forbidden_expressions(brand_dna: dict[str, Any]) -> list[str]:
    """禁止表現リストを抽出."""
    voice = brand_dna.get("voice", {})
    vocab = voice.get("vocabulary", {})
    avoid = vocab.get("avoid", [])
    forbidden = brand_dna.get("forbidden", {}).get("expressions", [])
    return list(dict.fromkeys([*avoid, *forbidden]))
