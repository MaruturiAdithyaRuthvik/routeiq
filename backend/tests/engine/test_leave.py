from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from app.engine.leave import (
    LEAVE_POLICIES,
    LeaveRequestInput,
    balance_from_ledger,
    generate_leave_ledger_entries,
    leave_ledger_entries_for_transition,
    route_leave,
    validate_leave_request,
)
from app.engine.models import (
    ApprovalRole,
    ExistingLeaveRequest,
    LeaveEffectBucket,
    LeaveLedgerEntry,
    LeaveLedgerEntryType,
    LeavePolicy,
    LeaveStatus,
)


@pytest.mark.parametrize(
    ("hire_date", "expected_accruals"),
    [
        (date(2026, 1, 15), 9),
        (date(2026, 1, 16), 8),
    ],
)
def test_hire_month_cutoff(employee, annual_policy, hire_date, expected_accruals) -> None:
    employee = replace(employee, hire_date=hire_date)
    result = generate_leave_ledger_entries(
        employee,
        annual_policy,
        Decimal("0"),
        as_of_date=date(2026, 10, 22),
    )
    assert result.ok and result.value is not None
    accruals = [entry for entry in result.value if entry.entry_type == LeaveLedgerEntryType.ACCRUAL]
    assert len(accruals) == expected_accruals
    assert sum((entry.delta_days for entry in accruals), Decimal(0)) == Decimal(
        "18" if expected_accruals == 9 else "16"
    )


def test_month_end_accrual_and_year_end_remainder(employee, annual_policy) -> None:
    result = generate_leave_ledger_entries(
        employee,
        annual_policy,
        Decimal("12"),
        as_of_date=date(2026, 12, 31),
    )
    assert result.ok and result.value is not None
    assert result.value[0].entry_type == LeaveLedgerEntryType.OPENING
    assert result.value[0].delta_days == Decimal("10")
    accruals = [entry for entry in result.value if entry.entry_type == LeaveLedgerEntryType.ACCRUAL]
    assert len(accruals) == 12
    assert sum((entry.delta_days for entry in accruals), Decimal(0)) == Decimal("24")
    assert accruals[-1].delta_days == Decimal("2.000000")


def test_accrual_stops_after_termination_and_unpaid_has_no_ledger(employee, annual_policy) -> None:
    terminated = replace(employee, hire_date=date(2020, 1, 1), termination_date=date(2026, 6, 15))
    result = generate_leave_ledger_entries(
        terminated, annual_policy, Decimal("0"), as_of_date=date(2026, 12, 31)
    )
    assert result.value is not None
    assert all(entry.entry_date <= date(2026, 5, 31) for entry in result.value[1:])
    unpaid = LeavePolicy("LPO-006", "Unpaid", None, Decimal(0), 30, None, 0, Decimal(0), True)
    assert generate_leave_ledger_entries(employee, unpaid, Decimal(0)).value == ()
    assert not generate_leave_ledger_entries(employee, annual_policy, Decimal("-1")).ok
    assert not generate_leave_ledger_entries(
        employee, annual_policy, Decimal(0), balance_year=2025
    ).ok
    assert not generate_leave_ledger_entries(
        employee, annual_policy, Decimal(0), first_sequence=0
    ).ok


def test_six_l1_leave_policies_are_explicit() -> None:
    assert tuple(LEAVE_POLICIES) == tuple(f"LPO-{number:03d}" for number in range(1, 7))
    assert LEAVE_POLICIES["LPO-001"].annual_entitlement_days == Decimal("24")
    assert LEAVE_POLICIES["LPO-002"].medical_certificate_after_days == 2
    assert LEAVE_POLICIES["LPO-003"].max_consecutive_days == 3
    assert LEAVE_POLICIES["LPO-004"].tenure_required_months == 12
    assert LEAVE_POLICIES["LPO-005"].lump_sum_days == Decimal("5")
    assert LEAVE_POLICIES["LPO-006"].is_unpaid


def test_lump_sum_tenure_exactly_12_months(employee) -> None:
    parental = LeavePolicy("LPO-004", "Parental", None, Decimal(0), None, None, 12, Decimal("90"))
    employee = replace(employee, hire_date=date(2025, 10, 22))
    before = generate_leave_ledger_entries(
        employee, parental, Decimal(0), as_of_date=date(2026, 10, 21)
    )
    exact = generate_leave_ledger_entries(
        employee, parental, Decimal(0), as_of_date=date(2026, 10, 22)
    )
    assert before.value is not None and len(before.value) == 1
    assert exact.value is not None and len(exact.value) == 2
    assert exact.value[-1].entry_date == date(2026, 10, 22)
    assert exact.value[-1].delta_days == Decimal("90")


def test_parental_request_is_eligible_on_exact_12_month_anniversary(employee) -> None:
    parental = LeavePolicy("LPO-004", "Parental", None, Decimal(0), None, None, 12, Decimal("90"))
    employee = replace(employee, hire_date=date(2025, 11, 23))
    result = validate_leave_request(
        LeaveRequestInput(
            employee,
            parental,
            date(2026, 11, 23),
            date(2026, 11, 23),
            Decimal("90"),
        )
    )
    assert result.ok and result.value is not None
    assert result.value.balance_after == Decimal("89")


