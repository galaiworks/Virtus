"""brand_dna モジュールのユニットテスト."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.brand_dna import forbidden_expressions, format_brand_dna, load_brand_dna


def test_load_brand_dna_reads_yaml(tmp_path: Path):
    """YAML をパースして dict を返す."""
    p = tmp_path / "brand-dna.yml"
    p.write_text(
        yaml.safe_dump({"identity": {"name": "test"}}, allow_unicode=True),
        encoding="utf-8",
    )
    data = load_brand_dna(p)
    assert data == {"identity": {"name": "test"}}


def test_load_brand_dna_missing_file(tmp_path: Path):
    """存在しないファイルは FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_brand_dna(tmp_path / "missing.yml")


def test_format_brand_dna_is_yaml(galaiworks_brand_dna):
    """整形結果が YAML としてロード可能."""
    text = format_brand_dna(galaiworks_brand_dna)
    parsed = yaml.safe_load(text)
    assert parsed == galaiworks_brand_dna


def test_forbidden_expressions_merges_avoid_and_forbidden(galaiworks_brand_dna):
    """voice.vocabulary.avoid と forbidden.expressions をマージ."""
    result = forbidden_expressions(galaiworks_brand_dna)
    # avoid から
    assert "絶対" in result
    assert "100%" in result
    # forbidden から
    assert "絶対稼げる" in result
    # 重複排除
    assert len(result) == len(set(result))
