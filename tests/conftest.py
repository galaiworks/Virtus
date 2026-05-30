"""共通テストフィクスチャ."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def galaiworks_brand_dna() -> dict[str, Any]:
    """galaiworks 自身を例とした最小ブランド DNA."""
    return {
        "identity": {
            "name": "galaiworks",
            "primary_target_audience": "ひとり社長・コーチ・コンサル・専門家",
        },
        "voice": {
            "tone": "プロフェッショナル × 親近感 × 直球",
            "vocabulary": {
                "preferred": ["率直に言うと", "結論から言うと", "本質は"],
                "avoid": ["絶対", "必ず", "100%", "簡単"],
            },
            "signature_phrases": ["率直に言います", "現実的かつ厳密に"],
        },
        "forbidden": {
            "expressions": ["絶対稼げる", "誰でも簡単に", "魔法のような"],
        },
    }


@pytest.fixture
def fake_anthropic_client() -> MagicMock:
    """Anthropic クライアントを差し替えるためのモック."""
    client = MagicMock()
    # デフォルトの応答 (各テストで上書き可能)
    response = MagicMock()
    response.content = [MagicMock(text="MOCK_RESPONSE")]
    client.messages.create.return_value = response
    return client


def set_client_response(client: MagicMock, text: str) -> None:
    """モッククライアントの応答テキストを上書き."""
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    client.messages.create.return_value = response
