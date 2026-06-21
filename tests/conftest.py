"""pytest 共通フィクスチャ。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# リポジトリルートを import パスへ(``import src...`` を解決)。
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture
def brand_dna() -> dict:
    """テスト用の最小ブランド DNA(galaiworks を模した forbidden 入り)。"""
    return {
        "identity": {
            "name": "galaiworks",
            "unique_value_proposition": "海外最先端の AI を日本のひとり社長へ",
        },
        "voice": {"avoid": ["絶対", "必ず", "簡単"]},
        "forbidden": {
            "expressions": ["絶対稼げる", "誰でも簡単に", "魔法のような"],
            "topics": ["競合のディスり"],
        },
    }


@pytest.fixture
def config():
    from src.officina.config import OfficinaConfig

    return OfficinaConfig(price_floor_usd=1000.0, dry_run=True)
