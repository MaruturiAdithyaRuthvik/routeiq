"""Expense scenarios, routing, approvals, findings, and reimbursements."""

from __future__ import annotations

import hashlib
import math
import random
from collections.abc import Callable
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.engine.eligibility import check_reimbursement_eligibility
from app.engine.expense import (
    ExpenseClaimEvaluation,
    detect_split_claims,
    route_expense,
    validate_expense_claim,
)
from app.engine.ids import IdKind
from app.engine.lifecycle import transition
from app.engine.models import (
    ApprovalPathStep,
    ApprovalRole,
    ApprovalStep,
    ApprovalStepStatus,
    AuditFindingStatus,
    CountryCode,
    CurrencyCode,
    Employee,
    ExpenseCategory,
    ExpenseClaim,
    ExpenseLine,
    ExpenseStatus,
    FindingCode,
    OpenFinding,
    ReceiptFileType,
    ReimbursementStatus,
    RequestType,
)
from app.engine.money import FX_TO_USD, round_half_up

from .context import CATEGORIES, CATEGORY_LIMITS, GenerationContext, Row
from .helpers import (
    add_workdays,
    event_payload,
    make_audit_row,
    new_id,
    utc_at,
)
from .leave import _add_finding, resolve_approver_path, resolved_rule_ids
from .tables import set_table

_ZERO = Decimal("0")
_CATEGORY_WEIGHTS = (27, 10, 8, 18, 8, 10, 6, 5, 3, 5)
_MEDIAN_USD: dict[str, Decimal] = {
    "MEALS": Decimal("35"),
    "LODGING": Decimal("220"),
    "AIRFARE": Decimal("500"),
    "GROUND_TRANSPORT": Decimal("32"),
    "SOFTWARE": Decimal("150"),
    "OFFICE_SUPPLIES": Decimal("45"),
    "TRAINING": Decimal("300"),
    "CLIENT_ENTERTAINMENT": Decimal("90"),
    "GIFTS": Decimal("70"),
    "COMMUNICATION": Decimal("45"),
}


