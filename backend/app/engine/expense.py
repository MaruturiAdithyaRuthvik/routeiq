"""Expense line, claim, routing, and split-claim rules (E1-E6, E10, AU3)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Final

from .calendar import AS_OF_DATE
from .models import (
    ApprovalPathStep,
    ApprovalRole,
    CountryCode,
    CurrencyCode,
    ExpenseCategory,
    ExpenseClaim,
    ExpenseLine,
    ExpensePolicy,
    FindingCode,
    ReceiptFileType,
)
from .money import FX_TO_USD, round_half_up, to_usd
from .results import RuleResult, failure, success

_ONE: Final = Decimal("1")
_ZERO: Final = Decimal("0")
_BOUNDARIES: Final = (
    Decimal("50"),
    Decimal("1000"),
    Decimal("5000"),
    Decimal("20000"),
)


@dataclass(frozen=True, slots=True)
class ExpenseFlag:
    code: FindingCode
    rule_id: str
    reason_code: str
    message: str
    pct_over: Decimal | None = None


@dataclass(frozen=True, slots=True)
class EvaluatedExpenseLine:
    line_number: int
    category: ExpenseCategory
    amount: Decimal
    currency: str
    amount_usd: Decimal
    fx_rate_to_usd: Decimal
    limit_usd: Decimal
    receipt_threshold_usd: Decimal
    flags: tuple[ExpenseFlag, ...]


@dataclass(frozen=True, slots=True)
class ExpenseClaimEvaluation:
    lines: tuple[EvaluatedExpenseLine, ...]
    total_usd: Decimal
    flags: tuple[ExpenseFlag, ...]
    hard_reject_reason_codes: tuple[str, ...]
    hard_rejected: bool


@dataclass(frozen=True, slots=True)
class SplitClaimPair:
    first_claim_id: str
    second_claim_id: str
    boundary_usd: Decimal


def _policy_for_line(
    line: ExpenseLine, country: CountryCode, expense_date: date, policies: tuple[ExpensePolicy, ...]
) -> ExpensePolicy | None:
    candidates = [
        policy
        for policy in policies
        if policy.category == line.category
        and policy.country == country
        and policy.effective_from <= expense_date
        and (policy.effective_to is None or expense_date < policy.effective_to)
    ]
    return (
        max(candidates, key=lambda policy: (policy.version, policy.effective_from))
        if candidates
        else None
    )


def _metadata_valid(line: ExpenseLine) -> bool:
    metadata = (line.receipt_id, line.receipt_hash, line.file_type, line.size_kb)
    if not line.receipt_present:
        return all(value is None for value in metadata)
    if not isinstance(line.receipt_hash, str):
        return False
    try:
        ReceiptFileType(line.file_type)
    except (TypeError, ValueError):
        return False
    return (
        line.receipt_id is not None
        and len(line.receipt_hash) == 64
        and all(character in "0123456789abcdef" for character in line.receipt_hash)
        and line.size_kb is not None
        and line.size_kb > _ZERO
    )


def evaluate_expense_line(
    line: ExpenseLine,
    country: CountryCode,
    expense_date: date,
    policies: tuple[ExpensePolicy, ...],
    *,
    existing_receipt_hashes: frozenset[str] = frozenset(),
) -> RuleResult[EvaluatedExpenseLine]:
    """Convert, policy-check, and flag an expense line (E1-E3)."""

    policy = _policy_for_line(line, country, expense_date, policies)
    if policy is None:
        return failure(
            reason_codes=("EXPENSE_POLICY_NOT_FOUND",),
            rule_ids=("E1",),
            message="No effective expense policy matches the employee country and line category.",
        )
    if policy.per_line_limit_usd <= _ZERO or policy.receipt_threshold_usd < _ZERO:
        return failure(
            reason_codes=("INVALID_EXPENSE_POLICY",),
            rule_ids=("E1",),
            message="Expense policy limit must be positive and receipt threshold non-negative.",
        )
    converted = to_usd(line.amount, line.currency)
    if converted.value is None:
        return failure(
            reason_codes=converted.reason_codes,
            rule_ids=converted.rule_ids,
            message=converted.messages[0],
        )

    flags: list[ExpenseFlag] = []
    if converted.value > policy.per_line_limit_usd:
        flags.append(
            ExpenseFlag(
                FindingCode.POLICY_LIMIT_BREACH,
                "E3",
                "POLICY_LIMIT_BREACH",
                "Line exceeds the effective per-line policy limit.",
                round_half_up(
                    (converted.value / policy.per_line_limit_usd - _ONE) * Decimal(100), 2
                ).value,
            )
        )
    if converted.value > policy.receipt_threshold_usd and not line.receipt_present:
        flags.append(
            ExpenseFlag(
                FindingCode.MISSING_RECEIPT,
                "E3",
                "MISSING_RECEIPT",
                "A receipt is required above the effective threshold.",
            )
        )
    if line.receipt_hash is not None and line.receipt_hash in existing_receipt_hashes:
        flags.append(
            ExpenseFlag(
                FindingCode.DUPLICATE_RECEIPT,
                "E3",
                "DUPLICATE_RECEIPT",
                "Receipt hash appears on another expense line.",
            )
        )
    if not _metadata_valid(line):
        return failure(
            reason_codes=("INVALID_RECEIPT_METADATA",),
            rule_ids=("E2",),
            message="Receipt presence and metadata do not satisfy the E2 requirements.",
            value=EvaluatedExpenseLine(
                line.line_number,
                line.category,
                line.amount,
                CurrencyCode(line.currency).value,
                converted.value,
                FX_TO_USD[CurrencyCode(line.currency)],
                policy.per_line_limit_usd,
                policy.receipt_threshold_usd,
                tuple(flags),
            ),
        )
    resolved_currency = CurrencyCode(line.currency)
    return success(
        EvaluatedExpenseLine(
            line.line_number,
            line.category,
            line.amount,
            resolved_currency.value,
            converted.value,
            FX_TO_USD[resolved_currency],
            policy.per_line_limit_usd,
            policy.receipt_threshold_usd,
            tuple(flags),
        ),
        reason_codes=("EXPENSE_LINE_EVALUATED",),
        rule_ids=("E1", "E2", "E3"),
        message="Converted and checked expense line against effective policy.",
    )


def validate_expense_claim(
    claim: ExpenseClaim,
    policies: tuple[ExpensePolicy, ...],
    *,
    existing_receipt_hashes: frozenset[str] = frozenset(),
    as_of_date: date = AS_OF_DATE,
) -> RuleResult[ExpenseClaimEvaluation]:
    """Evaluate every line and apply E4 hard-rejection rules in documented order."""

    evaluated_lines: list[EvaluatedExpenseLine] = []
    line_flags: list[ExpenseFlag] = []
    reason_codes: list[str] = []
    receipt_hashes = Counter(line.receipt_hash for line in claim.lines if line.receipt_hash)
    duplicate_hashes = set(existing_receipt_hashes)
    duplicate_hashes.update(
        receipt_hash for receipt_hash, count in receipt_hashes.items() if count > 1
    )
    for line in sorted(claim.lines, key=lambda item: item.line_number):
        evaluated = evaluate_expense_line(
            line,
            claim.employee.country,
            claim.expense_date,
            policies,
            existing_receipt_hashes=frozenset(duplicate_hashes),
        )
        if not evaluated.ok or evaluated.value is None:
            return failure(
                reason_codes=evaluated.reason_codes,
                rule_ids=evaluated.rule_ids,
                message=evaluated.messages[0],
            )
        evaluated_lines.append(evaluated.value)
        line_flags.extend(evaluated.value.flags)
        if (
            line.receipt_hash is not None
            and line.receipt_hash in duplicate_hashes
            and FindingCode.DUPLICATE_RECEIPT.value not in reason_codes
        ):
            reason_codes.append(FindingCode.DUPLICATE_RECEIPT.value)
    rounded_total = round_half_up(sum((line.amount_usd for line in evaluated_lines), _ZERO), 2)
    if rounded_total.value is None:
        return failure(
            reason_codes=rounded_total.reason_codes,
            rule_ids=rounded_total.rule_ids,
            message=rounded_total.messages[0],
        )

    all_flags = list(line_flags)
    if claim.cost_center_id is None:
        all_flags.append(
            ExpenseFlag(
                FindingCode.MISSING_COST_CENTER,
                "E3",
                "MISSING_COST_CENTER",
                "Expense claim has no cost center.",
            )
        )
        reason_codes.append("MISSING_COST_CENTER")
    if claim.expense_date < claim.employee.hire_date or (
        claim.employee.termination_date is not None
        and claim.expense_date > claim.employee.termination_date
    ):
        all_flags.append(
            ExpenseFlag(
                FindingCode.DATE_OUTSIDE_EMPLOYMENT,
                "E3",
                "DATE_OUTSIDE_EMPLOYMENT",
                "Expense date is outside the employee's employment dates.",
            )
        )
        reason_codes.append("DATE_OUTSIDE_EMPLOYMENT")
    if claim.expense_date > as_of_date:
        all_flags.append(
            ExpenseFlag(
                FindingCode.FUTURE_EXPENSE_DATE,
                "E4",
                "FUTURE_EXPENSE_DATE",
                "Expense date is after AS_OF_DATE.",
            )
        )
        reason_codes.append("FUTURE_EXPENSE_DATE")

    if any(line.amount_usd > line.limit_usd * Decimal("1.5") for line in evaluated_lines):
        reason_codes.append("POLICY_LIMIT_BREACH")

    ordered_reasons = tuple(
        code
        for code in (
            "POLICY_LIMIT_BREACH",
            "DUPLICATE_RECEIPT",
            "MISSING_COST_CENTER",
            "DATE_OUTSIDE_EMPLOYMENT",
            "FUTURE_EXPENSE_DATE",
        )
        if code in reason_codes
    )
    evaluation = ExpenseClaimEvaluation(
        lines=tuple(evaluated_lines),
        total_usd=rounded_total.value,
        flags=tuple(all_flags),
        hard_reject_reason_codes=ordered_reasons,
        hard_rejected=bool(ordered_reasons),
    )
    if ordered_reasons:
        return failure(
            reason_codes=ordered_reasons,
            rule_ids=("E4", "AU3"),
            message="Expense claim has one or more E4 submit-time hard rejects.",
            value=evaluation,
        )
    return success(
        evaluation,
        reason_codes=("EXPENSE_CLAIM_VALID",),
        rule_ids=("E1", "E2", "E3", "E4"),
        message="Expense claim has no E4 hard-rejection conditions.",
    )


def route_expense(
    total_usd: Decimal,
    lines: tuple[EvaluatedExpenseLine, ...],
    employee_country: CountryCode,
    merchant_country: CountryCode,
    *,
    open_e3_flags: tuple[ExpenseFlag, ...] = (),
) -> RuleResult[tuple[ApprovalPathStep, ...]]:
    """Create ordered, deduplicated base and additive approval roles (E5, E6, AU3)."""

    if not total_usd.is_finite() or total_usd < _ZERO:
        return failure(
            reason_codes=("INVALID_CLAIM_TOTAL",),
            rule_ids=("E5",),
            message="Claim total must be a finite non-negative Decimal.",
        )
    base_reason: str
    base_code: str
    if total_usd < Decimal("50") and not open_e3_flags:
        base_roles = (ApprovalRole.SYSTEM,)
        base_reason = "Claim is below USD 50 and has no open E3 flags."
        base_code = "EXPENSE_LT_50_AUTO"
    elif total_usd < Decimal("50"):
        base_roles = (ApprovalRole.MANAGER,)
        base_reason = "Claim is below USD 50 but has open E3 flags."
        base_code = "EXPENSE_LT_50_FLAGGED"
    elif total_usd < Decimal("1000"):
        base_roles = (ApprovalRole.MANAGER,)
        base_reason = "Claim total is USD 50 to below USD 1,000."
        base_code = "EXPENSE_50_1000"
    elif total_usd < Decimal("5000"):
        base_roles = (ApprovalRole.MANAGER, ApprovalRole.DEPT_HEAD)
        base_reason = "Claim total is USD 1,000 to below USD 5,000."
        base_code = "EXPENSE_1000_5000"
    elif total_usd < Decimal("20000"):
        base_roles = (
            ApprovalRole.MANAGER,
            ApprovalRole.DEPT_HEAD,
            ApprovalRole.FINANCE_CONTROLLER,
        )
        base_reason = "Claim total is USD 5,000 to below USD 20,000."
        base_code = "EXPENSE_5000_20000"
    else:
        base_roles = (
            ApprovalRole.MANAGER,
            ApprovalRole.DEPT_HEAD,
            ApprovalRole.FINANCE_CONTROLLER,
            ApprovalRole.CFO,
        )
        base_reason = "Claim total is USD 20,000 or more."
        base_code = "EXPENSE_GTE_20000"

    additions: list[tuple[ApprovalRole, str, str, str]] = []
    if employee_country != merchant_country and any(
        line.category == ExpenseCategory.AIRFARE for line in lines
    ):
        additions.append(
            (
                ApprovalRole.FINANCE_CONTROLLER,
                "AIRFARE_INTERNATIONAL",
                "E6",
                "International airfare requires finance-controller review.",
            )
        )
    if any(
        line.category == ExpenseCategory.CLIENT_ENTERTAINMENT and line.amount_usd > Decimal("250")
        for line in lines
    ):
        additions.append(
            (
                ApprovalRole.COMPLIANCE_OFFICER,
                "CLIENT_ENTERTAINMENT_GT_250",
                "E6",
                "Client-entertainment line exceeds USD 250.",
            )
        )
    if any(
        line.category == ExpenseCategory.GIFTS and line.amount_usd > Decimal("250")
        for line in lines
    ):
        additions.append(
            (
                ApprovalRole.COMPLIANCE_OFFICER,
                "GIFT_GT_250",
                "E6",
                "Gift line exceeds USD 250.",
            )
        )
    if any(
        flag.code == FindingCode.POLICY_LIMIT_BREACH
        and not any(line.amount_usd > line.limit_usd * Decimal("1.5") for line in lines)
        for flag in open_e3_flags
    ):
        additions.append(
            (
                ApprovalRole.FINANCE_CONTROLLER,
                "POLICY_LIMIT_BREACH",
                "E6",
                "Policy-limit exception requires finance-controller review.",
            )
        )
    if any(flag.code == FindingCode.MISSING_RECEIPT for flag in open_e3_flags):
        additions.append(
            (
                ApprovalRole.FINANCE_CONTROLLER,
                "MISSING_RECEIPT",
                "E6",
                "Missing-receipt exception requires finance-controller review.",
            )
        )

    role_reasons: dict[ApprovalRole, tuple[str, tuple[str, ...]]] = {
        role: (base_reason, (base_code,)) for role in base_roles
    }
    role_rule_ids: dict[ApprovalRole, list[str]] = {role: ["E5", "AU3"] for role in base_roles}
    ordered_roles = list(base_roles)
    for role, reason_code, rule_id, message in additions:
        if role not in role_reasons:
            ordered_roles.append(role)
            role_reasons[role] = (message, (reason_code,))
            role_rule_ids[role] = [rule_id, "AU3"]
        else:
            old_reason, old_codes = role_reasons[role]
            role_reasons[role] = (old_reason, tuple(dict.fromkeys((*old_codes, reason_code))))
            role_rule_ids[role].append(rule_id)

    path: list[ApprovalPathStep] = []
    for level, role in enumerate(ordered_roles, start=1):
        reason, reason_codes = role_reasons[role]
        rule_ids = tuple(dict.fromkeys(role_rule_ids[role]))
        path.append(
            ApprovalPathStep(
                level=level,
                approver_type=role,
                reason=reason,
                rule_ids=rule_ids,
                reason_codes=reason_codes,
            )
        )
    path_result = tuple(path)
    all_codes = tuple(dict.fromkeys((base_code, *(item[1] for item in additions))))
    return success(
        path_result,
        reason_codes=all_codes,
        rule_ids=("E5", "E6", "AU3"),
        message="Derived ordered expense approval path from total and exception rules.",
    )


def detect_split_claims(
    claims: tuple[ExpenseClaim, ...],
    totals_usd: dict[str, Decimal],
) -> RuleResult[tuple[SplitClaimPair, ...]]:
    """Find deterministic E10 split-claim pairs without consulting ground truth."""

    pairs: list[SplitClaimPair] = []
    sorted_claims = sorted(
        claims,
        key=lambda claim: (claim.employee.employee_id, claim.expense_date, claim.expense_claim_id),
    )
    for index, first in enumerate(sorted_claims):
        first_total = totals_usd.get(first.expense_claim_id)
        if first_total is None:
            return failure(
                reason_codes=("CLAIM_TOTAL_MISSING",),
                rule_ids=("E10",),
                message=f"Missing computed total for {first.expense_claim_id}.",
            )
        for second in sorted_claims[index + 1 :]:
            if first.employee.employee_id != second.employee.employee_id:
                continue
            if first.merchant_name.strip().casefold() != second.merchant_name.strip().casefold():
                continue
            if abs((first.expense_date - second.expense_date).days) > 3:
                continue
            if not {line.category for line in first.lines}.intersection(
                line.category for line in second.lines
            ):
                continue
            second_total = totals_usd.get(second.expense_claim_id)
            if second_total is None:
                return failure(
                    reason_codes=("CLAIM_TOTAL_MISSING",),
                    rule_ids=("E10",),
                    message=f"Missing computed total for {second.expense_claim_id}.",
                )
            for boundary in _BOUNDARIES:
                lower = boundary * Decimal("0.90")
                upper = boundary * Decimal("0.9999")
                if (
                    lower <= first_total <= upper
                    and lower <= second_total <= upper
                    and first_total + second_total >= boundary
                ):
                    pairs.append(
                        SplitClaimPair(
                            first.expense_claim_id,
                            second.expense_claim_id,
                            boundary,
                        )
                    )
    return success(
        tuple(pairs),
        reason_codes=("SPLIT_CLAIM_DETECTED",) if pairs else ("NO_SPLIT_CLAIM",),
        rule_ids=("E10",),
        message=f"Detected {len(pairs)} split-claim pair(s).",
    )