def test_ledger_balance_applies_releases_debits_adjustments_and_reversals(annual_policy) -> None:
    entries = (
        LeaveLedgerEntry(
            "LLE-2026-000001",
            "EMP-000001",
            "LPO-001",
            LeaveLedgerEntryType.OPENING,
            LeaveEffectBucket.AVAILABLE,
            Decimal("10"),
            date(2026, 1, 1),
        ),
        LeaveLedgerEntry(
            "LLE-2026-000002",
            "EMP-000001",
            "LPO-001",
            LeaveLedgerEntryType.ACCRUAL,
            LeaveEffectBucket.AVAILABLE,
            Decimal("5"),
            date(2026, 1, 31),
        ),
        LeaveLedgerEntry(
            "LLE-2026-000003",
            "EMP-000001",
            "LPO-001",
            LeaveLedgerEntryType.RESERVE,
            LeaveEffectBucket.RESERVED,
            Decimal("3"),
            date(2026, 2, 1),
        ),
        LeaveLedgerEntry(
            "LLE-2026-000004",
            "EMP-000001",
            "LPO-001",
            LeaveLedgerEntryType.RELEASE,
            LeaveEffectBucket.RESERVED,
            Decimal("-1"),
            date(2026, 2, 2),
        ),
        LeaveLedgerEntry(
            "LLE-2026-000005",
            "EMP-000001",
            "LPO-001",
            LeaveLedgerEntryType.DEBIT,
            LeaveEffectBucket.USED,
            Decimal("2"),
            date(2026, 2, 3),
        ),
        LeaveLedgerEntry(
            "LLE-2026-000006",
            "EMP-000001",
            "LPO-001",
            LeaveLedgerEntryType.ADJUSTMENT,
            LeaveEffectBucket.AVAILABLE,
            Decimal("-1"),
            date(2026, 2, 4),
        ),
        LeaveLedgerEntry(
            "LLE-2026-000007",
            "EMP-000001",
            "LPO-001",
            LeaveLedgerEntryType.REVERSAL,
            LeaveEffectBucket.AVAILABLE,
            Decimal("1"),
            date(2026, 2, 5),
        ),
    )
    assert balance_from_ledger(entries, policy_id=annual_policy.leave_policy_id).value == Decimal(
        "11.000000"
    )


def test_leave_validation_balance_equal_to_request_is_valid(employee, annual_policy) -> None:
    result = validate_leave_request(
        LeaveRequestInput(
            employee,
            annual_policy,
            date(2026, 11, 23),
            date(2026, 11, 25),
            Decimal("3"),
        )
    )
    assert result.ok and result.value is not None
    assert result.value.business_days == 3
    assert result.value.balance_after == Decimal("0")
    assert not validate_leave_request(
        LeaveRequestInput(
            employee,
            annual_policy,
            date(2026, 11, 23),
            date(2026, 11, 25),
            Decimal("2.99"),
        )
    ).ok


@pytest.mark.parametrize(
    ("request_factory", "expected_code"),
    [
        (
            lambda e, p: LeaveRequestInput(
                e, p, date(2026, 11, 25), date(2026, 11, 24), Decimal(10)
            ),
            "INVALID_DATE_RANGE",
        ),
        (
            lambda e, p: LeaveRequestInput(
                e, p, date(2026, 10, 24), date(2026, 10, 25), Decimal(10)
            ),
            "ZERO_BUSINESS_DAYS",
        ),
        (
            lambda e, p: LeaveRequestInput(
                replace(e, hire_date=date(2026, 11, 24)),
                p,
                date(2026, 11, 23),
                date(2026, 11, 24),
                Decimal(10),
            ),
            "EMPLOYEE_NOT_ACTIVE",
        ),
        (
            lambda e, p: LeaveRequestInput(
                replace(e, hire_date=date(2025, 11, 24)),
                replace(p, tenure_required_months=12),
                date(2026, 11, 23),
                date(2026, 11, 24),
                Decimal(10),
            ),
            "TENURE_INELIGIBLE",
        ),
        (
            lambda e, p: LeaveRequestInput(
                e,
                replace(p, max_consecutive_days=2),
                date(2026, 11, 23),
                date(2026, 11, 25),
                Decimal(10),
            ),
            "MAX_CONSECUTIVE_DAYS",
        ),
        (
            lambda e, p: LeaveRequestInput(
                e,
                p,
                date(2026, 11, 23),
                date(2026, 11, 24),
                Decimal(10),
                (
                    ExistingLeaveRequest(
                        "EMP-000001", date(2026, 11, 24), date(2026, 11, 26), LeaveStatus.APPROVED
                    ),
                ),
            ),
            "OVERLAP",
        ),
        (
            lambda e, p: LeaveRequestInput(
                e, p, date(2026, 11, 23), date(2026, 11, 24), Decimal(1)
            ),
            "INSUFFICIENT_BALANCE",
        ),
    ],
)
def test_leave_validation_stops_at_first_l4_failure(
    employee, annual_policy, request_factory, expected_code
) -> None:
    result = validate_leave_request(request_factory(employee, annual_policy))
    assert not result.ok
    assert result.reason_codes == (expected_code,)
    assert result.rule_ids == ("L4",)