def generate_expense_data(context: GenerationContext) -> None:
    """Generate claims and derive all totals, findings, paths, decisions, and reimbursements."""

    rng: random.Random = context.rng
    employees: dict[str, Employee] = context.references["employees"]
    employee_choices = tuple(employees[key] for key in sorted(employees))
    line_rows: list[Row] = []
    claim_rows: list[Row] = []
    event_rows: list[Row] = []
    claim_models: list[ExpenseClaim] = []
    claim_totals: dict[str, Decimal] = {}
    line_ids_by_claim: dict[str, list[str]] = {}
    claim_paths: dict[str, tuple[ApprovalPathStep, ...]] = {}
    claim_final_approval: dict[str, datetime] = {}
    claim_approval_steps: dict[str, list[Row]] = {}
    prior_receipt_hashes: set[str] = set()
    out_of_employment_sequence = max(15, round(context.preset.expense_claims * 0.45))
    split_first_sequence = max(20, round(context.preset.expense_claims * 0.30))
    split_second_sequence = split_first_sequence + 1
    split_employee_id = _select_split_employee(context)
    split_date: date | None = None
    duplicate_source_hash: str | None = None
    event_sequence = 1
    audit_sequence = int(context.references["next_audit_sequence"])
    expense_audits: list[Row] = []

    for sequence in range(1, context.preset.expense_claims + 1):
        claim_id = new_id(IdKind.EXPENSE_CLAIM, sequence)
        submit_date = _submission_date(sequence - 1, context.preset.expense_claims)
        employee = _select_employee_for_claim(
            context,
            sequence,
            submit_date,
            employee_choices,
            out_of_employment_sequence,
            split_first_sequence,
            split_second_sequence,
            split_employee_id,
        )
        submit_at = utc_at(submit_date, 9 * 60 + (sequence % 12) * 20)
        existing_hashes = frozenset(prior_receipt_hashes)
        merchant_country = _merchant_country(context, employee, sequence)
        expense_date = _expense_date(
            context,
            sequence,
            employee,
            submit_date,
            out_of_employment_sequence,
            split_first_sequence,
            split_second_sequence,
            split_date,
        )
        if sequence == split_first_sequence:
            split_date = expense_date
            context.references["split_date"] = split_date
        if sequence == split_second_sequence:
            expense_date = context.references["split_date"]
        cost_center_id = _claim_cost_center(context, employee, expense_date)
        if sequence == 5:
            cost_center_id = None
        if sequence in (split_first_sequence, split_second_sequence):
            merchant_country = employee.country
            cost_center_id = _claim_cost_center(context, employee, expense_date)

        line_count = _line_count(rng, sequence, split_first_sequence, split_second_sequence)
        line_models: list[ExpenseLine] = []
        for line_number in range(1, line_count + 1):
            category, usd_target, receipt_present, forced_hash = _line_scenario(
                context,
                sequence,
                line_number,
                employee,
                cost_center_id,
                line_count,
                split_first_sequence,
                split_second_sequence,
                duplicate_source_hash,
            )
            if sequence == 2 and line_number == 1 and duplicate_source_hash is not None:
                forced_hash = duplicate_source_hash
            currency = CurrencyCode(employee.home_currency or CurrencyCode.USD)
            source_amount = _local_amount(usd_target, currency)
            receipt_hash = forced_hash
            receipt_id = None
            file_type = None
            size_kb = None
            if receipt_present:
                receipt_id = f"RCT-2026-{sequence:06d}-{line_number:02d}"
                if receipt_hash is None:
                    descriptor = (
                        f"RouteIQ synthetic receipt|{context.seed}|{claim_id}|{line_number}|"
                        f"{employee.employee_id}|{expense_date.isoformat()}"
                    )
                    receipt_hash = hashlib.sha256(descriptor.encode("utf-8")).hexdigest()
                file_type = rng.choice(("PDF", "JPG", "JPEG", "PNG", "HEIC"))
                size_kb = Decimal(rng.randint(35, 950)) / Decimal(10)
                prior_receipt_hashes.add(receipt_hash)
                if sequence == 1 and line_number == 2:
                    duplicate_source_hash = receipt_hash
                    context.references["duplicate_receipt_source_hash"] = receipt_hash
            model = ExpenseLine(
                line_number=line_number,
                category=ExpenseCategory(category),
                amount=source_amount,
                currency=currency,
                receipt_present=receipt_present,
                receipt_id=receipt_id,
                receipt_hash=receipt_hash,
                file_type=None if file_type is None else ReceiptFileType(file_type),
                size_kb=size_kb,
                description=f"Synthetic {category.casefold().replace('_', ' ')} expense.",
            )
            line_models.append(model)

        claim_model = ExpenseClaim(
            expense_claim_id=claim_id,
            employee=employee,
            merchant_name=_merchant_name(
                context,
                employee.country.value,
                line_models[0].category.value,
                sequence,
                split_first_sequence,
                split_second_sequence,
            ),
            merchant_country=CountryCode(merchant_country.value),
            expense_date=expense_date,
            cost_center_id=cost_center_id,
            lines=tuple(line_models),
        )
        validation = validate_expense_claim(
            claim_model,
            context.references["expense_policies"],
            existing_receipt_hashes=existing_hashes,
            as_of_date=context.as_of_date,
        )
        if validation.value is None:
            raise ValueError(validation.messages[0])
        evaluation = validation.value
        total_usd = evaluation.total_usd
        claim_totals[claim_id] = total_usd
        claim_models.append(claim_model)
        line_ids: list[str] = []

        evaluated_by_line = {item.line_number: item for item in evaluation.lines}
        for line in line_models:
            evaluated = evaluated_by_line[line.line_number]
            line_id = new_id(IdKind.EXPENSE_LINE, line.line_number, parent_id=claim_id)
            line_ids.append(line_id)
            line_rows.append(
                {
                    "expense_line_id": line_id,
                    "expense_claim_id": claim_id,
                    "line_number": line.line_number,
                    "category": line.category.value,
                    "expense_policy_id": context.references["policy_id_by_category_country"][
                        (employee.country.value, line.category.value)
                    ],
                    "description": line.description,
                    "amount": line.amount,
                    "currency": line.currency.value,
                    "fx_rate_to_usd": evaluated.fx_rate_to_usd,
                    "amount_usd": evaluated.amount_usd,
                    "receipt_present": line.receipt_present,
                    "receipt_id": line.receipt_id,
                    "receipt_hash": line.receipt_hash,
                    "file_type": None if line.file_type is None else line.file_type.value,
                    "size_kb": line.size_kb,
                }
            )
        line_ids_by_claim[claim_id] = line_ids

        created_at = submit_at - timedelta(minutes=1)
        request_events: list[Row] = []

        def append_event(
            event_type: str,
            from_status: str | None,
            to_status: str | None,
            occurred_at: datetime,
            reason_code: str | None = None,
            actor_employee_id: str | None = None,
            payload: dict[str, object] | None = None,
            system_event: bool = False,
            events: list[Row] = request_events,
            parent_id: str = claim_id,
            default_actor_id: str = employee.employee_id,
        ) -> str:
            nonlocal event_sequence
            event_id = new_id(IdKind.EXPENSE_CLAIM_EVENT, event_sequence)
            event_sequence += 1
            events.append(
                {
                    "event_id": event_id,
                    "expense_claim_id": parent_id,
                    "sequence_number": len(events) + 1,
                    "event_type": event_type,
                    "from_status": from_status,
                    "to_status": to_status,
                    "occurred_at": occurred_at,
                    "actor_employee_id": (
                        None if system_event else actor_employee_id or default_actor_id
                    ),
                    "reason_code": reason_code,
                    "event_payload": payload or {},
                }
            )
            return event_id

        append_event("CREATED", None, "DRAFT", created_at)
        _add_expense_flags(
            context,
            claim_id,
            line_ids,
            evaluation,
            submit_at,
        )
        submit_audit = make_audit_row(
            context,
            audit_sequence,
            request_id=claim_id,
            request_type="EXPENSE",
            decision_kind="SUBMIT_VALIDATION",
            inputs={
                "employee_id": employee.employee_id,
                "expense_date": expense_date,
                "cost_center_id": cost_center_id,
                "total_usd": total_usd,
                "line_count": len(line_models),
            },
            outputs={
                "valid": validation.ok,
                "hard_rejected": evaluation.hard_rejected,
                "reason_codes": evaluation.hard_reject_reason_codes,
            },
            matched_rule_ids=validation.rule_ids,
            reason_codes=evaluation.hard_reject_reason_codes,
            recorded_at=submit_at,
        )
        expense_audits.append(submit_audit)
        audit_sequence += 1

        claim_status = ExpenseStatus.DRAFT
        resolved_path: tuple[ApprovalPathStep, ...] = ()
        final_decision_at: datetime | None = None
        approval_rows: list[Row] = []
        if evaluation.hard_rejected:
            reason_code = evaluation.hard_reject_reason_codes[0]
            append_event("SUBMISSION_ATTEMPT", "DRAFT", "DRAFT", submit_at, reason_code)
        else:
            append_event("SUBMITTED", "DRAFT", "SUBMITTED", submit_at)
            transition(claim_status, ExpenseStatus.SUBMITTED, RequestType.EXPENSE)
            claim_status = ExpenseStatus.SUBMITTED
            append_event(
                "APPROVAL_STARTED",
                "SUBMITTED",
                "PENDING_APPROVAL",
                submit_at + timedelta(minutes=1),
            )
            transition(claim_status, ExpenseStatus.PENDING_APPROVAL, RequestType.EXPENSE)
            claim_status = ExpenseStatus.PENDING_APPROVAL

            open_e3_flags = tuple(flag for flag in evaluation.flags if flag.rule_id == "E3")
            routed = route_expense(
                total_usd,
                evaluation.lines,
                employee.country,
                claim_model.merchant_country,
                open_e3_flags=open_e3_flags,
            )
            if not routed.ok or routed.value is None:
                raise ValueError(routed.messages[0])
            resolved_path = resolve_approver_path(
                context,
                routed.value,
                employee,
                request_type="EXPENSE",
                on_date=submit_date,
                cost_center_id=cost_center_id,
            )
            if any(
                step.approver_id is None and step.approver_type != ApprovalRole.SYSTEM
                for step in resolved_path
            ):
                _add_finding(
                    context,
                    expense_claim_id=claim_id,
                    finding_code="UNRESOLVED_APPROVER",
                    severity="ERROR",
                    details={"rule_ids": ["G5", "E7", "AU3"]},
                    detected_at=submit_at,
                )
            route_audit = make_audit_row(
                context,
                audit_sequence,
                request_id=claim_id,
                request_type="EXPENSE",
                decision_kind="ROUTING",
                inputs={
                    "employee_id": employee.employee_id,
                    "expense_date": expense_date,
                    "merchant_country": merchant_country,
                    "cost_center_id": cost_center_id,
                    "total_usd": total_usd,
                    "flags": [flag.code.value for flag in evaluation.flags],
                },
                outputs={"path": resolved_path},
                matched_rule_ids=tuple(
                    sorted(set(routed.rule_ids + resolved_rule_ids(resolved_path)))
                ),
                reason_codes=tuple(code for step in resolved_path for code in step.reason_codes),
                path=resolved_path,
                recorded_at=submit_at,
            )
            expense_audits.append(route_audit)
            audit_sequence += 1
            claim_paths[claim_id] = resolved_path

            if resolved_path and resolved_path[0].approver_type == ApprovalRole.SYSTEM:
                assigned = submit_at + timedelta(minutes=2)
                approval_rows.append(
                    _approval_row(
                        claim_id,
                        None,
                        1,
                        ApprovalRole.SYSTEM,
                        ApprovalStepStatus.APPROVED,
                        assigned,
                        assigned,
                        employee.country.value,
                        None,
                    )
                )
                final_decision_at = assigned
                claim_status = ExpenseStatus.APPROVED
                append_event(
                    "APPROVAL_DECIDED",
                    "PENDING_APPROVAL",
                    "APPROVED",
                    assigned,
                    actor_employee_id=None,
                    system_event=True,
                )
            else:
                outcome = rng.choices(("APPROVE", "REJECT", "PENDING"), weights=(84, 7, 9), k=1)[0]
                claim_status, approval_rows, final_decision_at, _final_event = (
                    _process_expense_steps(
                        context,
                        claim_id,
                        employee,
                        submit_at,
                        resolved_path,
                        outcome,
                        append_event,
                    )
                )
            claim_approval_steps[claim_id] = approval_rows
            context.references.setdefault("approval_step_rows", []).extend(approval_rows)
            if claim_status != ExpenseStatus.PENDING_APPROVAL:
                transition(ExpenseStatus.PENDING_APPROVAL, claim_status, RequestType.EXPENSE)
            if final_decision_at is not None:
                approval_audit = make_audit_row(
                    context,
                    audit_sequence,
                    request_id=claim_id,
                    request_type="EXPENSE",
                    decision_kind="APPROVAL",
                    inputs={"expense_claim_id": claim_id, "total_usd": total_usd},
                    outputs={"status": claim_status.value},
                    matched_rule_ids=("E5", "E6", "E8", "AU3"),
                    reason_codes=tuple(
                        code for step in resolved_path for code in step.reason_codes
                    ),
                    path=resolved_path,
                    recorded_at=final_decision_at,
                )
                expense_audits.append(approval_audit)
                audit_sequence += 1
            if claim_status == ExpenseStatus.APPROVED and final_decision_at is not None:
                claim_final_approval[claim_id] = final_decision_at

        claim_rows.append(
            {
                "expense_claim_id": claim_id,
                "employee_id": employee.employee_id,
                "merchant_name": claim_model.merchant_name,
                "merchant_country": merchant_country,
                "expense_date": expense_date,
                "cost_center_id": cost_center_id,
                "total_usd": total_usd,
                "status": claim_status.value,
                "submitted_at": submit_at if not evaluation.hard_rejected else None,
                "risk_score": 0,
            }
        )
        event_rows.extend(request_events)

    _create_split_findings(context, claim_models, claim_totals)
    reimbursement_rows = _create_reimbursements(
        context,
        claim_rows,
        claim_totals,
        claim_models,
        line_ids_by_claim,
        claim_approval_steps,
        claim_final_approval,
        claim_paths,
        event_rows,
        event_sequence,
        expense_audits,
        audit_sequence,
    )
    context.references["expense_claim_rows"] = claim_rows
    context.references["expense_line_rows"] = line_rows
    context.references["expense_event_rows"] = event_rows
    context.references["expense_claim_models"] = {
        claim.expense_claim_id: claim for claim in claim_models
    }
    context.references["expense_totals"] = claim_totals
    context.references["expense_line_ids"] = line_ids_by_claim
    context.references["expense_paths"] = claim_paths
    context.references["reimbursement_rows"] = reimbursement_rows
    context.references["decision_audit_rows"].extend(expense_audits)
    set_table(context, "expense_claim", claim_rows)
    set_table(context, "expense_line", line_rows)
    set_table(context, "expense_claim_event", event_rows)
    set_table(context, "approval_step", context.references.get("approval_step_rows", []))
    set_table(context, "reimbursement", reimbursement_rows)
    set_table(context, "decision_audit", context.references["decision_audit_rows"])


