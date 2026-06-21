"""エンドツーエンド:オーケストレーターのパイプライン実行(要件定義 §4-§6)。"""

from __future__ import annotations

import pytest

from src.officina.models import Deal, Lead, Stage
from src.officina.orchestrator import Orchestrator


@pytest.fixture
def deal() -> Deal:
    lead = Lead(company="株式会社テスト", contact="山田", email="yamada@test.co.jp")
    # 低 ACV(< $25k)= AI 主導が機能する帯(§3)。
    return Deal(lead=lead, acv=12_000.0, metadata={"icp_approved": True})


@pytest.fixture
def stage_inputs() -> dict:
    return {
        Stage.PROSPECTING: {
            "candidates": [
                {"company": "A社", "contact": "佐藤", "email": "a@a.co.jp"},
                {"company": "B社", "contact": "鈴木", "email": "b@b.co.jp"},
            ]
        },
        Stage.OUTREACH: {
            "lead": {"company": "A社", "contact": "佐藤"},
            "deliverability": {"domain_reputation": 95.0, "sent_today": 0},
        },
        Stage.QUALIFY: {"reply_text": "興味があります。資料をください。"},
        Stage.DISCOVERY: {
            "meeting_notes": {
                "goal": "集客自動化",
                "pain_points": ["時間不足"],
                "scope": "エージェント構築",
                "success_criteria": "リード月50件",
                "budget": "1.2万USD",
                "timeline": "2ヶ月",
            }
        },
        Stage.PROPOSAL: {"price_usd": 12_000.0, "list_price_usd": 12_000.0},
        Stage.BUILD: {"acceptance_tests": ["疎通", "品質", "受入"]},
    }


def test_runs_to_contract_human_gate(brand_dna, deal, stage_inputs):
    orch = Orchestrator(brand_dna=brand_dna)
    result = orch.run(deal, stage_inputs)
    # 自律で契約締結ゲート(🚩 ゲート A)まで到達し、人間待ちで停止。
    assert result.status == "pending_human"
    assert result.current_stage == Stage.CONTRACT
    assert result.metadata.get("pending_approval")


def test_full_run_through_both_human_gates(brand_dna, deal, stage_inputs):
    orch = Orchestrator(brand_dna=brand_dna)
    orch.run(deal, stage_inputs)
    # ゲート A:契約承認 → BUILD 実行 → ゲート B で再停止。
    orch.resume(deal, "approve", stage_inputs=stage_inputs)
    assert deal.status == "pending_human"
    assert deal.current_stage == Stage.DELIVERY_APPROVAL
    # ゲート B:納品承認 → 納品・アフター → 完了。
    orch.resume(deal, "approve", stage_inputs=stage_inputs)
    assert deal.status == "delivered"
    assert deal.current_stage == Stage.AFTERCARE


def test_icp_requires_human_approval_when_not_pregranted(brand_dna, stage_inputs):
    lead = Lead(company="X", email="x@x.co.jp")
    deal = Deal(lead=lead, acv=10_000.0)  # icp_approved なし
    orch = Orchestrator(brand_dna=brand_dna)
    result = orch.run(deal, stage_inputs)
    assert result.status == "pending_human"
    assert result.current_stage == Stage.ICP_RESEARCH


def test_high_acv_closing_requires_human(brand_dna, stage_inputs):
    lead = Lead(company="大型", email="big@corp.com")
    deal = Deal(lead=lead, acv=80_000.0, metadata={"icp_approved": True})
    orch = Orchestrator(brand_dna=brand_dna)
    result = orch.run(deal, stage_inputs)
    # $50k 超は人間主導クロージング(§3 ACV 閾値)。
    assert result.status == "pending_human"
    assert result.current_stage == Stage.CLOSING


def test_price_below_floor_escalates(brand_dna, deal, stage_inputs):
    from src.officina.config import OfficinaConfig

    cfg = OfficinaConfig(price_floor_usd=20_000.0)  # 下限 > 提示価格
    orch = Orchestrator(brand_dna=brand_dna, config=cfg)
    result = orch.run(deal, stage_inputs)
    assert result.status == "escalated"
    assert result.current_stage == Stage.PROPOSAL
    # リジェクトログに記録(= リグレッションテスト化)。
    assert len(orch.reject_log) >= 1


def test_opt_out_blocks_outreach(brand_dna, deal, stage_inputs):
    stage_inputs[Stage.OUTREACH]["opt_out"] = True
    orch = Orchestrator(brand_dna=brand_dna)
    result = orch.run(deal, stage_inputs)
    assert result.status == "escalated"
    assert result.current_stage == Stage.OUTREACH
