"""Leave request scenarios and append-only ledger generation through the engine."""

from __future__ import annotations

import random
from collections.abc import Callable
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.engine.calendar import business_days_between
from app.engine.ids import IdKind
from app.engine.leave import (
    ExistingLeaveRequest,
    LeaveRequestInput,
    balance_from_ledger,
    generate_leave_ledger_entries,
    leave_ledger_entries_for_transition,
    route_leave,
    validate_leave_request,
)
from app.engine.lifecycle import transition
from app.engine.models import (
    ApprovalPathStep,
    ApprovalStepStatus,
    AuditFindingStatus,
    Employee,
    LeaveLedgerEntry,
    LeaveStatus,
    RequestType,
)

from .context import GenerationContext, Row
from .helpers import add_workdays, make_audit_row, new_id, utc_at
from .tables import set_table

_ZERO = Decimal("0")
_POLICY_WEIGHTS = (
    ("LPO-001", 50),
    ("LPO-002", 20),
    ("LPO-003", 20),
    ("LPO-004", 2),
    ("LPO-005", 3),
    ("LPO-006", 5),
)


def generate_leave_data(context: GenerationContext) -> None:
    """Create opening/accrual ledger, then validate, route, and process leave requests."""

    ledger_models: list[LeaveLedgerEntry] = []
    ledger_rows: list[Row] = []
    next_ledger = 1
    employees: dict[str, Employee] = context.references["employees"]
    for employee_id in sorted(employees):
        employee = employees[employee_id]
        for policy_id in sorted(context.references["leave_policies"]):
            policy = context.references["leave_policies"][policy_id]
            prior_closing = _prior_year_closing(employee, policy_id)
            generated = generate_leave_ledger_entries(
                employee,
                policy,
                prior_closing,
                as_of_date=context.as_of_date,
                first_sequence=next_ledger,
            )
            if not generated.ok or generated.value is None:
                raise ValueError(generated.messages[0])
            for entry in generated.value:
                ledger_models.append(entry)
                ledger_rows.append(_ledger_row(entry))
            next_ledger += len(generated.value)

    context.references["ledger_models"] = ledger_models
    context.references["ledger_rows"] = ledger_rows
    context.references["next_ledger_sequence"] = next_ledger

    people = tuple(employees[key] for key in sorted(employees))
    recent_employee_id = _recent_balance_employee_id(context)
    overlap_employee_id = _overlap_employee_id(context)
    context.references["recent_balance_employee_id"] = recent_employee_id
    context.references["overlap_employee_id"] = overlap_employee_id

    request_rows: list[Row] = []
    event_rows: list[Row] = []
    existing: list[ExistingLeaveRequest] = []
    validation_findings: dict[str, list[str]] = {}
    leave_audits: list[Row] = []
    seed_rng: random.Random = context.rng
    event_sequence = 1
    audit_sequence = int(context.references.get("next_audit_sequence", 1))
    leave_paths: dict[str, tuple[ApprovalPathStep, ...]] = {}

    for sequence in range(1, context.preset.leave_requests + 1):
        request_id = new_id(IdKind.LEAVE_REQUEST, sequence)
        submit_date = _submission_date(sequence - 1, context.preset.leave_requests)
        employee, policy_id, start_date, end_date = _leave_scenario(
            context,
            sequence,
            submit_date,
            people,
            recent_employee_id,
            overlap_employee_id,
        )
        policy = context.references["leave_policies"][policy_id]
        requested = business_days_between(start_date, end_date, employee.country)
        if requested.value is None:
            raise ValueError(requested.messages[0])
        available = _current_available(context, employee.employee_id, policy_id)
        request_input = LeaveRequestInput(
            employee=employee,
            policy=policy,
            start_date=start_date,
            end_date=end_date,
            available_days=available,
            existing_requests=tuple(existing),
        )
        if sequence == 52:
            request_input = LeaveRequestInput(
                employee=employee,
                policy=policy,
                start_date=start_date,
                end_date=end_date,
                available_days=available,
                existing_requests=(),
            )

        validation = validate_leave_request(request_input)
        if validation.value is None:
            raise ValueError(validation.messages[0])
        business_days = validation.value.business_days
        submit_time = utc_at(submit_date, 9 * 60 + (sequence % 12) * 20)
        created_at = submit_time - timedelta(minutes=1)
        request_events: list[Row] = []

        def append_event(
            event_type: str,
            from_status: str | None,
            to_status: str | None,
            occurred_at: datetime,
            reason_code: str | None = None,
            actor_employee_id: str | None = None,
            events: list[Row] = request_events,
            parent_id: str = request_id,
            default_actor_id: str = employee.employee_id,
        ) -> str:
            nonlocal event_sequence
            event_id = new_id(IdKind.LEAVE_REQUEST_EVENT, event_sequence)
            event_sequence += 1
            events.append(
                {
                    "event_id": event_id,
                    "leave_request_id": parent_id,
                    "sequence_number": len(events) + 1,
                    "event_type": event_type,
                    "from_status": from_status,
                    "to_status": to_status,
                    "occurred_at": occurred_at,
                    "actor_employee_id": actor_employee_id or default_actor_id,
                    "reason_code": reason_code,
                }
            )
            return event_id

        append_event("CREATED", None, "DRAFT", created_at)
        request_status = LeaveStatus.DRAFT
        resolved_path: tuple[ApprovalPathStep, ...] = ()
        submit_audit = make_audit_row(
            context,
            audit_sequence,
            request_id=request_id,
            request_type="LEAVE",
            decision_kind="SUBMIT_VALIDATION",
            inputs={
                "employee_id": employee.employee_id,
                "policy_id": policy_id,
                "start_date": start_date,
                "end_date": end_date,
                "available_days": available,
                "existing_request_count": len(request_input.existing_requests),
            },
            outputs={
                "valid": validation.ok,
                "business_days": business_days,
                "reason_codes": validation.reason_codes,
            },
            matched_rule_ids=validation.rule_ids,
            reason_codes=validation.reason_codes,
            recorded_at=submit_time,
        )
        leave_audits.append(submit_audit)
        audit_sequence += 1
        if not validation.ok:
            rejection_code = validation.reason_codes[0]
            append_event("SUBMISSION_ATTEMPT", "DRAFT", "DRAFT", submit_time, rejection_code)
            validation_findings[request_id] = [rejection_code]
            _add_finding(
                context,
                leave_request_id=request_id,
                finding_code=rejection_code,
                severity="ERROR",
                details={"message": validation.messages[0], "rule_ids": list(validation.rule_ids)},
                detected_at=submit_time,
            )
        else:
            submitted_event_id = append_event("SUBMITTED", "DRAFT", "SUBMITTED", submit_time)
            transition(request_status, LeaveStatus.SUBMITTED, RequestType.LEAVE)
            request_status = LeaveStatus.SUBMITTED
            append_event(
                "APPROVAL_STARTED",
                "SUBMITTED",
                "PENDING_APPROVAL",
                submit_time + timedelta(minutes=1),
            )
            transition(request_status, LeaveStatus.PENDING_APPROVAL, RequestType.LEAVE)
            request_status = LeaveStatus.PENDING_APPROVAL

            reserve = leave_ledger_entries_for_transition(
                employee_id=employee.employee_id,
                policy=policy,
                leave_request_id=request_id,
                requested_days=Decimal(business_days),
                target_status=LeaveStatus.SUBMITTED,
                entry_date=submit_date,
                first_sequence=int(context.references["next_ledger_sequence"]),
            )
            if not reserve.ok or reserve.value is None:
                raise ValueError(reserve.messages[0])
            _append_ledger(context, reserve.value, request_id, submitted_event_id)

            routed = route_leave(policy, business_days)
            if not routed.ok or routed.value is None:
                raise ValueError(routed.messages[0])
            resolved = resolve_approver_path(
                context, routed.value, employee, request_type="LEAVE", on_date=submit_date
            )
            resolved_path = resolved
            leave_paths[request_id] = resolved_path
            if any(
                step.approver_id is None and step.approver_type.value != "SYSTEM"
                for step in resolved
            ):
                _add_finding(
                    context,
                    leave_request_id=request_id,
                    finding_code="UNRESOLVED_APPROVER",
                    severity="ERROR",
                    details={"rule_ids": ["G5", "E7", "AU3"]},
                    detected_at=submit_time,
                )
                validation_findings.setdefault(request_id, []).append("UNRESOLVED_APPROVER")

            route_audit = make_audit_row(
                context,
                audit_sequence,
                request_id=request_id,
                request_type="LEAVE",
                decision_kind="ROUTING",
                inputs={
                    "employee_id": employee.employee_id,
                    "policy_id": policy_id,
                    "business_days": business_days,
                    "start_date": start_date,
                    "end_date": end_date,
                    "country": employee.country.value,
                },
                outputs={"path": resolved_path},
                matched_rule_ids=tuple(sorted(set(routed.rule_ids + resolved_rule_ids(resolved)))),
                reason_codes=tuple(code for step in resolved for code in step.reason_codes),
                path=resolved_path,
                recorded_at=submit_time,
            )
            leave_audits.append(route_audit)
            audit_sequence += 1

            outcome = _leave_outcome(context, sequence, seed_rng)
            final_status, step_rows, last_decided_at, decided_event_id = _process_leave_steps(
                context,
                request_id,
                employee,
                submit_date,
                submit_time,
                resolved_path,
                outcome,
                append_event,
            )
            request_status = final_status
            context.references.setdefault("approval_step_rows", []).extend(step_rows)
            if final_status in (LeaveStatus.APPROVED, LeaveStatus.REJECTED):
                transition(LeaveStatus.PENDING_APPROVAL, final_status, RequestType.LEAVE)
                if last_decided_at is None:
                    raise ValueError("terminal leave request lacks a decision timestamp")
                ledger_effect = leave_ledger_entries_for_transition(
                    employee_id=employee.employee_id,
                    policy=policy,
                    leave_request_id=request_id,
                    requested_days=Decimal(business_days),
                    target_status=final_status,
                    entry_date=last_decided_at.date(),
                    first_sequence=int(context.references["next_ledger_sequence"]),
                )
                if not ledger_effect.ok or ledger_effect.value is None:
                    raise ValueError(ledger_effect.messages[0])
                _append_ledger(context, ledger_effect.value, request_id, decided_event_id)

            if final_status != LeaveStatus.PENDING_APPROVAL:
                approval_audit = make_audit_row(
                    context,
                    audit_sequence,
                    request_id=request_id,
                    request_type="LEAVE",
                    decision_kind="APPROVAL",
                    inputs={"leave_request_id": request_id, "business_days": business_days},
                    outputs={"status": final_status.value},
                    matched_rule_ids=("L5", "L6", "L7", "AU3"),
                    reason_codes=tuple(
                        code for step in resolved_path for code in step.reason_codes
                    ),
                    path=resolved_path,
                    recorded_at=last_decided_at or submit_time,
                )
                leave_audits.append(approval_audit)
                audit_sequence += 1

        request_rows.append(
            {
                "leave_request_id": request_id,
                "employee_id": employee.employee_id,
                "leave_policy_id": policy_id,
                "start_date": start_date,
                "end_date": end_date,
                "business_days": business_days,
                "status": request_status.value,
                "submitted_at": submit_time if validation.ok else None,
                "medical_certificate_required": validation.value.medical_certificate_required,
                "risk_score": 0,
                "reason": "Synthetic scenario generated by RouteIQ datagen.",
            }
        )
        event_rows.extend(request_events)
        if request_status != LeaveStatus.DRAFT:
            existing.append(
                ExistingLeaveRequest(employee.employee_id, start_date, end_date, request_status)
            )

    context.references["leave_request_rows"] = request_rows
    context.references["leave_event_rows"] = event_rows
    context.references["leave_audit_rows"] = leave_audits
    context.references.setdefault("decision_audit_rows", []).extend(leave_audits)
    context.references["leave_findings_by_request"] = validation_findings
    context.references["leave_paths"] = leave_paths
    context.references["next_audit_sequence"] = audit_sequence
    context.references["next_leave_event_sequence"] = event_sequence
    set_table(context, "leave_request", request_rows)
    set_table(context, "leave_request_event", event_rows)
    set_table(context, "leave_ledger_entry", context.references["ledger_rows"])
    set_table(context, "decision_audit", leave_audits)


