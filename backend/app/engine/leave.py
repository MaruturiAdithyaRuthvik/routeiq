"""Leave accrual, validation, and routing rules (L1-L7, G3-G5, AU3)."""

from __future__ import annotations

import calendar as month_calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from types import MappingProxyType
from typing import Final

from .calendar import AS_OF_DATE, ExcludedDate, business_days_between
from .ids import IdKind, format_id, validate_id
from .models import (
    ApprovalPathStep,
    ApprovalRole,
    Employee,
    ExistingLeaveRequest,
    LeaveEffectBucket,
    LeaveLedgerEntry,
    LeaveLedgerEntryType,
    LeavePolicy,
    LeaveStatus,
)
from .money import round_half_up
from .results import RuleResult, failure, success

_ZERO: Final = Decimal("0")
_ACTIVE_OVERLAP_STATUSES: Final = {
    LeaveStatus.SUBMITTED,
    LeaveStatus.PENDING_APPROVAL,
    LeaveStatus.APPROVED,
}

LEAVE_POLICIES: Final = MappingProxyType(
    {
        "LPO-001": LeavePolicy(
            "LPO-001", "Annual", Decimal("24"), Decimal("10"), 20, None, 0, None
        ),
        "LPO-002": LeavePolicy("LPO-002", "Sick", Decimal("12"), Decimal("0"), 15, 2, 0, None),
        "LPO-003": LeavePolicy("LPO-003", "Casual", Decimal("8"), Decimal("0"), 3, None, 0, None),
        "LPO-004": LeavePolicy(
            "LPO-004", "Parental", None, Decimal("0"), None, None, 12, Decimal("90")
        ),
        "LPO-005": LeavePolicy(
            "LPO-005", "Compassionate", None, Decimal("0"), 5, None, 0, Decimal("5")
        ),
        "LPO-006": LeavePolicy(
            "LPO-006", "Unpaid", None, Decimal("0"), 30, None, 0, Decimal("0"), True
        ),
    }
)


@dataclass(frozen=True, slots=True)
class LeaveRequestInput:
    employee: Employee
    policy: LeavePolicy
    start_date: date
    end_date: date
    available_days: Decimal
    existing_requests: tuple[ExistingLeaveRequest, ...] = ()


@dataclass(frozen=True, slots=True)
class LeaveValidation:
    business_days: int
    calendar_days: int
    excluded_dates: tuple[ExcludedDate, ...]
    balance_before: Decimal | None
    balance_after: Decimal | None
    medical_certificate_required: bool


def _month_end(year: int, month: int) -> date:
    """Return a calendar month end without consulting the system clock (L2)."""

    return date(year, month, month_calendar.monthrange(year, month)[1])


def _add_months(value: date, months: int) -> date:
    """Add calendar months, clamping to the target month's last day (L1, L2)."""

    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, month_calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _ledger_entry(
    *,
    sequence: int,
    employee: Employee,
    policy: LeavePolicy,
    entry_type: LeaveLedgerEntryType,
    effect_bucket: LeaveEffectBucket,
    delta_days: Decimal,
    entry_date: date,
    prior_year_closing_days: Decimal | None = None,
) -> LeaveLedgerEntry:
    identifier = format_id(IdKind.LEAVE_LEDGER_ENTRY, sequence)
    if identifier.value is None:
        raise ValueError(identifier.messages[0])
    return LeaveLedgerEntry(
        leave_ledger_entry_id=identifier.value,
        employee_id=employee.employee_id,
        leave_policy_id=policy.leave_policy_id,
        entry_type=entry_type,
        effect_bucket=effect_bucket,
        delta_days=delta_days,
        entry_date=entry_date,
        prior_year_closing_days=prior_year_closing_days,
    )