def _select_employee_for_claim(
    context: GenerationContext,
    sequence: int,
    submit_date: date,
    choices: tuple[Employee, ...],
    outside_sequence: int,
    split_first: int,
    split_second: int,
    split_employee_id: str,
) -> Employee:
    if sequence in (split_first, split_second):
        return context.references["employees"][split_employee_id]
    if sequence == outside_sequence:
        terminated = sorted(
            (
                context.references["employees"][employee_id]
                for employee_id in context.references["terminated_employee_ids"]
            ),
            key=lambda employee: (
                employee.termination_date or context.as_of_date,
                employee.employee_id,
            ),
        )
        if terminated:
            return terminated[0]
    active_by_submission = [
        employee
        for employee in choices
        if employee.hire_date < submit_date
        and (employee.termination_date is None or employee.termination_date >= date(2026, 1, 1))
    ]
    return context.rng.choice(active_by_submission or choices)


def _select_split_employee(context: GenerationContext) -> str:
    employees = [
        employee
        for employee in context.references["employees"].values()
        if employee.manager_id is not None and employee.termination_date is None
    ]
    return min(employees, key=lambda employee: employee.employee_id).employee_id


def _merchant_country(context: GenerationContext, employee: Employee, sequence: int) -> CountryCode:
    if sequence in (
        max(20, round(context.preset.expense_claims * 0.30)),
        max(20, round(context.preset.expense_claims * 0.30)) + 1,
    ):
        return employee.country
    if context.rng.random() < 0.16:
        other = [country for country in CountryCode if country != employee.country]
        return context.rng.choice(other)
    return employee.country