def _employee_by_id(context: GenerationContext, employee_id: str) -> Employee:
    return context.references["employees"][employee_id]


def _prior_year_closing(employee: Employee, policy_id: str) -> Decimal:
    if policy_id != "LPO-001" or employee.hire_date.year >= 2026:
        return _ZERO
    return Decimal(int(employee.employee_id[-6:]) % 13)


def _recent_balance_employee_id(context: GenerationContext) -> str:
    candidates = [
        employee
        for employee in context.references["employees"].values()
        if employee.hire_date.year == 2026 and employee.termination_date is None
    ]
    if not candidates:
        raise ValueError("master stage must produce active 2026 hires")
    selected = min(candidates, key=lambda employee: employee.employee_id)
    return selected.employee_id


def _overlap_employee_id(context: GenerationContext) -> str:
    assignment_by_id = {row["employee_id"]: row for row in context.get_rows("employee")}
    candidates = [
        employee
        for employee in context.references["employees"].values()
        if employee.manager_id is not None
        and employee.hire_date <= date(2026, 7, 6)
        and (employee.termination_date is None or employee.termination_date >= date(2026, 7, 7))
    ]
    requesters = [
        employee
        for employee in candidates
        if employee.employee_id
        in {
            employee_id
            for employee_id, row in assignment_by_id.items()
            if row["system_role"] == "REQUESTER"
        }
    ]
    return min(requesters or candidates, key=lambda employee: employee.employee_id).employee_id


