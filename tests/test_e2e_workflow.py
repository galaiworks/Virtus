"""E2E 統合テスト: Researcher → Brain → Connector → Guardian.

サミット 6/4 デモで動かす予定のワークフローを 1 度通しで実行.
全 LLM 呼び出しはモック.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.agents.connector import Connector
from src.agents.guardian import Guardian
from src.agents.researcher import Researcher
from src.brain.store import BrainStore
from src.prospecting.sources import PressRelease, ProspectingSource


class _StubSource(ProspectingSource):
    name = "stub_e2e"

    def __init__(self, releases: list[PressRelease]) -> None:
        self.releases = releases

    def fetch(self, period_hours: int = 24) -> list[PressRelease]:
        return list(self.releases)


def _approved_verdict_json() -> str:
    return json.dumps(
        {
            "brand_dna": {"score": 25, "issues": []},
            "legal": {"score": 25, "issues": []},
            "quality": {"score": 19, "issues": []},
            "target_fit": {"score": 15, "issues": []},
            "overpromise": {"score": 10, "issues": []},
            "hallucination": {"score": 5, "issues": []},
            "total": 99,
            "verdict": "APPROVED",
            "self_reflection_passed": True,
            "feedback": "",
        }
    )


def _make_client(responses: list[str]) -> MagicMock:
    client = MagicMock()

    def side_effect(*_args, **_kwargs):
        text = responses.pop(0)
        msg = MagicMock()
        msg.content = [MagicMock(text=text)]
        return msg

    client.messages.create.side_effect = side_effect
    return client


def test_full_workflow_active_prospecting_to_dm_draft(galaiworks_brand_dna):
    """
    1. Researcher が PR タイムズから 1 件抽出 (95 点)
    2. Brain に保存
    3. Connector が上位リードに対する DM 草案を生成 (LLM モック)
    4. Guardian が DM を 95 点ループで評価 (LLM モック、APPROVED)
    5. 監査ログに 2 件記録される
    """
    store = BrainStore()
    high = PressRelease(
        source_id="rel_001",
        title="株式会社サンプル AI、シリーズ A で 5 億円の資金調達",
        description="年商 12 億円、採用拡大も実施。業界トップシェア",
        url="https://prtimes.jp/sample/001",
        published_at=datetime(2030, 5, 25, 10, 0, tzinfo=timezone.utc),
        company="株式会社サンプル AI",
        categories=("SaaS",),
    )
    researcher = Researcher(
        api_key="x",
        model="claude-sonnet-4-6",
        brand_dna=galaiworks_brand_dna,
        sources=[_StubSource([high])],
        store=store,
        client=MagicMock(),
    )

    # --- Step 1: 能動探索
    prospecting_result = researcher.execute(
        {
            "task_type": "active_prospecting",
            "context": {
                "target_industries": ["SaaS"],
                "min_score": 60,
                "top_n": 10,
            },
        }
    )
    assert prospecting_result["count"] == 1

    # --- Step 2: Brain から上位を取り出す
    top_leads = store.top_leads(limit=5, min_score=60)
    assert len(top_leads) == 1
    target_lead = top_leads[0]

    # --- Step 3: Connector が DM 草案生成
    dm_draft = "山田さん、ご無沙汰しています。先日の調達おめでとうございます..."
    connector = Connector(
        api_key="x",
        model="claude-sonnet-4-6",
        brand_dna=galaiworks_brand_dna,
        client=_make_client([dm_draft]),
    )
    dm_result = connector.execute(
        {
            "task_type": "draft_outreach_dm",
            "context": {
                "customer_name": "ガライ",
                "recipient": {
                    "name": "山田太郎",
                    "company": target_lead["company"],
                    "lead_score": target_lead["score"],
                },
                "prior_context": f"PR タイムズで調達ニュースを確認: {target_lead['title']}",
                "cta": "サミット招待 + 1on1 (15 分)",
            },
        }
    )
    assert dm_result["draft"] == dm_draft
    assert dm_result["requires_human_approval"] is True

    # --- Step 4: Guardian で 95 点ループ
    guardian = Guardian(
        api_key="x",
        model="claude-opus-4-7",
        brand_dna=galaiworks_brand_dna,
        client=_make_client([_approved_verdict_json()]),
    )
    verdict = guardian.evaluate(dm_result["draft"], content_type="outreach_dm")
    assert verdict.approved
    assert verdict.total_score == 99

    # --- Step 5: 監査ログを Brain に記録
    store.log_audit(
        agent="Guardian",
        action="evaluate",
        payload={
            "content_type": "outreach_dm",
            "total_score": verdict.total_score,
            "verdict": verdict.verdict,
        },
        content_id=target_lead["source_id"],
    )

    audit = store.recent_audit(limit=10)
    actions = [(row["agent"], row["action"]) for row in audit]
    assert ("Guardian", "evaluate") in actions
    assert ("Researcher", "active_prospecting") in actions
    store.close()
