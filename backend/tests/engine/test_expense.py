from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from app.engine.expense import (
    EvaluatedExpenseLine,
    ExpenseFlag,
    detect_split_claims,
    evaluate_expense_line,
    route_expense,
    validate_expense_claim,
)
from app.engine.models import (
    ApprovalRole,
    CountryCode,
    ExpenseCategory,
    ExpenseClaim,
    ExpenseLine,
    ExpensePolicy,
    FindingCode,
    ReceiptFileType,
)


def line(
    amount: str,
    *,
    category: ExpenseCategory = ExpenseCategory.MEALS,
    receipt_present: bool = True,
    receipt_hash: str | None = "a" * 64,
    currency: str = "USD",
    line_number: int = 1,
) -> ExpenseLine:
    return ExpenseLine(
        line_number=line_number,
        category=category,
        amount=Decimal(amount),
        currency=currency,
        receipt_present=receipt_present,
        receipt_id="RCT-2026-000001" if receipt_present else None,
        receipt_hash=receipt_hash if receipt_present else None,
        file_type=ReceiptFileType.PDF if receipt_present else None,
        size_kb=Decimal("100") if receipt_present else None,
    )


def policy_with_limit(limit: str, threshold: str = "25") -> ExpensePolicy:
    return ExpensePolicy(
        "XPO-0001",
        ExpenseCategory.MEALS,
        CountryCode.US,
        Decimal(limit),
        Decimal(threshold),
        date(2026, 1, 1),
    )


def claim_for(employee, lines: tuple[ExpenseLine, ...], **changes) -> ExpenseClaim:
    base = ExpenseClaim(
        expense_claim_id="EXP-2026-000001",
        employee=employee,
        merchant_name="Northstar Cafe",
        merchant_country=CountryCode.US,
        expense_date=date(2026, 10, 15),
        cost_center_id="CC-0001",
        lines=lines,
    )
    return replace(base, **changes)


@pytest.mark.parametrize(
    ("amount", "expected_flag", "hard_reject"),
    [
        ("100.00", False, False),
        ("100.01", True, False),
        ("150.00", True, False),
        ("150.01", True, True),
    ],
)
def test_policy_limit_and_exact_150_percent_boundary(
    employee, amount, expected_flag, hard_reject
) -> None:
    policy = policy_with_limit("100")
    claim = claim_for(employee, (line(amount),))
    result = validate_expense_claim(claim, (policy,))
    assert result.value is not None
    has_breach = any(flag.code == FindingCode.POLICY_LIMIT_BREACH for flag in result.value.flags)
    assert has_breach is expected_flag
    assert result.value.hard_rejected is hard_reject
    if hard_reject:
        assert result.reason_codes == ("POLICY_LIMIT_BREACH",)
    elif amount == "150.00":
        assert any(
            flag.pct_over == Decimal("50.00")
            for flag in result.value.flags
            if flag.code == FindingCode.POLICY_LIMIT_BREACH
        )


def test_e2_amount_conversion_receipt_and_duplicate_hash(employee, expense_policy) -> None:
    original = line("50", receipt_hash="b" * 64)
    result = evaluate_expense_line(
        original, employee.country, date(2026, 10, 15), (expense_policy,)
    )
    assert result.ok and result.value is not None
    assert result.value.amount_usd == Decimal("50.00")
    assert result.value.fx_rate_to_usd == Decimal("1")
    duplicate = evaluate_expense_line(
        original,
        employee.country,
        date(2026, 10, 15),
        (expense_policy,),
        existing_receipt_hashes=frozenset({"b" * 64}),
    )
    assert duplicate.value is not None
    assert duplicate.value.flags[0].code == FindingCode.DUPLICATE_RECEIPT
    bad_metadata = evaluate_expense_line(
        replace(original, receipt_hash="BAD"),
        employee.country,
        date(2026, 10, 15),
        (expense_policy,),
    )
    assert not bad_metadata.ok
    assert "INVALID_RECEIPT_METADATA" in bad_metadata.reason_codes
    assert not evaluate_expense_line(
        original, employee.country, date(2025, 1, 1), (expense_policy,)
    ).ok
    invalid_policy = replace(expense_policy, per_line_limit_usd=Decimal("0"))
    assert not evaluate_expense_line(
        original, employee.country, date(2026, 10, 15), (invalid_policy,)
    ).ok