def _submission_date(index: int, total: int) -> date:
    return date(2026, 1, 1) + timedelta(days=index * 294 // max(total - 1, 1))


def _leave_scenario(
    context: GenerationContext,
    sequence: int,
    submit_date: date,
    people: tuple[Employee, ...],
    recent_employee_id: str,
    overlap_employee_id: str,
) -> tuple[Employee, str, date, date]:
    rng = context.rng
    if sequence == 1:
        employee = rng.choice(people)
        return employee, "LPO-001", date(2026, 2, 14), date(2026, 2, 15)
    if sequence == 2:
        return (
            _employee_by_id(context, recent_employee_id),
            "LPO-001",
            date(2026, 10, 5),
            date(2026, 10, 14),
        )
    if sequence == 3:
        employee = min(
            (item for item in people if item.country.value == "IN"),
            key=lambda item: item.employee_id,
        )
        return employee, "LPO-001", date(2026, 10, 9), date(2026, 10, 13)
    if sequence == 4:
        employee = min(
            (item for item in people if item.country.value == "US"),
            key=lambda item: item.employee_id,
        )
        return employee, "LPO-001", date(2026, 12, 30), date(2026, 12, 31)
    if sequence in (51, 52):
        return (
            _employee_by_id(context, overlap_employee_id),
            "LPO-006",
            date(2026, 7, 6),
            date(2026, 7, 7),
        )

    policy_id = rng.choices(
        [policy for policy, _weight in _POLICY_WEIGHTS],
        weights=[weight for _policy, weight in _POLICY_WEIGHTS],
        k=1,
    )[0]
    employee = rng.choice(
        tuple(person for person in people if person.employee_id != overlap_employee_id)
    )
    lower = max(date(2026, 1, 1), employee.hire_date)
    upper = min(date(2026, 12, 31), employee.termination_date or date(2026, 12, 31))
    if lower > upper:
        lower = upper
    start = _select_leave_start(rng, lower, upper, policy_id, submit_date)
    target_days = _leave_length(rng, policy_id)
    end = _end_for_business_days(start, target_days, employee)
    if end > upper:
        end = upper
    return employee, policy_id, start, end


def _select_leave_start(
    rng: random.Random, lower: date, upper: date, policy_id: str, submit_date: date
) -> date:
    if lower > upper:
        return upper
    month_weights = (
        (1, 1, 1, 1, 1, 2, 4, 3, 1, 1, 2, 5)
        if policy_id == "LPO-001"
        else (1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2)
    )
    months = [month for month in range(1, 13) if date(2026, month, 1) <= upper]
    weights = [month_weights[month - 1] for month in months]
    month = rng.choices(months, weights=weights, k=1)[0]
    month_start = max(lower, date(2026, month, 1))
    month_end = min(upper, date(2026, month, _month_days(2026, month)))
    if month_start > month_end:
        return lower
    selected = month_start + timedelta(days=rng.randint(0, (month_end - month_start).days))
    if selected < submit_date - timedelta(days=60):
        recent_start = submit_date - timedelta(days=30)
        if recent_start >= lower:
            return min(recent_start, upper)
    return selected


def _leave_length(rng: random.Random, policy_id: str) -> int:
    if policy_id == "LPO-001":
        return rng.choices((2, 3, 5, 8, 12), weights=(2, 3, 4, 3, 1), k=1)[0]
    if policy_id == "LPO-002":
        return rng.choices((1, 2, 3, 5, 8), weights=(4, 4, 3, 2, 1), k=1)[0]
    if policy_id == "LPO-003":
        return rng.choice((1, 2, 3))
    if policy_id == "LPO-004":
        return rng.choice((20, 45, 60, 90))
    if policy_id == "LPO-005":
        return rng.randint(1, 5)
    return rng.randint(1, 10)


def _end_for_business_days(start: date, count: int, employee: Employee) -> date:
    current = start
    last = start
    while current <= date(2026, 12, 31):
        result = business_days_between(start, current, employee.country)
        if result.value is not None and result.value.count >= count:
            return current
        last = current
        current += timedelta(days=1)
    return last


def _month_days(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - timedelta(days=1)).day


def _current_available(context: GenerationContext, employee_id: str, policy_id: str) -> Decimal:
    entries = tuple(
        entry
        for entry in context.references["ledger_models"]
        if entry.employee_id == employee_id and entry.leave_policy_id == policy_id
    )
    balance = balance_from_ledger(entries, policy_id=policy_id)
    if balance.value is None:
        raise ValueError(balance.messages[0])
    return balance.value


def _leave_outcome(context: GenerationContext, sequence: int, rng: random.Random) -> str:
    if sequence in (51, 52):
        return "APPROVE"
    return rng.choices(("APPROVE", "REJECT", "PENDING"), weights=(88, 6, 6), k=1)[0]


def _process_leave_steps(
    context: GenerationContext,
    request_id: str,
    employee: Employee,
    submit_date: date,
    submitted_at: datetime,
    path: tuple[ApprovalPathStep, ...],
    outcome: str,
    append_event: Callable[..., str],
) -> tuple[LeaveStatus, list[Row], datetime | None, str | None]:

    if not path:
        return LeaveStatus.PENDING_APPROVAL, [], None, None
    steps: list[Row] = []
    last_decided: datetime | None = None
    final_event_id: str | None = None
    reject_at = context.rng.randrange(len(path)) if outcome == "REJECT" else -1
    pending_after = context.rng.randrange(len(path)) if outcome == "PENDING" else len(path)
    previous_decision = submitted_at + timedelta(minutes=2)
    request_final = LeaveStatus.PENDING_APPROVAL
    for index, resolved in enumerate(path):
        assigned_at = previous_decision + timedelta(minutes=1)
        if assigned_at.date() > context.as_of_date:
            assigned_at = utc_at(context.as_of_date, 16 * 60)
        due_date = add_workdays(assigned_at.date(), 3, employee.country.value)
        status = ApprovalStepStatus.PENDING
        decided_at: datetime | None = None
        reason_code = None
        rejected = outcome == "REJECT" and index == reject_at
        should_decide = (
            outcome == "APPROVE"
            or (outcome == "REJECT" and index <= reject_at)
            or (outcome == "PENDING" and index < pending_after)
        )
        if should_decide and resolved.approver_id is not None:
            delay = context.rng.choices((1, 2, 3, 4), weights=(2, 4, 3, 1), k=1)[0]
            decision_date = add_workdays(assigned_at.date(), delay, employee.country.value)
            decision_time = utc_at(decision_date, 15 * 60 + index * 5)
            if decision_date <= context.as_of_date:
                status = ApprovalStepStatus.REJECTED if rejected else ApprovalStepStatus.APPROVED
                decided_at = decision_time
                last_decided = decision_time
                previous_decision = decision_time
                terminal = rejected or (outcome == "APPROVE" and index == len(path) - 1)
                final_event_id = append_event(  # type: ignore[operator]
                    "APPROVAL_DECIDED",
                    "PENDING_APPROVAL",
                    "REJECTED" if rejected else "APPROVED" if terminal else "PENDING_APPROVAL",
                    decision_time,
                    reason_code,
                    resolved.approver_id,
                )
                if rejected:
                    request_final = LeaveStatus.REJECTED
            else:
                should_decide = False
        steps.append(
            {
                "approval_step_id": new_id(IdKind.APPROVAL_STEP, index + 1, parent_id=request_id),
                "leave_request_id": request_id,
                "expense_claim_id": None,
                "step_number": index + 1,
                "required_role": resolved.approver_type.value,
                "approver_employee_id": resolved.approver_id,
                "status": status.value,
                "assigned_at": assigned_at,
                "due_date": due_date,
                "decided_at": decided_at,
                "reason_code": reason_code,
            }
        )
        if rejected or status != ApprovalStepStatus.APPROVED:
            break
    while len(steps) < len(path):
        index = len(steps)
        resolved = path[index]
        assigned_at = max(
            steps[-1]["assigned_at"] + timedelta(minutes=1),
            previous_decision + timedelta(minutes=1),
        )
        if assigned_at.date() > context.as_of_date:
            assigned_at = utc_at(context.as_of_date, 16 * 60)
        steps.append(
            {
                "approval_step_id": new_id(IdKind.APPROVAL_STEP, index + 1, parent_id=request_id),
                "leave_request_id": request_id,
                "expense_claim_id": None,
                "step_number": index + 1,
                "required_role": resolved.approver_type.value,
                "approver_employee_id": resolved.approver_id,
                "status": ApprovalStepStatus.PENDING.value,
                "assigned_at": assigned_at,
                "due_date": add_workdays(assigned_at.date(), 3, employee.country.value),
                "decided_at": None,
                "reason_code": None,
            }
        )
    if request_final != LeaveStatus.REJECTED and all(
        step["status"] == ApprovalStepStatus.APPROVED.value for step in steps
    ):
        request_final = LeaveStatus.APPROVED
    return request_final, steps, last_decided, final_event_id


def resolve_approver_path(
    context: GenerationContext,
    path: tuple[ApprovalPathStep, ...],
    employee: Employee,
    *,
    request_type: str,
    on_date: date,
    cost_center_id: str | None = None,
) -> tuple[ApprovalPathStep, ...]:
    from app.engine.resolver import resolve_approvers

    resolved = resolve_approvers(
        path,
        employee,
        context.references["organization"],
        request_type=RequestType(request_type),
        cost_center_id=cost_center_id,
        on_date=on_date,
    )
    if resolved.value is None:
        raise ValueError(resolved.messages[0])
    return resolved.value


def resolved_rule_ids(path: tuple[ApprovalPathStep, ...]) -> tuple[str, ...]:
    return tuple(sorted({rule_id for step in path for rule_id in step.rule_ids}))


def _append_ledger(
    context: GenerationContext,
    entries: tuple[LeaveLedgerEntry, ...],
    request_id: str | None,
    source_event_id: str | None,
) -> None:
    rows: list[Row] = context.references["ledger_rows"]
    models: list[LeaveLedgerEntry] = context.references["ledger_models"]
    for entry in entries:
        models.append(entry)
        row = _ledger_row(entry)
        row["leave_request_id"] = request_id
        row["source_event_id"] = source_event_id
        rows.append(row)
    context.references["next_ledger_sequence"] = int(
        context.references["next_ledger_sequence"]
    ) + len(entries)


def _ledger_row(entry: LeaveLedgerEntry) -> Row:
    return {
        "leave_ledger_entry_id": entry.leave_ledger_entry_id,
        "employee_id": entry.employee_id,
        "leave_policy_id": entry.leave_policy_id,
        "leave_request_id": entry.leave_request_id,
        "entry_type": entry.entry_type.value,
        "effect_bucket": entry.effect_bucket.value,
        "delta_days": entry.delta_days,
        "prior_year_closing_days": entry.prior_year_closing_days,
        "entry_date": entry.entry_date,
        "reversal_of_entry_id": entry.reversal_of_entry_id,
        "source_event_id": None,
    }


def _add_finding(
    context: GenerationContext,
    *,
    finding_code: str,
    severity: str,
    detected_at: datetime,
    details: dict[str, object],
    leave_request_id: str | None = None,
    expense_claim_id: str | None = None,
    expense_line_id: str | None = None,
    approval_step_id: str | None = None,
    reimbursement_id: str | None = None,
) -> str:
    rows: list[Row] = context.references.setdefault("finding_rows", [])
    finding_id = new_id(IdKind.AUDIT_FINDING, len(rows) + 1)
    rows.append(
        {
            "audit_finding_id": finding_id,
            "leave_request_id": leave_request_id,
            "expense_claim_id": expense_claim_id,
            "expense_line_id": expense_line_id,
            "approval_step_id": approval_step_id,
            "reimbursement_id": reimbursement_id,
            "finding_code": finding_code,
            "severity": severity,
            "status": AuditFindingStatus.OPEN.value,
            "details": details,
            "detected_at": detected_at,
        }
    )
    return finding_id


def rebuild_leave_balances(context: GenerationContext) -> None:
    """Reconcile snapshots from the complete ledger, including injected adjustments."""

    rows: list[Row] = []
    all_entries: list[LeaveLedgerEntry] = context.references["ledger_models"]
    entries_by_key: dict[tuple[str, str], list[LeaveLedgerEntry]] = {}
    for entry in all_entries:
        entries_by_key.setdefault((entry.employee_id, entry.leave_policy_id), []).append(entry)
    for employee_id in sorted(context.references["employees"]):
        for policy_id in sorted(context.references["leave_policies"]):
            entries = tuple(entries_by_key.get((employee_id, policy_id), ()))
            opening = sum(
                (entry.delta_days for entry in entries if entry.entry_type.value == "OPENING"),
                _ZERO,
            )
            accrued = sum(
                (entry.delta_days for entry in entries if entry.entry_type.value == "ACCRUAL"),
                _ZERO,
            )
            adjustments = sum(
                (
                    entry.delta_days
                    for entry in entries
                    if entry.entry_type.value == "ADJUSTMENT"
                    or (
                        entry.entry_type.value == "REVERSAL"
                        and entry.effect_bucket.value == "AVAILABLE"
                    )
                ),
                _ZERO,
            )
            used = sum(
                (
                    entry.delta_days
                    for entry in entries
                    if entry.entry_type.value == "DEBIT"
                    or (
                        entry.entry_type.value == "REVERSAL" and entry.effect_bucket.value == "USED"
                    )
                ),
                _ZERO,
            )
            pending = sum(
                (
                    entry.delta_days
                    for entry in entries
                    if entry.entry_type.value in ("RESERVE", "RELEASE")
                    or (
                        entry.entry_type.value == "REVERSAL"
                        and entry.effect_bucket.value == "RESERVED"
                    )
                ),
                _ZERO,
            )
            available = balance_from_ledger(entries, policy_id=policy_id)
            if available.value is None:
                raise ValueError(available.messages[0])
            rows.append(
                {
                    "leave_balance_id": f"LBL-{employee_id}-{policy_id}-2026",
                    "employee_id": employee_id,
                    "leave_policy_id": policy_id,
                    "balance_year": 2026,
                    "as_of_date": context.as_of_date,
                    "opening_days": opening,
                    "accrued_days": accrued,
                    "adjustments_days": adjustments,
                    "used_days": used,
                    "pending_days": pending,
                    "available_days": available.value,
                }
            )
    set_table(context, "leave_balance", rows)
    set_table(context, "leave_ledger_entry", context.references["ledger_rows"])
