"""Lead Strategist の朝報生成テスト."""

from __future__ import annotations

from src.agents.lead_strategist import LeadStrategist
from tests.conftest import set_client_response

EXPECTED_BRIEF = """おはようございます、ガライ さん。2026 年 5 月 28 日 (木) です。

【今日の優先事項】
1. A 社の追いかけ電話を 10:30 に
2. サミット用スライド完成
3. M 社の月次レビュー準備

【背景データ】
- A 社は過去 3 件中 2 件で電話追いかけが奏功

【Virtus の動き】
- Researcher: 新規 4 件をダッシュボード反映
- Drafter: 登壇原稿 2nd ドラフトを 12:00 まで

【ガライ さんが判断すべきこと】
- M 社の次四半期方針
"""


def test_morning_brief_calls_llm_with_brand_dna(
    galaiworks_brand_dna, fake_anthropic_client
):
    """朝報生成時、システムプロンプトにブランド DNA が含まれる."""
    set_client_response(fake_anthropic_client, EXPECTED_BRIEF)

    agent = LeadStrategist(
        api_key="test",
        model="claude-opus-4-7",
        brand_dna=galaiworks_brand_dna,
        client=fake_anthropic_client,
    )

    result = agent.execute(
        {
            "task_type": "morning_brief",
            "context": {
                "customer_name": "ガライ",
                "current_date": "2026 年 5 月 28 日 (木)",
                "yesterday_data": {"reach": 1200},
                "active_leads": [{"name": "A 社"}],
            },
        }
    )

    assert result["task_type"] == "morning_brief"
    assert result["output"] == EXPECTED_BRIEF

    # システムプロンプトにブランド DNA とシグネチャフレーズが含まれることを確認
    call_args = fake_anthropic_client.messages.create.call_args
    system_prompt = call_args.kwargs["system"]
    assert "galaiworks" in system_prompt
    assert "率直に言います" in system_prompt
    # ブランド DNA の禁止語が読み込まれている
    assert "絶対" in system_prompt


def test_unsupported_task_type_raises(galaiworks_brand_dna, fake_anthropic_client):
    """サポート外の task_type は ValueError."""
    agent = LeadStrategist(
        api_key="test",
        model="claude-opus-4-7",
        brand_dna=galaiworks_brand_dna,
        client=fake_anthropic_client,
    )

    import pytest

    with pytest.raises(ValueError, match="サポートしていません"):
        agent.execute({"task_type": "unknown_task", "context": {}})


def test_morning_brief_includes_active_leads_in_user_message(
    galaiworks_brand_dna, fake_anthropic_client
):
    """ユーザメッセージに進行中リードが含まれる."""
    set_client_response(fake_anthropic_client, "朝報")
    agent = LeadStrategist(
        api_key="test",
        model="claude-opus-4-7",
        brand_dna=galaiworks_brand_dna,
        client=fake_anthropic_client,
    )

    agent.morning_brief(
        {
            "customer_name": "ガライ",
            "current_date": "2026-05-28",
            "active_leads": [{"id": "lead_001"}, {"id": "lead_002"}],
            "active_deals": [{"id": "deal_001"}],
        }
    )

    user_message = fake_anthropic_client.messages.create.call_args.kwargs["messages"][0]
    assert "進行中リード (2 件)" in user_message["content"]
    assert "進行中商談 (1 件)" in user_message["content"]