def test_missing_receipt_flag_and_total_rounded_per_line(employee, expense_policy) -> None:
    missing = replace(
        line("26", receipt_present=False, receipt_hash=None),
        receipt_present=False,
    )
    result = validate_expense_claim(claim_for(employee, (missing,)), (expense_policy,))
    assert result.ok and result.value is not None
    assert result.value.total_usd == Decimal("26.00")
    assert any(flag.code == FindingCode.MISSING_RECEIPT for flag in result.value.flags)
    two = (
        replace(line("0.005", line_number=1), category=ExpenseCategory.MEALS),
        replace(line("0.005", line_number=2), receipt_hash="c" * 64),
    )
    rounded = validate_expense_claim(claim_for(employee, two), (expense_policy,))
    assert rounded.value is not None
    assert rounded.value.total_usd == Decimal("0.02")


def test_duplicate_receipt_within_claim_and_hard_reject_codes(employee, expense_policy) -> None:
    first = line("20", line_number=1, receipt_hash="d" * 64)
    second = line("20", line_number=2, receipt_hash="d" * 64)
    claim = claim_for(employee, (first, second), cost_center_id=None)
    result = validate_expense_claim(claim, (expense_policy,))
    assert not result.ok and result.value is not None
    assert result.reason_codes == ("DUPLICATE_RECEIPT", "MISSING_COST_CENTER")
    assert (
        sum(
            flag.code == FindingCode.DUPLICATE_RECEIPT
            for line_result in result.value.lines
            for flag in line_result.flags
        )
        == 2
    )
    assert result.value.hard_rejected
    outside = claim_for(
        replace(employee, termination_date=date(2026, 10, 14)),
        (line("20"),),
        expense_date=date(2026, 10, 15),
        cost_center_id=None,
    )
    outside_result = validate_expense_claim(outside, (expense_policy,))
    assert outside_result.reason_codes == (
        "MISSING_COST_CENTER",
        "DATE_OUTSIDE_EMPLOYMENT",
    )
    future = claim_for(employee, (line("20"),), expense_date=date(2026, 10, 23))
    assert "FUTURE_EXPENSE_DATE" in validate_expense_claim(future, (expense_policy,)).reason_codes


@pytest.mark.parametrize(
    ("total", "expected_roles", "reason"),
    [
        ("49.99", (ApprovalRole.SYSTEM,), "EXPENSE_LT_50_AUTO"),
        ("50.00", (ApprovalRole.MANAGER,), "EXPENSE_50_1000"),
        ("999.99", (ApprovalRole.MANAGER,), "EXPENSE_50_1000"),
        ("1000.00", (ApprovalRole.MANAGER, ApprovalRole.DEPT_HEAD), "EXPENSE_1000_5000"),
        ("4999.99", (ApprovalRole.MANAGER, ApprovalRole.DEPT_HEAD), "EXPENSE_1000_5000"),
        (
            "5000.00",
            (ApprovalRole.MANAGER, ApprovalRole.DEPT_HEAD, ApprovalRole.FINANCE_CONTROLLER),
            "EXPENSE_5000_20000",
        ),
        (
            "19999.99",
            (ApprovalRole.MANAGER, ApprovalRole.DEPT_HEAD, ApprovalRole.FINANCE_CONTROLLER),
            "EXPENSE_5000_20000",
        ),
        (
            "20000.00",
            (
                ApprovalRole.MANAGER,
                ApprovalRole.DEPT_HEAD,
                ApprovalRole.FINANCE_CONTROLLER,
                ApprovalRole.CFO,
            ),
            "EXPENSE_GTE_20000",
        ),
    ],
)
def test_expense_base_approval_band_boundaries(total, expected_roles, reason) -> None:
    result = route_expense(Decimal(total), (), CountryCode.US, CountryCode.US)
    assert result.ok and result.value is not None
    assert tuple(step.approver_type for step in result.value) == expected_roles
    assert result.reason_codes[0] == reason


def test_under_50_flagged_claim_routes_manager_and_adds_exception_path() -> None:
    missing_receipt = ExpenseFlag(
        FindingCode.MISSING_RECEIPT,
        "E3",
        "MISSING_RECEIPT",
        "Receipt missing.",
    )
    result = route_expense(
        Decimal("49.99"),
        (),
        CountryCode.US,
        CountryCode.US,
        open_e3_flags=(missing_receipt,),
    )
    assert result.value is not None
    assert result.value[0].approver_type == ApprovalRole.MANAGER
    assert "EXPENSE_LT_50_FLAGGED" in result.reason_codes
    assert ApprovalRole.FINANCE_CONTROLLER in tuple(step.approver_type for step in result.value)