@pytest.mark.parametrize(
    ("policy_id", "unpaid", "days", "expected_roles", "reason"),
    [
        ("LPO-001", False, 3, (ApprovalRole.MANAGER,), "LEAVE_DAYS_1_3"),
        ("LPO-001", False, 4, (ApprovalRole.MANAGER, ApprovalRole.HR_PARTNER), "LEAVE_DAYS_4_10"),
        ("LPO-001", False, 10, (ApprovalRole.MANAGER, ApprovalRole.HR_PARTNER), "LEAVE_DAYS_4_10"),
        (
            "LPO-001",
            False,
            11,
            (ApprovalRole.MANAGER, ApprovalRole.HR_PARTNER, ApprovalRole.DEPT_HEAD),
            "LEAVE_DAYS_GT_10",
        ),
        (
            "LPO-004",
            False,
            1,
            (ApprovalRole.MANAGER, ApprovalRole.HR_PARTNER, ApprovalRole.DEPT_HEAD),
            "PARENTAL_LEAVE",
        ),
        ("LPO-006", True, 1, (ApprovalRole.MANAGER, ApprovalRole.HR_PARTNER), "LEAVE_UNPAID"),
    ],
)
def test_leave_routing_boundaries(
    annual_policy, policy_id, unpaid, days, expected_roles, reason
) -> None:
    policy = replace(annual_policy, leave_policy_id=policy_id, is_unpaid=unpaid)
    result = route_leave(policy, days)
    assert result.ok and result.value is not None
    assert tuple(step.approver_type for step in result.value) == expected_roles
    assert result.reason_codes == (reason,)
    assert all("L5" in step.rule_ids and "AU3" in step.rule_ids for step in result.value)


def test_medical_certificate_uses_calendar_days(employee) -> None:
    sick = LeavePolicy("LPO-002", "Sick", Decimal("12"), Decimal(0), 15, 2, 0, None)
    result = validate_leave_request(
        LeaveRequestInput(employee, sick, date(2026, 11, 23), date(2026, 11, 25), Decimal("3"))
    )
    assert result.value is not None and result.value.medical_certificate_required


@pytest.mark.parametrize(
    ("status", "types", "deltas"),
    [
        (LeaveStatus.SUBMITTED, (LeaveLedgerEntryType.RESERVE,), (Decimal("3"),)),
        (
            LeaveStatus.APPROVED,
            (LeaveLedgerEntryType.RELEASE, LeaveLedgerEntryType.DEBIT),
            (Decimal("-3"), Decimal("3")),
        ),
        (LeaveStatus.REJECTED, (LeaveLedgerEntryType.RELEASE,), (Decimal("-3"),)),
        (LeaveStatus.CANCELLED, (LeaveLedgerEntryType.RELEASE,), (Decimal("-3"),)),
    ],
)
def test_leave_l6_ledger_effects(employee, annual_policy, status, types, deltas) -> None:
    result = leave_ledger_entries_for_transition(
        employee_id=employee.employee_id,
        policy=annual_policy,
        leave_request_id="LVE-2026-000001",
        requested_days=Decimal("3"),
        target_status=status,
        entry_date=date(2026, 10, 22),
        first_sequence=10,
    )
    assert result.ok and result.value is not None
    assert tuple(entry.entry_type for entry in result.value) == types
    assert tuple(entry.delta_days for entry in result.value) == deltas
    assert all(entry.leave_request_id == "LVE-2026-000001" for entry in result.value)


def test_unpaid_ledger_markers_are_zero_and_invalid_l6_inputs_fail(employee) -> None:
    unpaid = LEAVE_POLICIES["LPO-006"]
    result = leave_ledger_entries_for_transition(
        employee_id=employee.employee_id,
        policy=unpaid,
        leave_request_id="LVE-2026-000001",
        requested_days=Decimal("3"),
        target_status=LeaveStatus.APPROVED,
        entry_date=date(2026, 10, 22),
        first_sequence=1,
    )
    assert result.value is not None
    assert tuple(entry.delta_days for entry in result.value) == (Decimal(0), Decimal(0))
    assert not leave_ledger_entries_for_transition(
        employee_id="bad",
        policy=unpaid,
        leave_request_id="LVE-2026-000001",
        requested_days=Decimal("3"),
        target_status=LeaveStatus.SUBMITTED,
        entry_date=date(2026, 10, 22),
        first_sequence=1,
    ).ok
    assert not leave_ledger_entries_for_transition(
        employee_id=employee.employee_id,
        policy=unpaid,
        leave_request_id="LVE-2026-000001",
        requested_days=Decimal("3"),
        target_status=LeaveStatus.DRAFT,
        entry_date=date(2026, 10, 22),
        first_sequence=1,
    ).ok
