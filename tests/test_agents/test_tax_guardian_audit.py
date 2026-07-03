"""税理士エージェントの Guardian 連携・監査ログのテスト。

重点:
- 独占業務エスカレーションは「安全側の正しい挙動」として Guardian で PASS。
- 免責事項のない税務出力は Guardian が force_reject。
- すべての判定が監査ログに残る(boundary_verdict / escalation_level / 免責付与)。
"""

from __future__ import annotations

import json

import pytest

from src.agents.tax_accountant import TaxAccountant
from src.agents.tax_audit import TaxAuditEntry, TaxAuditLog
from src.agents.tax_review import guardian_for, result_to_review_text, review_tax_result
from src.officina.models import Verdict


@pytest.fixture
def agent(brand_dna) -> TaxAccountant:
    return TaxAccountant(model="claude-sonnet-4-6", brand_dna=brand_dna, dry_run=True)


# --- Guardian 連携 ---
def test_guardian_passes_normal_output_with_disclaimer(agent: TaxAccountant) -> None:
    result = agent.execute(
        {"type": "estimate_income_tax", "taxable_income": 3_000_000}
    )
    gate = review_tax_result(result, guardian_for(agent.brand_dna))
    assert gate.verdict == Verdict.PASS
    assert gate.score >= 95


def test_guardian_passes_escalation_as_safe_behavior(agent: TaxAccountant) -> None:
    # 独占業務を検出して止めた出力は「逃げずに正しく止めた」ので合格扱い。
    result = agent.execute(
        {"type": "categorize_expense", "request_text": "確定申告書を作って提出して"}
    )
    assert result.content_type == "escalation"
    gate = review_tax_result(result, guardian_for(agent.brand_dna))
    assert gate.verdict == Verdict.PASS
    assert gate.details["safe_escalation"] is True


def test_guardian_force_rejects_missing_disclaimer() -> None:
    from src.agents.base import AgentResult

    # 免責のない偽の税務出力 + 過剰約束 -> force_reject されるべき。
    fake = AgentResult(
        agent="tax_accountant",
        content_type="tax_support",
        output={
            "task_type": "estimate_income_tax",
            "result": {"estimated_total_tax": 100000, "note": "必ず節税できます"},
            "boundary_verdict": "pass",
        },
        meta={},
    )
    gate = review_tax_result(fake, guardian_for())
    assert gate.verdict == Verdict.ESCALATE
    assert gate.details.get("force_reject") is True
    assert any("免責" in r for r in gate.reasons)


def test_review_text_includes_disclaimer_and_notes(agent: TaxAccountant) -> None:
    result = agent.execute(
        {"type": "check_invoice", "invoice": {"issuer_name": "galaiworks"}}
    )
    text = result_to_review_text(result)
    assert "免責" in text
    assert "税理士" in text


# --- 監査ログ ---
def test_audit_log_records_normal_task(brand_dna) -> None:
    log = TaxAuditLog()
    agent = TaxAccountant(
        model="claude-sonnet-4-6", brand_dna=brand_dna, dry_run=True, audit_log=log
    )
    agent.execute({"type": "estimate_income_tax", "taxable_income": 5_000_000})
    assert len(log.entries) == 1
    entry = log.entries[0]
    assert entry["boundary_verdict"] == "pass"
    assert entry["escalation_level"] == 0
    assert entry["disclaimer_attached"] is True
    assert entry["source_year"]
    assert entry["timestamp"]


def test_audit_log_records_escalation(brand_dna) -> None:
    log = TaxAuditLog()
    agent = TaxAccountant(
        model="claude-sonnet-4-6", brand_dna=brand_dna, dry_run=True, audit_log=log
    )
    agent.execute(
        {"type": "categorize_expense", "request_text": "税務調査の立会いをお願い"}
    )
    entry = log.entries[0]
    assert entry["boundary_verdict"] == "escalate_to_zeirishi"
    assert entry["escalation_level"] == 3


def test_audit_log_writes_jsonl(tmp_path, brand_dna) -> None:
    path = tmp_path / "audit" / "tax.jsonl"
    log = TaxAuditLog(path=path)
    agent = TaxAccountant(
        model="claude-sonnet-4-6", brand_dna=brand_dna, dry_run=True, audit_log=log
    )
    agent.execute({"type": "deadline_reminder", "today_month": 2, "today_day": 1})
    agent.execute({"type": "bookkeeping_summary", "expenses": []})

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["agent"] == "tax_accountant"
    assert first["task_type"] == "deadline_reminder"


def test_audit_entry_timestamp_injectable() -> None:
    log = TaxAuditLog()
    entry = TaxAuditEntry(
        agent="tax_accountant",
        task_type="estimate_income_tax",
        boundary_verdict="pass",
        escalation_level=0,
        disclaimer_attached=True,
        source_year="令和6年度税制",
    )
    saved = log.record(entry, timestamp="2026-07-03T10:00:00+00:00")
    assert saved["timestamp"] == "2026-07-03T10:00:00+00:00"
