"""Reimbursement eligibility and deterministic payment scheduling (E9, G3-G4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Final

from .calendar import AS_OF_DATE, add_business_days
from .models import (
    ApprovalStep,
    ApprovalStepStatus,
    AuditFindingStatus,
    Employee,
    ExpenseStatus,
    FindingCode,
    OpenFinding,
    ReimbursementStatus,
)
from .money import currency_for_country, to_home_currency
from .results import RuleResult, failure, success

_DUPLICATE_RELATED: Final = {
    FindingCode.DUPLICATE_RECEIPT,
    FindingCode.SPLIT_CLAIM,
    FindingCode.DUPLICATE_REIMBURSEMENT,
}


@dataclass(frozen=True, slots=True)
class ReimbursementEligibility:
    eligible: bool
    amount_home_currency: Decimal | None
    home_currency: str | None
    payment_date: date | None
    status: ReimbursementStatus | None
    reasons: tuple[str, ...]


def check_reimbursement_eligibility(
    *,
    employee: Employee,
    amount_usd: Decimal,
    claim_status: ExpenseStatus,
    approval_steps: tuple[ApprovalStep, ...],
    findings: tuple[OpenFinding, ...],
    cost_center_id: str | None,
    existing_reimbursement_ids: tuple[str, ...],
    final_approval_date: date,
    as_of_date: date = AS_OF_DATE,
) -> RuleResult[ReimbursementEligibility]:
    """Evaluate every E9 gate and derive home-currency amount/payment state."""

    reasons: list[str] = []
    if claim_status != ExpenseStatus.APPROVED:
        reasons.append("CLAIM_NOT_APPROVED")
    if any(step.status != ApprovalStepStatus.APPROVED for step in approval_steps):
        reasons.append("APPROVAL_STEP_NOT_APPROVED")
    if not approval_steps:
        reasons.append("APPROVAL_STEPS_MISSING")
    if any(
        finding.status == AuditFindingStatus.OPEN and finding.finding_code in _DUPLICATE_RELATED
        for finding in findings
    ):
        reasons.append("DUPLICATE_RELATED_FINDING_OPEN")
        if any(
            finding.status == AuditFindingStatus.OPEN
            and finding.finding_code == FindingCode.DUPLICATE_REIMBURSEMENT
            for finding in findings
        ):
            reasons.append("DUPLICATE_REIMBURSEMENT")
    if cost_center_id is None:
        reasons.append("MISSING_COST_CENTER")
    if existing_reimbursement_ids:
        reasons.append("REIMBURSEMENT_ALREADY_EXISTS")

    if reasons:
        result = ReimbursementEligibility(False, None, None, None, None, tuple(reasons))
        return failure(
            reason_codes=tuple(reasons),
            rule_ids=("E9", "AU3"),
            message="Reimbursement is blocked by one or more E9 eligibility conditions.",
            value=result,
        )

    home_currency_result = currency_for_country(employee.country)
    if home_currency_result.value is None:
        result = ReimbursementEligibility(False, None, None, None, None, ("UNSUPPORTED_COUNTRY",))
        return failure(
            reason_codes=("UNSUPPORTED_COUNTRY",),
            rule_ids=("G2", "E9"),
            message=home_currency_result.messages[0],
            value=result,
        )
    converted = to_home_currency(amount_usd, home_currency_result.value)
    if converted.value is None:
        result = ReimbursementEligibility(False, None, None, None, None, converted.reason_codes)
        return failure(
            reason_codes=converted.reason_codes,
            rule_ids=converted.rule_ids,
            message=converted.messages[0],
            value=result,
        )
    payment_date = add_business_days(final_approval_date, 5, employee.country)
    if payment_date.value is None:
        result = ReimbursementEligibility(False, None, None, None, None, payment_date.reason_codes)
        return failure(
            reason_codes=payment_date.reason_codes,
            rule_ids=payment_date.rule_ids,
            message=payment_date.messages[0],
            value=result,
        )
    status = (
        ReimbursementStatus.PAID
        if payment_date.value <= as_of_date
        else ReimbursementStatus.SCHEDULED
    )
    result = ReimbursementEligibility(
        True,
        converted.value,
        home_currency_result.value.value,
        payment_date.value,
        status,
        ("REIMBURSEMENT_ELIGIBLE",),
    )
    return success(
        result,
        reason_codes=result.reasons,
        rule_ids=("G2", "G3", "G4", "E9"),
        message="Claim satisfies E9; reimbursement amount and payment date are derived.",
    )