def _expense_date(
    context: GenerationContext,
    sequence: int,
    employee: Employee,
    submit_date: date,
    outside_sequence: int,
    split_first: int,
    split_second: int,
    split_date: date | None,
) -> date:
    if sequence == outside_sequence and employee.termination_date is not None:
        return min(employee.termination_date + timedelta(days=1), context.as_of_date)
    if sequence in (split_first, split_second) and split_date is not None:
        return split_date
    if sequence == split_first:
        return max(employee.hire_date, submit_date - timedelta(days=1))
    if sequence == 7:
        return date(2026, 11, 2)
    earliest = max(date(2026, 1, 1), employee.hire_date)
    latest = min(submit_date - timedelta(days=1), employee.termination_date or submit_date)
    if latest < earliest:
        return earliest
    days_back = context.rng.randint(0, min(60, (latest - earliest).days))
    return latest - timedelta(days=days_back)


def _claim_cost_center(context: GenerationContext, employee: Employee, on_date: date) -> str | None:
    candidates = [
        row
        for row in context.references["assignments"]
        if row["employee_id"] == employee.employee_id
        and row["effective_from"] <= on_date
        and (row["effective_to"] is None or on_date < row["effective_to"])
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda row: (-row["allocation_pct"], row["cost_center_id"]))
    return candidates[0]["cost_center_id"]