def generate_leave_ledger_entries(
    employee: Employee,
    policy: LeavePolicy,
    prior_year_closing_days: Decimal,
    *,
    balance_year: int = 2026,
    as_of_date: date = AS_OF_DATE,
    first_sequence: int = 1,
) -> RuleResult[tuple[LeaveLedgerEntry, ...]]:
    """Generate opening and earned ledger entries deterministically (L1-L3)."""

    if balance_year != 2026 or as_of_date.year != balance_year:
        return failure(
            reason_codes=("UNSUPPORTED_BALANCE_YEAR",),
            rule_ids=("L2", "D1"),
            message="This engine implements the fixed 2026 balance year only.",
        )
    if (
        isinstance(first_sequence, bool)
        or not isinstance(first_sequence, int)
        or first_sequence < 1
        or first_sequence > 999_987
    ):
        return failure(
            reason_codes=("INVALID_ID_SEQUENCE",),
            rule_ids=("G1", "D1"),
            message="First ledger sequence must be a positive integer.",
        )
    if not prior_year_closing_days.is_finite() or prior_year_closing_days < _ZERO:
        return failure(
            reason_codes=("INVALID_PRIOR_YEAR_CLOSING",),
            rule_ids=("L2",),
            message="Prior-year closing days must be a finite non-negative Decimal.",
        )

    entries: list[LeaveLedgerEntry] = []
    sequence = first_sequence
    if not policy.is_unpaid:
        opening = min(prior_year_closing_days, policy.carry_forward_max_days)
        opening_entry = _ledger_entry(
            sequence=sequence,
            employee=employee,
            policy=policy,
            entry_type=LeaveLedgerEntryType.OPENING,
            effect_bucket=LeaveEffectBucket.AVAILABLE,
            delta_days=opening,
            prior_year_closing_days=prior_year_closing_days,
            entry_date=date(balance_year, 1, 1),
        )
        entries.append(opening_entry)
        sequence += 1

        if policy.annual_entitlement_days is not None:
            monthly = round_half_up(policy.annual_entitlement_days / Decimal(12), 6)
            if monthly.value is None:
                return failure(
                    reason_codes=monthly.reason_codes,
                    rule_ids=monthly.rule_ids,
                    message=monthly.messages[0],
                )
            yearly_credited = _ZERO
            for month in range(1, 13):
                last_day = _month_end(balance_year, month)
                if last_day > as_of_date:
                    break
                if employee.hire_date > last_day:
                    continue
                if employee.termination_date is not None and employee.termination_date < last_day:
                    continue
                if month == employee.hire_date.month and employee.hire_date.day > 15:
                    continue
                amount = monthly.value
                if month == 12:
                    amount = policy.annual_entitlement_days - yearly_credited
                yearly_credited += amount
                entries.append(
                    _ledger_entry(
                        sequence=sequence,
                        employee=employee,
                        policy=policy,
                        entry_type=LeaveLedgerEntryType.ACCRUAL,
                        effect_bucket=LeaveEffectBucket.AVAILABLE,
                        delta_days=amount,
                        entry_date=last_day,
                    )
                )
                sequence += 1
        elif policy.lump_sum_days is not None and policy.lump_sum_days > _ZERO:
            eligible_date = date(balance_year, 1, 1)
            if policy.tenure_required_months:
                tenure_date = _add_months(employee.hire_date, policy.tenure_required_months)
                eligible_date = max(eligible_date, tenure_date)
            if employee.hire_date > eligible_date:
                eligible_date = employee.hire_date
            if eligible_date <= as_of_date and (
                employee.termination_date is None or eligible_date <= employee.termination_date
            ):
                entries.append(
                    _ledger_entry(
                        sequence=sequence,
                        employee=employee,
                        policy=policy,
                        entry_type=LeaveLedgerEntryType.ACCRUAL,
                        effect_bucket=LeaveEffectBucket.AVAILABLE,
                        delta_days=policy.lump_sum_days,
                        entry_date=eligible_date,
                    )
                )

    return success(
        tuple(entries),
        reason_codes=("LEAVE_LEDGER_GENERATED",),
        rule_ids=("L1", "L2", "L3"),
        message=f"Generated {len(entries)} deterministic leave ledger entry(ies).",
    )


def balance_from_ledger(
    entries: tuple[LeaveLedgerEntry, ...], *, policy_id: str | None = None
) -> RuleResult[Decimal]:
    """Derive available days from opening, accrual, adjustments, used, and pending entries (L3)."""

    opening = _ZERO
    accrued = _ZERO
    adjustments = _ZERO
    used = _ZERO
    pending = _ZERO
    for entry in entries:
        if policy_id is not None and entry.leave_policy_id != policy_id:
            continue
        if entry.entry_type == LeaveLedgerEntryType.OPENING:
            opening += entry.delta_days
        elif entry.entry_type == LeaveLedgerEntryType.ACCRUAL:
            accrued += entry.delta_days
        elif entry.entry_type == LeaveLedgerEntryType.ADJUSTMENT or (
            entry.entry_type == LeaveLedgerEntryType.REVERSAL
            and entry.effect_bucket == LeaveEffectBucket.AVAILABLE
        ):
            adjustments += entry.delta_days
        elif entry.entry_type == LeaveLedgerEntryType.DEBIT or (
            entry.entry_type == LeaveLedgerEntryType.REVERSAL
            and entry.effect_bucket == LeaveEffectBucket.USED
        ):
            used += entry.delta_days
        elif entry.entry_type in (LeaveLedgerEntryType.RESERVE, LeaveLedgerEntryType.RELEASE) or (
            entry.entry_type == LeaveLedgerEntryType.REVERSAL
            and entry.effect_bucket == LeaveEffectBucket.RESERVED
        ):
            pending += entry.delta_days
    available = round_half_up(opening + accrued + adjustments - used - pending, 6)
    if available.value is None:
        return failure(
            reason_codes=available.reason_codes,
            rule_ids=("L3",),
            message=available.messages[0],
        )
    return success(
        available.value,
        reason_codes=("LEAVE_BALANCE_DERIVED",),
        rule_ids=("L3",),
        message="Derived available leave days from ledger entries.",
    )