def test_additive_rules_are_ordered_and_deduplicated() -> None:
    evaluated = (
        EvaluatedExpenseLine(
            1,
            ExpenseCategory.AIRFARE,
            Decimal("300"),
            "USD",
            Decimal("300"),
            Decimal("1"),
            Decimal("2000"),
            Decimal(0),
            (),
        ),
        EvaluatedExpenseLine(
            2,
            ExpenseCategory.GIFTS,
            Decimal("300"),
            "USD",
            Decimal("300"),
            Decimal("1"),
            Decimal("500"),
            Decimal("25"),
            (),
        ),
    )
    result = route_expense(
        Decimal("50"),
        evaluated,
        CountryCode.US,
        CountryCode.GB,
    )
    assert result.value is not None
    roles = tuple(step.approver_type for step in result.value)
    assert roles == (
        ApprovalRole.MANAGER,
        ApprovalRole.FINANCE_CONTROLLER,
        ApprovalRole.COMPLIANCE_OFFICER,
    )
    assert all(step.rule_ids for step in result.value)


def test_exception_routes_include_each_e6_rule_and_reason() -> None:
    lines = (
        EvaluatedExpenseLine(
            1,
            ExpenseCategory.AIRFARE,
            Decimal("250"),
            "USD",
            Decimal("250"),
            Decimal("1"),
            Decimal("2000"),
            Decimal(0),
            (),
        ),
        EvaluatedExpenseLine(
            2,
            ExpenseCategory.CLIENT_ENTERTAINMENT,
            Decimal("251"),
            "USD",
            Decimal("251"),
            Decimal("1"),
            Decimal("1000"),
            Decimal("25"),
            (),
        ),
        EvaluatedExpenseLine(
            3,
            ExpenseCategory.GIFTS,
            Decimal("251"),
            "USD",
            Decimal("251"),
            Decimal("1"),
            Decimal("500"),
            Decimal("25"),
            (),
        ),
        EvaluatedExpenseLine(
            4,
            ExpenseCategory.MEALS,
            Decimal("101"),
            "USD",
            Decimal("101"),
            Decimal("1"),
            Decimal("100"),
            Decimal("25"),
            (),
        ),
    )
    flags = (
        ExpenseFlag(
            FindingCode.POLICY_LIMIT_BREACH,
            "E3",
            "POLICY_LIMIT_BREACH",
            "Line exceeds policy.",
        ),
        ExpenseFlag(
            FindingCode.MISSING_RECEIPT,
            "E3",
            "MISSING_RECEIPT",
            "Receipt missing.",
        ),
    )
    result = route_expense(
        Decimal("853"),
        lines,
        CountryCode.US,
        CountryCode.GB,
        open_e3_flags=flags,
    )
    assert result.value is not None
    roles = tuple(step.approver_type for step in result.value)
    assert roles == (
        ApprovalRole.MANAGER,
        ApprovalRole.FINANCE_CONTROLLER,
        ApprovalRole.COMPLIANCE_OFFICER,
    )
    codes = {code for step in result.value for code in step.reason_codes}
    assert {
        "AIRFARE_INTERNATIONAL",
        "CLIENT_ENTERTAINMENT_GT_250",
        "GIFT_GT_250",
        "POLICY_LIMIT_BREACH",
        "MISSING_RECEIPT",
    }.issubset(codes)
    controller = result.value[1]
    assert "E6" in controller.rule_ids
    compliance = result.value[2]
    assert "E6" in compliance.rule_ids


def test_split_claim_detection_uses_normalized_merchant_shared_category_and_boundary(
    employee,
) -> None:
    first = claim_for(employee, (line("950"),), expense_claim_id="EXP-2026-000001")
    second = claim_for(
        employee,
        (line("950", line_number=1, receipt_hash="e" * 64),),
        expense_claim_id="EXP-2026-000002",
        merchant_name="  NORTHSTAR CAFE ",
        expense_date=date(2026, 10, 18),
    )
    pair_result = detect_split_claims(
        (second, first),
        {
            "EXP-2026-000001": Decimal("950"),
            "EXP-2026-000002": Decimal("950"),
        },
    )
    assert pair_result.ok and pair_result.value is not None
    assert pair_result.value[0].boundary_usd == Decimal("1000")
    assert not detect_split_claims(
        (first, second),
        {"EXP-2026-000001": Decimal("950")},
    ).ok
    far = replace(second, expense_date=date(2026, 10, 19))
    assert (
        detect_split_claims(
            (first, far),
            {"EXP-2026-000001": Decimal("950"), "EXP-2026-000002": Decimal("950")},
        ).value
        == ()
    )
    different_employee = replace(second, employee=replace(employee, employee_id="EMP-000003"))
    assert (
        detect_split_claims(
            (first, different_employee),
            {"EXP-2026-000001": Decimal("950"), "EXP-2026-000002": Decimal("950")},
        ).value
        == ()
    )
