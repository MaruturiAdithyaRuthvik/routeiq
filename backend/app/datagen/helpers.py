"""Shared deterministic serialization and provenance helpers."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from app.engine.calendar import add_business_days
from app.engine.decision import create_decision_trace
from app.engine.ids import IdKind, format_id
from app.engine.models import ApprovalPathStep, CountryCode

from .context import GenerationContext, Row

DOCUMENTED_REASON_CODES = frozenset(
    {
        "INVALID_DATE_RANGE",
        "ZERO_BUSINESS_DAYS",
        "EMPLOYEE_NOT_ACTIVE",
        "TENURE_INELIGIBLE",
        "MAX_CONSECUTIVE_DAYS",
        "OVERLAP",
        "INSUFFICIENT_BALANCE",
        "LEAVE_UNPAID",
        "LEAVE_DAYS_1_3",
        "LEAVE_DAYS_4_10",
        "LEAVE_DAYS_GT_10",
        "PARENTAL_LEAVE",
        "EXPENSE_LT_50_AUTO",
        "EXPENSE_LT_50_FLAGGED",
        "EXPENSE_50_1000",
        "EXPENSE_1000_5000",
        "EXPENSE_5000_20000",
        "EXPENSE_GTE_20000",
        "AIRFARE_INTERNATIONAL",
        "CLIENT_ENTERTAINMENT_GT_250",
        "GIFT_GT_250",
        "POLICY_LIMIT_BREACH",
        "MISSING_RECEIPT",
        "DUPLICATE_RECEIPT",
        "MISSING_COST_CENTER",
        "DATE_OUTSIDE_EMPLOYMENT",
        "FUTURE_EXPENSE_DATE",
        "SPLIT_CLAIM",
        "SELF_APPROVAL_PREVENTED",
        "UNRESOLVED_APPROVER",
        "CEO_MANAGER_FALLBACK",
        "DUPLICATE_REIMBURSEMENT",
    }
)


def new_id(kind: IdKind, sequence: int, *, parent_id: str | None = None) -> str:
    result = format_id(kind, sequence, parent_id=parent_id)
    if result.value is None:
        raise ValueError(result.messages[0])
    return result.value


def utc_at(day: date, minute_of_day: int = 9 * 60) -> datetime:
    return datetime.combine(day, time.min, tzinfo=UTC) + timedelta(minutes=minute_of_day)


def add_workdays(start: date, count: int, country: str) -> date:
    result = add_business_days(start, count, CountryCode(country))
    if result.value is None:
        raise ValueError(result.messages[0])
    return result.value


def clean_codes(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(sorted({value for value in values if value in DOCUMENTED_REASON_CODES}))


def make_audit_row(
    context: GenerationContext,
    sequence: int,
    *,
    request_id: str,
    request_type: str,
    decision_kind: str,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    matched_rule_ids: tuple[str, ...],
    reason_codes: tuple[str, ...],
    path: tuple[ApprovalPathStep, ...] = (),
    recorded_at: datetime,
) -> Row:
    trace_result = create_decision_trace(
        inputs_snapshot=inputs,
        outputs_snapshot=outputs,
        matched_rule_ids=tuple(sorted(set(matched_rule_ids))),
        reason_codes=clean_codes(reason_codes),
        path=path,
    )
    if trace_result.value is None:
        raise ValueError(trace_result.messages[0])
    trace = trace_result.value
    return {
        "decision_audit_id": new_id(IdKind.DECISION_AUDIT, sequence),
        "leave_request_id": request_id if request_type == "LEAVE" else None,
        "expense_claim_id": request_id if request_type == "EXPENSE" else None,
        "decision_kind": decision_kind,
        "inputs_snapshot": trace.inputs_snapshot,
        "outputs_snapshot": trace.outputs_snapshot,
        "matched_rule_ids": list(trace.matched_rule_ids),
        "reason_codes": list(trace.reason_codes),
        "computed_path": list(trace.path),
        "engine_version": trace.engine_version,
        "recorded_at": recorded_at,
    }


def event_payload(**values: Any) -> dict[str, Any]:
    return {key: value for key, value in sorted(values.items())}