def leave_ledger_entries_for_transition(
    *,
    employee_id: str,
    policy: LeavePolicy,
    leave_request_id: str,
    requested_days: Decimal,
    target_status: LeaveStatus,
    entry_date: date,
    first_sequence: int,
) -> RuleResult[tuple[LeaveLedgerEntry, ...]]:
    """Create append-only L6 RESERVE, RELEASE, and DEBIT ledger rows."""

    valid_employee = validate_id(employee_id, IdKind.EMPLOYEE)
    valid_request = validate_id(leave_request_id, IdKind.LEAVE_REQUEST)
    if not valid_employee.ok or not valid_request.ok:
        return failure(
            reason_codes=("INVALID_LEDGER_REFERENCE",),
            rule_ids=("G1", "L6"),
            message="Ledger entries require valid employee and leave-request IDs.",
        )
    if not requested_days.is_finite() or requested_days <= _ZERO:
        return failure(
            reason_codes=("INVALID_LEAVE_DAYS",),
            rule_ids=("L3", "L6"),
            message="Requested leave days must be a positive finite Decimal.",
        )
    actions: tuple[tuple[LeaveLedgerEntryType, LeaveEffectBucket, Decimal], ...]
    if target_status == LeaveStatus.SUBMITTED:
        actions = ((LeaveLedgerEntryType.RESERVE, LeaveEffectBucket.RESERVED, requested_days),)
    elif target_status == LeaveStatus.APPROVED:
        actions = (
            (LeaveLedgerEntryType.RELEASE, LeaveEffectBucket.RESERVED, -requested_days),
            (LeaveLedgerEntryType.DEBIT, LeaveEffectBucket.USED, requested_days),
        )
    elif target_status in (LeaveStatus.REJECTED, LeaveStatus.CANCELLED):
        actions = ((LeaveLedgerEntryType.RELEASE, LeaveEffectBucket.RESERVED, -requested_days),)
    else:
        return failure(
            reason_codes=("INVALID_LEDGER_TRANSITION",),
            rule_ids=("L6", "L7"),
            message=(
                "Leave ledger effects are defined only for submit, approval, rejection, "
                "or cancellation."
            ),
        )
    if (
        isinstance(first_sequence, bool)
        or not isinstance(first_sequence, int)
        or first_sequence < 1
        or first_sequence + len(actions) - 1 > 999_999
    ):
        return failure(
            reason_codes=("INVALID_ID_SEQUENCE",),
            rule_ids=("G1", "D1"),
            message="Ledger entry sequence exceeds its supported ID range.",
        )
    if policy.is_unpaid:
        actions = tuple((entry_type, bucket, _ZERO) for entry_type, bucket, _ in actions)
    entries_list: list[LeaveLedgerEntry] = []
    for offset, (entry_type, bucket, delta) in enumerate(actions):
        identifier = format_id(IdKind.LEAVE_LEDGER_ENTRY, first_sequence + offset)
        if identifier.value is None:
            return failure(
                reason_codes=identifier.reason_codes,
                rule_ids=identifier.rule_ids,
                message=identifier.messages[0],
            )
        entries_list.append(
            LeaveLedgerEntry(
                leave_ledger_entry_id=identifier.value,
                employee_id=employee_id,
                leave_policy_id=policy.leave_policy_id,
                leave_request_id=leave_request_id,
                entry_type=entry_type,
                effect_bucket=bucket,
                delta_days=delta,
                entry_date=entry_date,
            )
        )
    entries = tuple(entries_list)
    return success(
        entries,
        reason_codes=("LEAVE_LEDGER_TRANSITION_RECORDED",),
        rule_ids=("L3", "L6", "L7"),
        message=f"Created {len(entries)} append-only leave ledger transition entry(ies).",
    )


