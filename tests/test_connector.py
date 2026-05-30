"""Connector のテスト."""

from __future__ import annotations

import pytest

from src.agents.connector import Connector
from tests.conftest import set_client_response


def test_draft_outreach_dm_uses_brand_dna_and_returns_draft(
    galaiworks_brand_dna, fake_anthropic_client
):
    """システムプロンプトにブランド DNA + 受信者名が組み込まれ、ドラフトが返る."""
    set_client_response(fake_anthropic_client, "山田さん、ご無沙汰しています...")
    connector = Connector(
        api_key="x",
        model="claude-sonnet-4-6",
        brand_dna=galaiworks_brand_dna,
        client=fake_anthropic_client,
    )

    result = connector.execute(
        {
            "task_type": "draft_outreach_dm",
            "context": {
                "customer_name": "ガライ",
                "recipient": {"name": "山田太郎", "company": "B 工業"},
                "prior_context": "1 月の MTG で営業 DX 課題を共有",
                "cta": "サミット招待 + 1on1 (15 分)",
            },
        }
    )

    assert result["draft"].startswith("山田さん")
    assert result["requires_human_approval"] is True
    system = fake_anthropic_client.messages.create.call_args.kwargs["system"]
    assert "ガライ" in system
    assert "山田太郎" in system
    # 過剰約束禁止の指示が入っている
    assert "100%" in system or "保証表現" in system


def test_draft_dm_reply_includes_history_in_user_message(
    galaiworks_brand_dna, fake_anthropic_client
):
    """過去のやり取りがユーザメッセージに含まれる."""
    set_client_response(fake_anthropic_client, "返信案")
    connector = Connector(
        api_key="x",
        model="claude-sonnet-4-6",
        brand_dna=galaiworks_brand_dna,
        client=fake_anthropic_client,
    )

    connector.execute(
        {
            "task_type": "draft_dm_reply",
            "context": {
                "platform": "linkedin",
                "interaction_history": [{"from": "self", "text": "前回のメッセージ"}],
                "incoming_message": {"text": "ありがとうございます"},
            },
        }
    )

    user_msg = fake_anthropic_client.messages.create.call_args.kwargs["messages"][0][
        "content"
    ]
    assert "linkedin" in user_msg
    assert "前回のメッセージ" in user_msg
    assert "ありがとうございます" in user_msg


def test_unsupported_task_type_raises(galaiworks_brand_dna, fake_anthropic_client):
    connector = Connector(
        api_key="x",
        model="claude-sonnet-4-6",
        brand_dna=galaiworks_brand_dna,
        client=fake_anthropic_client,
    )
    with pytest.raises(ValueError, match="サポートしていません"):
        connector.execute({"task_type": "send_email"})
