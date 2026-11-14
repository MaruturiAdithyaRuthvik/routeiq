"""Explicit request lifecycle transitions (L7, E8)."""

from __future__ import annotations

from dataclasses import dataclass

from .models import ExpenseStatus, LeaveStatus, RequestType


class IllegalTransition(ValueError):
    """Raised when a request lifecycle edge is not explicitly permitted (L7, E8)."""

    def __init__(
        self,
        current: str,
        target: str,
        request_type: RequestType,
        rule_id: str,
    ) -> None:
        self.current = current
        self.target = target
        self.request_type = request_type
        self.reason_codes = ("ILLEGAL_TRANSITION",)
        self.rule_ids = (rule_id,)
        super().__init__(
            f"{request_type.value} lifecycle cannot transition from {current} to {target}."
        )


_LEAVE_TRANSITIONS = {
    LeaveStatus.DRAFT: frozenset({LeaveStatus.SUBMITTED}),
    LeaveStatus.SUBMITTED: frozenset({LeaveStatus.PENDING_APPROVAL}),
    LeaveStatus.PENDING_APPROVAL: frozenset(
        {LeaveStatus.APPROVED, LeaveStatus.REJECTED, LeaveStatus.CANCELLED}
    ),
    LeaveStatus.APPROVED: frozenset(),
    LeaveStatus.REJECTED: frozenset(),
    LeaveStatus.CANCELLED: frozenset(),
}

_EXPENSE_TRANSITIONS = {
    ExpenseStatus.DRAFT: frozenset({ExpenseStatus.SUBMITTED}),
    ExpenseStatus.SUBMITTED: frozenset({ExpenseStatus.PENDING_APPROVAL}),
    ExpenseStatus.PENDING_APPROVAL: frozenset(
        {ExpenseStatus.APPROVED, ExpenseStatus.REJECTED, ExpenseStatus.CANCELLED}
    ),
    ExpenseStatus.APPROVED: frozenset({ExpenseStatus.REIMBURSED}),
    ExpenseStatus.REJECTED: frozenset(),
    ExpenseStatus.CANCELLED: frozenset(),
    ExpenseStatus.REIMBURSED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class TransitionResult:
    request_type: RequestType
    from_status: str
    to_status: str
    reason_codes: tuple[str, ...]
    rule_ids: tuple[str, ...]
    message: str


def transition(
    current: LeaveStatus | ExpenseStatus | str,
    target: LeaveStatus | ExpenseStatus | str,
    request_type: RequestType,
) -> TransitionResult:
    """Apply one legal lifecycle edge or raise an explainable IllegalTransition (L7, E8)."""

    if request_type == RequestType.LEAVE:
        try:
            current_status = LeaveStatus(current)
            target_status = LeaveStatus(target)
        except ValueError as exc:
            raise IllegalTransition(str(current), str(target), request_type, "L7") from exc
        allowed = _LEAVE_TRANSITIONS[current_status]
        rule_id = "L7"
    else:
        try:
            current_status = ExpenseStatus(current)
            target_status = ExpenseStatus(target)
        except ValueError as exc:
            raise IllegalTransition(str(current), str(target), request_type, "E8") from exc
        allowed = _EXPENSE_TRANSITIONS[current_status]
        rule_id = "E8"
    if target_status not in allowed:
        raise IllegalTransition(
            current_status.value,
            target_status.value,
            request_type,
            rule_id,
        )
    return TransitionResult(
        request_type=request_type,
        from_status=current_status.value,
        to_status=target_status.value,
        reason_codes=("LIFECYCLE_TRANSITION",),
        rule_ids=(rule_id,),
        message=f"Applied legal {request_type.value} lifecycle transition.",
    )