def _line_count(rng: random.Random, sequence: int, split_first: int, split_second: int) -> int:
    if sequence == 1:
        return 2
    if sequence == 12:
        return 1
    if sequence in (split_first, split_second):
        return 1
    if sequence % 5 == 0:
        return 2
    return rng.choices((1, 2, 3, 4, 5, 6), weights=(40, 30, 20, 8, 1, 1), k=1)[0]


def _line_scenario(
    context: GenerationContext,
    sequence: int,
    line_number: int,
    employee: Employee,
    cost_center_id: str | None,
    line_count: int,
    split_first: int,
    split_second: int,
    duplicate_source_hash: str | None,
) -> tuple[str, Decimal, bool, str | None]:
    rng = context.rng
    if sequence == 1 and line_number == 1:
        return "MEALS", Decimal("60"), False, None
    if sequence == 1 and line_number == 2:
        return "MEALS", Decimal("25"), True, None
    if sequence == 12 and line_number == 1:
        return "MEALS", Decimal("30"), True, None
    if sequence == 2 and line_number == 1 and duplicate_source_hash is not None:
        return "MEALS", Decimal("45"), True, duplicate_source_hash
    if sequence == 3 and line_number == 1:
        factor, _threshold = CATEGORY_LIMITS["MEALS"]
        country_factor = context.references["cost_factors"][employee.country.value]
        return "MEALS", factor * country_factor * Decimal("1.20"), True, None
    if sequence == 4 and line_number == 1:
        factor, _threshold = CATEGORY_LIMITS["MEALS"]
        country_factor = context.references["cost_factors"][employee.country.value]
        return "MEALS", factor * country_factor * Decimal("1.60"), True, None
    if sequence in (split_first, split_second):
        return "AIRFARE", Decimal("950"), True, None
    if sequence % 5 == 0 and line_number <= 2:
        target = Decimal(context.rng.randint(60000, 90000)) / Decimal("100")
        return "AIRFARE", target, True, None

    category = rng.choices(CATEGORIES, weights=_CATEGORY_WEIGHTS, k=1)[0]
    sampled = float(context.np_rng.lognormal(math.log(float(_MEDIAN_USD[category])), 0.8))
    usd = round_half_up(Decimal(str(sampled)), 2)
    if usd.value is None:
        raise ValueError(usd.messages[0])
    factor = context.references["cost_factors"][employee.country.value]
    limit = CATEGORY_LIMITS[category][0] * factor
    amount = min(max(usd.value, Decimal("2.00")), limit * Decimal("0.95"))
    receipt_present = True
    if category == "AIRFARE" and amount < Decimal("50"):
        amount = Decimal("50")
    return category, amount, receipt_present, None