def validate_leave_request(request: LeaveRequestInput) -> RuleResult[LeaveValidation]:
    """Validate leave in the exact first-failure order prescribed by L4."""

    employee = request.employee
    policy = request.policy
    start = request.start_date
    end = request.end_date
    if end < start:
        return failure(
            reason_codes=("INVALID_DATE_RANGE",),
            rule_ids=("L4",),
            message="End date must be on or after start date.",
        )

    counted = business_days_between(start, end, employee.country)
    if counted.value is None:
        return failure(
            reason_codes=counted.reason_codes,
            rule_ids=counted.rule_ids,
            message=counted.messages[0],
        )
    day_count = counted.value
    calendar_days = (end - start).days + 1
    base = LeaveValidation(
        business_days=day_count.count,
        calendar_days=calendar_days,
        excluded_dates=day_count.excluded_dates,
        balance_before=None if policy.is_unpaid else request.available_days,
        balance_after=None
        if policy.is_unpaid
        else request.available_days - Decimal(day_count.count),
        medical_certificate_required=(
            policy.medical_certificate_after_days is not None
            and calendar_days > policy.medical_certificate_after_days
        ),
    )

    def reject(code: str, message: str) -> RuleResult[LeaveValidation]:
        return failure(reason_codes=(code,), rule_ids=("L4",), message=message, value=base)

    if day_count.count == 0:
        return reject("ZERO_BUSINESS_DAYS", "Leave range contains no business days.")

    if start < employee.hire_date or (
        employee.termination_date is not None and end > employee.termination_date
    ):
        return reject("EMPLOYEE_NOT_ACTIVE", "Employee is not active for the full leave range.")

    tenure_date = _add_months(employee.hire_date, policy.tenure_required_months)
    if start < tenure_date:
        return reject("TENURE_INELIGIBLE", "Employee does not meet the policy tenure requirement.")

    if policy.max_consecutive_days is not None and calendar_days > policy.max_consecutive_days:
        return reject("MAX_CONSECUTIVE_DAYS", "Leave exceeds the policy's calendar-day maximum.")

    overlaps = any(
        current.employee_id == employee.employee_id
        and current.status in _ACTIVE_OVERLAP_STATUSES
        and start <= current.end_date
        and current.start_date <= end
        for current in request.existing_requests
    )
    if overlaps:
        return reject("OVERLAP", "Leave overlaps an active request for this employee.")

    if not policy.is_unpaid and request.available_days < Decimal(day_count.count):
        return reject(
            "INSUFFICIENT_BALANCE", "Available leave balance is below requested business days."
        )

    return success(
        base,
        reason_codes=("LEAVE_REQUEST_VALID",),
        rule_ids=("L4",),
        message="Leave request passes all submit-time validations.",
    )


def route_leave(
    policy: LeavePolicy, business_days: int
) -> RuleResult[tuple[ApprovalPathStep, ...]]:
    """Derive sequential leave approver types and AU3 routing reasons (L5, AU3)."""

    if isinstance(business_days, bool) or business_days < 0:
        return failure(
            reason_codes=("INVALID_BUSINESS_DAY_COUNT",),
            rule_ids=("L5",),
            message="Business-day count must be a non-negative integer.",
        )
    if policy.is_unpaid:
        roles = (ApprovalRole.MANAGER, ApprovalRole.HR_PARTNER)
        reason_codes = ("LEAVE_UNPAID",)
    elif policy.leave_policy_id == "LPO-004":
        roles = (ApprovalRole.MANAGER, ApprovalRole.HR_PARTNER, ApprovalRole.DEPT_HEAD)
        reason_codes = ("PARENTAL_LEAVE",)
    elif business_days <= 3:
        roles = (ApprovalRole.MANAGER,)
        reason_codes = ("LEAVE_DAYS_1_3",)
    elif business_days <= 10:
        roles = (ApprovalRole.MANAGER, ApprovalRole.HR_PARTNER)
        reason_codes = ("LEAVE_DAYS_4_10",)
    else:
        roles = (ApprovalRole.MANAGER, ApprovalRole.HR_PARTNER, ApprovalRole.DEPT_HEAD)
        reason_codes = ("LEAVE_DAYS_GT_10",)
    reason = f"Leave routing matched {reason_codes[0]} for {business_days} business day(s)."
    path = tuple(
        ApprovalPathStep(
            level=index,
            approver_type=role,
            reason=reason,
            rule_ids=("L5", "AU3"),
            reason_codes=reason_codes,
        )
        for index, role in enumerate(roles, start=1)
    )
    return success(
        path,
        reason_codes=reason_codes,
        rule_ids=("L5", "AU3"),
        message=reason,
    )
