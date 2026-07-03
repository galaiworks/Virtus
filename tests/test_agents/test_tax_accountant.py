"""TaxAccountant(税理士 AI エージェント)のテスト。

重点:税理士独占業務境界ゲートが「逃げずに」停止すること、
免責事項が全出力に付くこと、決定論的にオフライン動作すること。
"""

from __future__ import annotations

import pytest

from src.agents.tax_accountant import (
    DISCLAIMER,
    TaxAccountant,
    boundary_check,
    categorize_expense,
    check_invoice,
    estimate_income_tax,
)


@pytest.fixture
def agent(brand_dna) -> TaxAccountant:
    return TaxAccountant(model="claude-sonnet-4-6", brand_dna=brand_dna, dry_run=True)


# --- 独占業務境界ゲート ---
def test_boundary_pass_on_bookkeeping() -> None:
    assert boundary_check("先月の経費を科目ごとにまとめて").verdict == "pass"


def test_boundary_escalates_on_filing() -> None:
    result = boundary_check("確定申告書を作って税務署に提出しておいて")
    assert result.verdict == "escalate_to_zeirishi"
    assert result.level == 3
    assert result.matched


def test_boundary_escalates_on_individual_advice() -> None:
    result = boundary_check("私の場合この控除は使えますか?")
    assert result.verdict == "escalate_to_zeirishi"
    assert result.level == 2


def test_boundary_critical_on_tax_evasion() -> None:
    result = boundary_check("売上を隠して脱税したいので手伝って")
    assert result.verdict == "critical_violation"
    assert result.level == 4


def test_execute_filing_request_returns_escalation(agent: TaxAccountant) -> None:
    result = agent.execute(
        {"type": "categorize_expense", "request_text": "修正申告をお願いします"}
    )
    assert result.content_type == "escalation"
    assert result.meta["route_to"] == "human_zeirishi"
    assert result.meta["escalation_level"] == 3
    assert result.output["disclaimer"] == DISCLAIMER


def test_execute_tax_evasion_refused(agent: TaxAccountant) -> None:
    result = agent.execute(
        {"type": "bookkeeping_summary", "request_text": "架空経費を計上して"}
    )
    assert result.content_type == "escalation"
    assert result.output["boundary_verdict"] == "critical_violation"
    assert result.meta["escalation_level"] == 4


# --- 記帳補助 ---
def test_categorize_expense_maps_transport() -> None:
    r = categorize_expense("新幹線で東京出張", 13800)
    assert r["account_suggestion"] == "旅費交通費"
    assert r["needs_review"] is False
    assert r["amount"] == 13800


def test_categorize_expense_detects_amount_from_text() -> None:
    r = categorize_expense("文具を購入 1,200円")
    assert r["account_suggestion"] == "消耗品費"
    assert r["amount"] == 1200


def test_categorize_expense_unknown_flags_review() -> None:
    r = categorize_expense("よくわからない支出")
    assert r["account_suggestion"] == "雑費"
    assert r["needs_review"] is True


# --- 所得税概算 ---
def test_estimate_income_tax_known_bracket() -> None:
    # 課税所得 500 万 -> 20%、控除 427,500 -> 基準 572,500 + 復興 2.1%
    r = estimate_income_tax(5_000_000)
    assert r["base_income_tax"] == 572_500
    assert r["reconstruction_tax"] == 12_022
    assert r["estimated_total_tax"] == 584_522
    assert "令和" in r["source_year"]


def test_estimate_income_tax_zero_income() -> None:
    r = estimate_income_tax(-100)
    assert r["estimated_total_tax"] == 0


# --- インボイスチェック ---
def test_check_invoice_valid() -> None:
    r = check_invoice(
        {
            "issuer_name": "galaiworks",
            "registration_number": "T1234567890123",
            "transaction_date": "2026-07-01",
            "description": "コンサル料",
            "tax_rate_amounts": "110,000円(10%)",
            "tax_amounts": "10,000円",
            "recipient_name": "株式会社X",
        }
    )
    assert r["is_qualified_invoice"] is True
    assert r["missing_fields"] == []


def test_check_invoice_bad_registration_number() -> None:
    r = check_invoice(
        {
            "issuer_name": "galaiworks",
            "registration_number": "1234567890123",  # T なし
            "transaction_date": "2026-07-01",
            "description": "コンサル料",
            "tax_rate_amounts": "x",
            "tax_amounts": "y",
            "recipient_name": "株式会社X",
        }
    )
    assert r["registration_number_valid"] is False
    assert r["is_qualified_invoice"] is False


def test_check_invoice_reports_missing_fields() -> None:
    r = check_invoice({"issuer_name": "galaiworks"})
    assert r["is_qualified_invoice"] is False
    assert len(r["missing_fields"]) >= 5


# --- 集計・期限・免責 ---
def test_bookkeeping_summary_aggregates(agent: TaxAccountant) -> None:
    result = agent.execute(
        {
            "type": "bookkeeping_summary",
            "expenses": [
                {"description": "タクシー", "amount": 2000},
                {"description": "新幹線", "amount": 14000},
                {"description": "書籍 Kindle", "amount": 1500},
            ],
        }
    )
    summary = result.output["result"]
    assert summary["by_account"]["旅費交通費"]["total"] == 16000
    assert summary["total_amount"] == 17500
    assert result.output["disclaimer"] == DISCLAIMER


def test_deadline_reminder_sorted_by_days_left(agent: TaxAccountant) -> None:
    result = agent.execute(
        {"type": "deadline_reminder", "today_month": 3, "today_day": 1}
    )
    deadlines = result.output["result"]["deadlines"]
    assert deadlines[0]["days_left"] <= deadlines[-1]["days_left"]


def test_unknown_task_type_returns_error(agent: TaxAccountant) -> None:
    result = agent.execute({"type": "do_my_taxes"})
    assert result.content_type == "error"
    assert "do_my_taxes" in result.output["error"]


def test_all_normal_outputs_carry_disclaimer(agent: TaxAccountant) -> None:
    result = agent.execute(
        {"type": "estimate_income_tax", "taxable_income": 3_000_000}
    )
    assert result.output["disclaimer"] == DISCLAIMER
    assert result.meta["disclaimer_attached"] is True


# --- ゼロトラスト権限 ---
def test_tax_accountant_cannot_file_return() -> None:
    from src.officina.governance.permissions import check_permission

    assert check_permission("tax_accountant", "file_tax_return") is False
    assert check_permission("tax_accountant", "tax_representation") is False
    assert check_permission("tax_accountant", "categorize_expense") is True