def _local_amount(usd_amount: Decimal, currency: CurrencyCode) -> Decimal:
    converted = round_half_up(usd_amount / FX_TO_USD[currency], 2)
    if converted.value is None:
        raise ValueError(converted.messages[0])
    return converted.value


def _merchant_name(
    context: GenerationContext,
    country: str,
    category: str,
    sequence: int,
    split_first: int,
    split_second: int,
) -> str:
    if sequence in (split_first, split_second):
        return "RouteIQ Synthetic Air Sample Merchant"
    return context.references["merchants"][(country, category)]


def _add_expense_flags(
    context: GenerationContext,
    claim_id: str,
    line_ids: list[str],
    evaluation: ExpenseClaimEvaluation,
    detected_at: datetime,
) -> None:
    for flag in evaluation.flags:
        line_id = None
        for item in evaluation.lines:
            if any(candidate is flag for candidate in item.flags):
                line_id = line_ids[item.line_number - 1]
                break
        _add_finding(
            context,
            finding_code=flag.code.value,
            severity="ERROR"
            if flag.code
            in (
                FindingCode.DUPLICATE_RECEIPT,
                FindingCode.MISSING_COST_CENTER,
                FindingCode.DATE_OUTSIDE_EMPLOYMENT,
                FindingCode.FUTURE_EXPENSE_DATE,
            )
            else "WARNING",
            details={
                "message": flag.message,
                "pct_over": None if flag.pct_over is None else str(flag.pct_over),
                "rule_id": flag.rule_id,
            },
            detected_at=detected_at,
            expense_claim_id=None if line_id is not None else claim_id,
            expense_line_id=line_id,
        )


def _process_expense_steps(
    context: GenerationContext,
    claim_id: str,
    employee: Employee,
    submitted_at: datetime,
    path: tuple[ApprovalPathStep, ...],
    outcome: str,
    append_event: Callable[..., str],
) -> tuple[ExpenseStatus, list[Row], datetime | None, str | None]:
    if not path:
        return ExpenseStatus.PENDING_APPROVAL, [], None, None
    reject_at = context.rng.randrange(len(path)) if outcome == "REJECT" else -1
    pending_after = context.rng.randrange(len(path)) if outcome == "PENDING" else len(path)
    previous_decision = submitted_at + timedelta(minutes=2)
    rows: list[Row] = []
    last_decision: datetime | None = None
    final_event_id: str | None = None
    final_status = ExpenseStatus.PENDING_APPROVAL
    for index, step in enumerate(path):
        assigned_at = previous_decision + timedelta(minutes=1)
        rejected = outcome == "REJECT" and index == reject_at
        should_decide = (
            outcome == "APPROVE"
            or (outcome == "REJECT" and index <= reject_at)
            or (outcome == "PENDING" and index < pending_after)
        )
        status = ApprovalStepStatus.PENDING
        decided_at = None
        if should_decide and step.approver_id is not None:
            delay = context.rng.choices((1, 2, 3, 4), weights=(2, 4, 3, 1), k=1)[0]
            decision_date = add_workdays(assigned_at.date(), delay, employee.country.value)
            decision_time = utc_at(decision_date, 15 * 60 + index * 5)
            if decision_date <= context.as_of_date:
                status = ApprovalStepStatus.REJECTED if rejected else ApprovalStepStatus.APPROVED
                decided_at = decision_time
                last_decision = decision_time
                previous_decision = decision_time
                terminal = rejected or (outcome == "APPROVE" and index == len(path) - 1)
                final_event_id = append_event(
                    "APPROVAL_DECIDED",
                    "PENDING_APPROVAL",
                    "REJECTED" if rejected else "APPROVED" if terminal else "PENDING_APPROVAL",
                    decision_time,
                    None,
                    step.approver_id,
                )
                if rejected:
                    final_status = ExpenseStatus.REJECTED
            if decision_date > context.as_of_date:
                should_decide = False
        rows.append(
            _approval_row(
                claim_id,
                step.approver_id,
                index + 1,
                step.approver_type,
                status,
                assigned_at,
                decided_at,
                employee.country.value,
                None,
            )
        )
        if status != ApprovalStepStatus.APPROVED:
            break
    while len(rows) < len(path):
        index = len(rows)
        step = path[index]
        assigned_at = max(
            rows[-1]["assigned_at"] + timedelta(minutes=1),
            previous_decision + timedelta(minutes=1),
        )
        if assigned_at.date() > context.as_of_date:
            assigned_at = utc_at(context.as_of_date, 16 * 60)
        rows.append(
            _approval_row(
                claim_id,
                step.approver_id,
                index + 1,
                step.approver_type,
                ApprovalStepStatus.PENDING,
                assigned_at,
                None,
                employee.country.value,
                None,
            )
        )
    if final_status != ExpenseStatus.REJECTED and all(
        row["status"] == ApprovalStepStatus.APPROVED.value for row in rows
    ):
        final_status = ExpenseStatus.APPROVED
    return final_status, rows, last_decision, final_event_id


