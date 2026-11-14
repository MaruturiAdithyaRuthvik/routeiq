"""Pure approval-role resolution against a deterministic organization snapshot (G5, E7)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Final

from .calendar import AS_OF_DATE
from .models import (
    ApprovalPathStep,
    ApprovalRole,
    Employee,
    FunctionalRole,
    OrganizationSnapshot,
    RequestType,
    SystemRole,
)
from .results import RuleResult, failure, success

_FUNCTIONAL_ROLE_FOR_APPROVAL: Final = {
    ApprovalRole.DEPT_HEAD: FunctionalRole.DEPT_HEAD,
    ApprovalRole.HR_PARTNER: FunctionalRole.HR_PARTNER,
    ApprovalRole.FINANCE_CONTROLLER: FunctionalRole.FINANCE_CONTROLLER,
    ApprovalRole.CFO: FunctionalRole.CFO,
    ApprovalRole.COMPLIANCE_OFFICER: FunctionalRole.COMPLIANCE_OFFICER,
}


def _active(employee: Employee, on_date: date) -> bool:
    return employee.hire_date <= on_date and (
        employee.termination_date is None or on_date <= employee.termination_date
    )


def _valid_approver(
    organization: OrganizationSnapshot,
    employee_id: str | None,
    on_date: date,
    *,
    excluded_employee_id: str,
) -> Employee | None:
    if employee_id is None:
        return None
    employee = next(
        (item for item in organization.employees if item.employee_id == employee_id), None
    )
    if (
        employee is None
        or employee.system_role != SystemRole.APPROVER
        or not _active(employee, on_date)
    ):
        return None
    if employee.employee_id == excluded_employee_id:
        return employee
    return employee


def _designated(
    organization: OrganizationSnapshot,
    role: ApprovalRole,
    on_date: date,
    requester_id: str,
) -> Employee | None:
    candidates: list[tuple[int, str, Employee]] = []
    for designation in organization.designated_approvers:
        if designation.role != role or not (
            designation.effective_from <= on_date
            and (designation.effective_to is None or on_date < designation.effective_to)
        ):
            continue
        employee = _valid_approver(
            organization,
            designation.employee_id,
            on_date,
            excluded_employee_id=requester_id,
        )
        if employee is not None and employee.functional_role == _FUNCTIONAL_ROLE_FOR_APPROVAL[role]:
            candidates.append((designation.priority, employee.employee_id, employee))
    if not candidates:
        return None
    distinct_candidates = [item for item in candidates if item[2].employee_id != requester_id]
    return min(distinct_candidates or candidates, key=lambda item: (item[0], item[1]))[2]


def _chro(organization: OrganizationSnapshot, requester_id: str, on_date: date) -> Employee | None:
    if organization.chro_employee_id == requester_id:
        return None
    return _valid_approver(
        organization,
        organization.chro_employee_id,
        on_date,
        excluded_employee_id=requester_id,
    )


def _resolve_role(
    role: ApprovalRole,
    requester: Employee,
    organization: OrganizationSnapshot,
    on_date: date,
    request_type: RequestType,
    cost_center_id: str | None,
) -> tuple[Employee | None, tuple[str, ...]]:
    if role == ApprovalRole.SYSTEM:
        return None, ("SYSTEM_AUTO_APPROVAL",)
    if role == ApprovalRole.MANAGER:
        if requester.is_ceo:
            return _chro(organization, requester.employee_id, on_date), ("CEO_MANAGER_FALLBACK",)
        manager = _valid_approver(
            organization,
            requester.manager_id,
            on_date,
            excluded_employee_id=requester.employee_id,
        )
        return manager, ()
    if role == ApprovalRole.HR_PARTNER:
        candidates = [
            employee
            for employee in organization.employees
            if employee.country == requester.country
            and employee.functional_role == FunctionalRole.HR_PARTNER
            and _active(employee, on_date)
            and employee.system_role == SystemRole.APPROVER
        ]
        if not candidates:
            return None, ()
        distinct_candidates = [
            employee for employee in candidates if employee.employee_id != requester.employee_id
        ]
        selected = min(distinct_candidates or candidates, key=lambda employee: employee.employee_id)
        return selected, ()
    if role == ApprovalRole.DEPT_HEAD:
        owner_id: str | None = None
        if request_type == RequestType.EXPENSE:
            center = next(
                (
                    item
                    for item in organization.cost_centers
                    if item.cost_center_id == cost_center_id
                ),
                None,
            )
            owner_id = center.owner_employee_id if center is not None else None
        else:
            assignments = [
                assignment
                for assignment in organization.cost_center_assignments
                if assignment.employee_id == requester.employee_id
                and assignment.effective_from <= on_date
                and (assignment.effective_to is None or on_date < assignment.effective_to)
            ]
            assignments.sort(key=lambda item: (-item.allocation_pct, item.cost_center_id))
            if assignments:
                center = next(
                    (
                        item
                        for item in organization.cost_centers
                        if item.cost_center_id == assignments[0].cost_center_id
                    ),
                    None,
                )
                owner_id = center.owner_employee_id if center is not None else None
        employee = _valid_approver(
            organization,
            owner_id,
            on_date,
            excluded_employee_id=requester.employee_id,
        )
        if employee is not None and employee.functional_role == FunctionalRole.DEPT_HEAD:
            return employee, ()
        return None, ()
    designated = _designated(organization, role, on_date, requester.employee_id)
    return designated, ()


def resolve_approvers(
    path: tuple[ApprovalPathStep, ...],
    requester: Employee,
    organization: OrganizationSnapshot,
    *,
    request_type: RequestType,
    cost_center_id: str | None = None,
    on_date: date = AS_OF_DATE,
) -> RuleResult[tuple[ApprovalPathStep, ...]]:
    """Resolve each role; escalate self-approval and retain unresolved steps (G5, E7, AU3)."""

    resolved: list[ApprovalPathStep] = []
    result_codes: list[str] = []
    unresolved = False
    for step in sorted(path, key=lambda item: item.level):
        employee, codes = _resolve_role(
            step.approver_type,
            requester,
            organization,
            on_date,
            request_type,
            cost_center_id,
        )
        reason_codes = list(step.reason_codes)
        reason = step.reason
        if "CEO_MANAGER_FALLBACK" in codes:
            reason_codes.append("CEO_MANAGER_FALLBACK")
            reason = f"{reason} CEO manager role resolved to the designated CHRO/HR head."

        if employee is not None and employee.employee_id == requester.employee_id:
            manager_id = (
                None if requester.manager_id == requester.employee_id else requester.manager_id
            )
            employee = _valid_approver(
                organization, manager_id, on_date, excluded_employee_id=requester.employee_id
            )
            if employee is None:
                employee = _chro(organization, requester.employee_id, on_date)
            reason_codes.append("SELF_APPROVAL_PREVENTED")
            reason = f"{reason} Self-approval prevented; escalated to the next valid authority."

        if step.approver_type == ApprovalRole.SYSTEM:
            result_codes.extend(reason_codes)
            resolved.append(
                replace(
                    step,
                    approver_id=None,
                    approver_name="SYSTEM",
                    reason_codes=tuple(dict.fromkeys(reason_codes)),
                )
            )
            continue

        if employee is None:
            unresolved = True
            reason_codes.append("UNRESOLVED_APPROVER")
            reason = f"{reason} No active distinct approver could be resolved."
        result_codes.extend(reason_codes)
        resolved.append(
            replace(
                step,
                approver_id=employee.employee_id if employee is not None else None,
                approver_name=employee.display_name or employee.employee_id
                if employee is not None
                else None,
                reason=reason,
                reason_codes=tuple(dict.fromkeys(reason_codes)),
            )
        )
    ordered_codes = tuple(dict.fromkeys(result_codes))
    resolved_path = tuple(resolved)
    if unresolved:
        return failure(
            reason_codes=ordered_codes,
            rule_ids=("G5", "E7", "AU3"),
            message="One or more approval roles remain unresolved; the request must stay pending.",
            value=resolved_path,
        )
    return success(
        resolved_path,
        reason_codes=ordered_codes or ("APPROVERS_RESOLVED",),
        rule_ids=("G5", "E7", "AU3"),
        message="Resolved every approval role deterministically.",
    )