def _approval_row(
    request_id: str,
    approver_id: str | None,
    sequence: int,
    role: ApprovalRole,
    status: ApprovalStepStatus,
    assigned_at: datetime,
    decided_at: datetime | None,
    country: str,
    reason_code: str | None,
) -> Row:
    return {
        "approval_step_id": new_id(IdKind.APPROVAL_STEP, sequence, parent_id=request_id),
        "leave_request_id": None,
        "expense_claim_id": request_id,
        "step_number": sequence,
        "required_role": role.value,
        "approver_employee_id": approver_id,
        "status": status.value,
        "assigned_at": assigned_at,
        "due_date": add_workdays(assigned_at.date(), 3, country),
        "decided_at": decided_at,
        "reason_code": reason_code,
    }


def _create_split_findings(
    context: GenerationContext,
    claims: list[ExpenseClaim],
    totals: dict[str, Decimal],
) -> None:
    result = detect_split_claims(tuple(claims), totals)
    if not result.ok or result.value is None:
        raise ValueError(result.messages[0])
    seen: set[tuple[str, str]] = set()
    for pair in result.value:
        pair_key = (pair.first_claim_id, pair.second_claim_id)
        if pair_key in seen:
            continue
        seen.add(pair_key)
        for claim_id in pair_key:
            _add_finding(
                context,
                expense_claim_id=claim_id,
                finding_code="SPLIT_CLAIM",
                severity="WARNING",
                details={
                    "paired_claim_id": pair.second_claim_id
                    if claim_id == pair.first_claim_id
                    else pair.first_claim_id,
                    "boundary_usd": str(pair.boundary_usd),
                    "rule_ids": ["E10"],
                },
                detected_at=utc_at(date(2026, 10, 22), 16 * 60),
            )
            context.references.setdefault("split_claim_ids", set()).add(claim_id)


def _create_reimbursements(
    context: GenerationContext,
    claim_rows: list[Row],
    claim_totals: dict[str, Decimal],
    claim_models: list[ExpenseClaim],
    line_ids_by_claim: dict[str, list[str]],
    approval_rows_by_claim: dict[str, list[Row]],
    final_approval_by_claim: dict[str, datetime],
    paths_by_claim: dict[str, tuple[ApprovalPathStep, ...]],
    event_rows: list[Row],
    next_event_sequence: int,
    audit_rows: list[Row],
    audit_sequence: int,
) -> list[Row]:
    reimbursements: list[Row] = []
    claim_by_id = {claim.expense_claim_id: claim for claim in claim_models}
    claim_row_by_id = {row["expense_claim_id"]: row for row in claim_rows}
    for claim_id in sorted(final_approval_by_claim):
        claim = claim_by_id[claim_id]
        approval_rows = approval_rows_by_claim[claim_id]
        step_models = tuple(
            ApprovalStep(
                approver_type=ApprovalRole(row["required_role"]),
                status=ApprovalStepStatus(row["status"]),
            )
            for row in approval_rows
        )
        line_ids = set(line_ids_by_claim[claim_id])
        findings = tuple(
            OpenFinding(
                finding_code=FindingCode(row["finding_code"]),
                status=AuditFindingStatus.OPEN,
            )
            for row in context.references.get("finding_rows", [])
            if row["status"] == AuditFindingStatus.OPEN.value
            and (
                row["expense_claim_id"] == claim_id
                or row["expense_line_id"] in line_ids
                or row["approval_step_id"] in {step["approval_step_id"] for step in approval_rows}
            )
        )
        final_date = final_approval_by_claim[claim_id].date()
        eligible = check_reimbursement_eligibility(
            employee=claim.employee,
            amount_usd=claim_totals[claim_id],
            claim_status=ExpenseStatus.APPROVED,
            approval_steps=step_models,
            findings=findings,
            cost_center_id=claim.cost_center_id,
            existing_reimbursement_ids=(),
            final_approval_date=final_date,
            as_of_date=context.as_of_date,
        )
        value = eligible.value
        audit_rows.append(
            make_audit_row(
                context,
                audit_sequence,
                request_id=claim_id,
                request_type="EXPENSE",
                decision_kind="REIMBURSEMENT_ELIGIBILITY",
                inputs={
                    "status": ExpenseStatus.APPROVED.value,
                    "total_usd": claim_totals[claim_id],
                    "step_statuses": [step.status.value for step in step_models],
                    "cost_center_id": claim.cost_center_id,
                },
                outputs={
                    "eligible": False if value is None else value.eligible,
                    "reasons": [] if value is None else value.reasons,
                },
                matched_rule_ids=eligible.rule_ids,
                reason_codes=eligible.reason_codes,
                path=paths_by_claim[claim_id],
                recorded_at=final_approval_by_claim[claim_id],
            )
        )
        audit_sequence += 1
        if not eligible.ok or value is None or not value.eligible:
            continue
        if (
            value.payment_date is None
            or value.amount_home_currency is None
            or value.home_currency is None
            or value.status is None
        ):
            raise ValueError("eligible reimbursement is missing computed payment data")
        reimbursement_id = new_id(IdKind.REIMBURSEMENT, len(reimbursements) + 1)
        paid_at = (
            utc_at(value.payment_date, 12 * 60)
            if value.status == ReimbursementStatus.PAID
            else None
        )
        reimbursement = {
            "reimbursement_id": reimbursement_id,
            "expense_claim_id": claim_id,
            "amount_home_currency": value.amount_home_currency,
            "home_currency": value.home_currency,
            "payment_date": value.payment_date,
            "status": value.status.value,
            "created_at": final_approval_by_claim[claim_id],
            "paid_at": paid_at,
            "payment_reference": f"PAY-2026-{len(reimbursements) + 1:06d}",
        }
        reimbursements.append(reimbursement)
        claim_row_by_id[claim_id]["status"] = ExpenseStatus.REIMBURSED.value
        transition(ExpenseStatus.APPROVED, ExpenseStatus.REIMBURSED, RequestType.EXPENSE)
        next_claim_sequence = 1 + max(
            (row["sequence_number"] for row in event_rows if row["expense_claim_id"] == claim_id),
            default=0,
        )
        event_rows.append(
            {
                "event_id": new_id(IdKind.EXPENSE_CLAIM_EVENT, next_event_sequence),
                "expense_claim_id": claim_id,
                "sequence_number": next_claim_sequence,
                "event_type": "REIMBURSEMENT_CREATED",
                "from_status": ExpenseStatus.APPROVED.value,
                "to_status": ExpenseStatus.REIMBURSED.value,
                "occurred_at": final_approval_by_claim[claim_id],
                "actor_employee_id": None,
                "reason_code": None,
                "event_payload": event_payload(
                    reimbursement_id=reimbursement_id, status=value.status.value
                ),
            }
        )
        next_event_sequence += 1
        next_claim_sequence += 1
        if value.status == ReimbursementStatus.PAID and paid_at is not None:
            event_rows.append(
                {
                    "event_id": new_id(IdKind.EXPENSE_CLAIM_EVENT, next_event_sequence),
                    "expense_claim_id": claim_id,
                    "sequence_number": next_claim_sequence,
                    "event_type": "REIMBURSEMENT_PAID",
                    "from_status": ExpenseStatus.REIMBURSED.value,
                    "to_status": ExpenseStatus.REIMBURSED.value,
                    "occurred_at": paid_at,
                    "actor_employee_id": None,
                    "reason_code": None,
                    "event_payload": event_payload(
                        reimbursement_id=reimbursement_id,
                        prior_status=ReimbursementStatus.SCHEDULED.value,
                        status=ReimbursementStatus.PAID.value,
                    ),
                }
            )
            next_event_sequence += 1
    context.references["next_expense_event_sequence"] = next_event_sequence
    context.references["next_audit_sequence"] = audit_sequence
    return reimbursements


def _submission_date(index: int, total: int) -> date:
    return date(2026, 1, 2) + timedelta(days=index * 293 // max(total - 1, 1))
