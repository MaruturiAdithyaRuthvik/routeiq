from dataclasses import replace
from datetime import date
from decimal import Decimal
from math import nan

import pytest

from app.engine.decision import create_decision_trace
from app.engine.eligibility import check_reimbursement_eligibility
from app.engine.lifecycle import IllegalTransition, transition
from app.engine.models import (
    ApprovalPathStep,
    ApprovalRole,
    ApprovalStep,
    AuditFindingStatus,
    CostCenter,
    CountryCode,
    DesignatedApprover,
    Employee,
    EmployeeCostCenterAssignment,
    ExpenseStatus,
    FindingCode,
    FunctionalRole,
    OpenFinding,
    OrganizationSnapshot,
    ReimbursementStatus,
    RequestType,
    SystemRole,
)
from app.engine.resolver import resolve_approvers
from app.engine.risk import calculate_risk_score


def employee_by_role(
    employee_id: str,
    role: FunctionalRole,
    *,
    country: CountryCode = CountryCode.US,
    system_role: SystemRole = SystemRole.APPROVER,
) -> Employee:
    return Employee(
        employee_id=employee_id,
        display_name=f"Person {employee_id}",
        country=country,
        hire_date=date(2018, 1, 1),
        functional_role=role,
        system_role=system_role,
        job_level=8,
    )


def step(role: ApprovalRole, level: int = 1) -> ApprovalPathStep:
    return ApprovalPathStep(
        level,
        role,
        f"Reason for {role.value}",
        ("E5",),
        ("EXPENSE_50_1000",),
    )


def test_manager_and_ceo_resolution(employee, manager) -> None:
    result = resolve_approvers(
        (step(ApprovalRole.MANAGER),),
        employee,
        OrganizationSnapshot((employee, manager)),
        request_type=RequestType.LEAVE,
    )
    assert result.ok and result.value is not None
    assert result.value[0].approver_id == manager.employee_id
    chro = employee_by_role("EMP-000003", FunctionalRole.HR_PARTNER)
    ceo = replace(employee, employee_id="EMP-000010", is_ceo=True, manager_id=None)
    ceo_result = resolve_approvers(
        (step(ApprovalRole.MANAGER),),
        ceo,
        OrganizationSnapshot((ceo, chro), chro_employee_id=chro.employee_id),
        request_type=RequestType.LEAVE,
    )
    assert ceo_result.ok and ceo_result.value is not None
    assert ceo_result.value[0].approver_id == chro.employee_id
    assert "CEO_MANAGER_FALLBACK" in ceo_result.value[0].reason_codes


def test_self_approval_escalates_and_records_reason() -> None:
    requester = employee_by_role("EMP-000001", FunctionalRole.NONE)
    requester = replace(requester, manager_id=requester.employee_id)
    manager = employee_by_role("EMP-000002", FunctionalRole.DEPT_HEAD)
    requester = replace(requester, system_role=SystemRole.APPROVER)
    result = resolve_approvers(
        (step(ApprovalRole.MANAGER),),
        requester,
        OrganizationSnapshot((requester, manager), chro_employee_id=manager.employee_id),
        request_type=RequestType.LEAVE,
    )
    assert result.ok and result.value is not None
    assert result.value[0].approver_id == manager.employee_id
    assert "SELF_APPROVAL_PREVENTED" in result.reason_codes
    assert "SELF_APPROVAL_PREVENTED" in result.value[0].reason_codes


def test_only_hr_partner_requester_escalates_to_manager(employee, manager) -> None:
    requester = replace(
        employee,
        functional_role=FunctionalRole.HR_PARTNER,
        system_role=SystemRole.APPROVER,
    )
    result = resolve_approvers(
        (step(ApprovalRole.HR_PARTNER),),
        requester,
        OrganizationSnapshot((requester, manager)),
        request_type=RequestType.LEAVE,
    )
    assert result.ok and result.value is not None
    assert result.value[0].approver_id == manager.employee_id
    assert "SELF_APPROVAL_PREVENTED" in result.value[0].reason_codes


def test_hr_partner_deterministic_selection_and_unresolved(employee) -> None:
    hr_b = employee_by_role("EMP-000003", FunctionalRole.HR_PARTNER)
    hr_a = employee_by_role("EMP-000002", FunctionalRole.HR_PARTNER)
    result = resolve_approvers(
        (step(ApprovalRole.HR_PARTNER),),
        employee,
        OrganizationSnapshot((employee, hr_b, hr_a)),
        request_type=RequestType.LEAVE,
    )
    assert result.value is not None
    assert result.value[0].approver_id == "EMP-000002"
    unresolved = resolve_approvers(
        (step(ApprovalRole.FINANCE_CONTROLLER),),
        employee,
        OrganizationSnapshot((employee,)),
        request_type=RequestType.EXPENSE,
    )
    assert not unresolved.ok and unresolved.value is not None
    assert unresolved.value[0].approver_id is None
    assert "UNRESOLVED_APPROVER" in unresolved.reason_codes


def test_dept_head_resolution_cost_center_owner_and_leave_assignment(employee) -> None:
    owner_a = employee_by_role("EMP-000003", FunctionalRole.DEPT_HEAD)
    owner_b = employee_by_role("EMP-000004", FunctionalRole.DEPT_HEAD)
    organization = OrganizationSnapshot(
        (employee, owner_a, owner_b),
        cost_centers=(CostCenter("CC-0001", owner_a.employee_id),),
        cost_center_assignments=(
            EmployeeCostCenterAssignment(
                employee.employee_id, "CC-0001", Decimal("60"), date(2026, 1, 1)
            ),
            EmployeeCostCenterAssignment(
                employee.employee_id, "CC-0002", Decimal("40"), date(2026, 1, 1)
            ),
        ),
    )
    expense = resolve_approvers(
        (step(ApprovalRole.DEPT_HEAD),),
        employee,
        organization,
        request_type=RequestType.EXPENSE,
        cost_center_id="CC-0001",
    )
    leave = resolve_approvers(
        (step(ApprovalRole.DEPT_HEAD),),
        employee,
        organization,
        request_type=RequestType.LEAVE,
    )
    assert expense.value is not None and expense.value[0].approver_id == owner_a.employee_id
    assert leave.value is not None and leave.value[0].approver_id == owner_a.employee_id


def test_designated_holder_system_step_and_requester_excluded(employee) -> None:
    finance = employee_by_role("EMP-000003", FunctionalRole.FINANCE_CONTROLLER)
    requester_as_holder = replace(
        employee,
        functional_role=FunctionalRole.FINANCE_CONTROLLER,
        system_role=SystemRole.APPROVER,
    )
    organization = OrganizationSnapshot(
        (employee, finance, requester_as_holder),
        designated_approvers=(
            DesignatedApprover(
                "ARL-001",
                ApprovalRole.FINANCE_CONTROLLER,
                requester_as_holder.employee_id,
                1,
                date(2026, 1, 1),
            ),
            DesignatedApprover(
                "ARL-002",
                ApprovalRole.FINANCE_CONTROLLER,
                finance.employee_id,
                2,
                date(2026, 1, 1),
            ),
        ),
    )
    result = resolve_approvers(
        (step(ApprovalRole.FINANCE_CONTROLLER), step(ApprovalRole.SYSTEM, 2)),
        employee,
        organization,
        request_type=RequestType.EXPENSE,
    )
    assert result.value is not None
    assert result.value[0].approver_id == finance.employee_id
    assert result.value[1].approver_name == "SYSTEM"
    assert not resolve_approvers(
        (step(ApprovalRole.MANAGER),),
        employee,
        OrganizationSnapshot((employee,)),
        request_type=RequestType.LEAVE,
    ).ok


@pytest.mark.parametrize(
    ("request_type", "current", "target", "expected"),
    [
        (RequestType.LEAVE, "DRAFT", "SUBMITTED", "L7"),
        (RequestType.LEAVE, "SUBMITTED", "PENDING_APPROVAL", "L7"),
        (RequestType.LEAVE, "PENDING_APPROVAL", "CANCELLED", "L7"),
        (RequestType.EXPENSE, "PENDING_APPROVAL", "APPROVED", "E8"),
        (RequestType.EXPENSE, "APPROVED", "REIMBURSED", "E8"),
    ],
)
def test_lifecycle_legal_transitions(request_type, current, target, expected) -> None:
    result = transition(current, target, request_type)
    assert result.from_status == current
    assert result.to_status == target
    assert result.rule_ids == (expected,)


@pytest.mark.parametrize(
    ("request_type", "current", "target", "rule_id"),
    [
        (RequestType.LEAVE, "DRAFT", "APPROVED", "L7"),
        (RequestType.LEAVE, "APPROVED", "CANCELLED", "L7"),
        (RequestType.EXPENSE, "DRAFT", "PENDING_APPROVAL", "E8"),
        (RequestType.EXPENSE, "REIMBURSED", "APPROVED", "E8"),
        (RequestType.EXPENSE, "INVALID", "APPROVED", "E8"),
    ],
)
def test_illegal_lifecycle_transitions_raise_explained_error(
    request_type, current, target, rule_id
) -> None:
    with pytest.raises(IllegalTransition) as raised:
        transition(current, target, request_type)
    assert raised.value.reason_codes == ("ILLEGAL_TRANSITION",)
    assert raised.value.rule_ids == (rule_id,)


def test_reimbursement_eligibility_and_payment_schedule(employee) -> None:
    eligible = check_reimbursement_eligibility(
        employee=employee,
        amount_usd=Decimal("100"),
        claim_status=ExpenseStatus.APPROVED,
        approval_steps=(ApprovalStep(ApprovalRole.SYSTEM, "APPROVED"),),
        findings=(),
        cost_center_id="CC-0001",
        existing_reimbursement_ids=(),
        final_approval_date=date(2026, 10, 22),
        as_of_date=date(2026, 10, 22),
    )
    assert eligible.ok and eligible.value is not None
    assert eligible.value.amount_home_currency == Decimal("100.00")
    assert eligible.value.payment_date == date(2026, 10, 29)
    assert eligible.value.status == ReimbursementStatus.SCHEDULED
    blocked = check_reimbursement_eligibility(
        employee=employee,
        amount_usd=Decimal("100"),
        claim_status=ExpenseStatus.PENDING_APPROVAL,
        approval_steps=(ApprovalStep(ApprovalRole.MANAGER, "PENDING"),),
        findings=(OpenFinding(FindingCode.DUPLICATE_RECEIPT, AuditFindingStatus.OPEN),),
        cost_center_id=None,
        existing_reimbursement_ids=("RMB-2026-000001",),
        final_approval_date=date(2026, 10, 22),
    )
    assert not blocked.ok and blocked.value is not None
    assert {
        "CLAIM_NOT_APPROVED",
        "APPROVAL_STEP_NOT_APPROVED",
        "DUPLICATE_RELATED_FINDING_OPEN",
        "MISSING_COST_CENTER",
        "REIMBURSEMENT_ALREADY_EXISTS",
    }.issubset(blocked.value.reasons)


def test_reimbursement_duplicate_finding_and_paid_boundary(employee) -> None:
    blocked = check_reimbursement_eligibility(
        employee=employee,
        amount_usd=Decimal("10"),
        claim_status=ExpenseStatus.APPROVED,
        approval_steps=(ApprovalStep(ApprovalRole.SYSTEM, "APPROVED"),),
        findings=(OpenFinding(FindingCode.DUPLICATE_REIMBURSEMENT, AuditFindingStatus.OPEN),),
        cost_center_id="CC-0001",
        existing_reimbursement_ids=(),
        final_approval_date=date(2026, 10, 1),
    )
    assert "DUPLICATE_REIMBURSEMENT" in blocked.reason_codes
    paid = check_reimbursement_eligibility(
        employee=employee,
        amount_usd=Decimal("10"),
        claim_status=ExpenseStatus.APPROVED,
        approval_steps=(ApprovalStep(ApprovalRole.SYSTEM, "APPROVED"),),
        findings=(OpenFinding(FindingCode.MISSING_RECEIPT, AuditFindingStatus.RESOLVED),),
        cost_center_id="CC-0001",
        existing_reimbursement_ids=(),
        final_approval_date=date(2026, 10, 1),
    )
    assert paid.value is not None and paid.value.status == ReimbursementStatus.PAID


def test_decision_trace_serializes_and_rejects_ground_truth() -> None:
    trace = create_decision_trace(
        inputs_snapshot={"start_date": date(2026, 1, 1), "amount": Decimal("12.34")},
        matched_rule_ids=("E5", "E5"),
        reason_codes=("EXPENSE_50_1000",),
        path=(step(ApprovalRole.MANAGER),),
        outputs_snapshot={"total_usd": Decimal("12.34")},
    )
    assert trace.ok and trace.value is not None
    encoded = trace.value.to_json()
    assert '"engine_version":"1.0.0"' in encoded
    assert '"start_date":"2026-01-01"' in encoded
    assert trace.value.matched_rule_ids == ("E5",)
    assert not create_decision_trace(
        inputs_snapshot={"expected_status": "APPROVED"},
        matched_rule_ids=("E5",),
        reason_codes=(),
        path=(),
        outputs_snapshot={},
    ).ok
    assert not create_decision_trace(
        inputs_snapshot={},
        matched_rule_ids=(),
        reason_codes=(),
        path=({"ground_truth_decision_id": "GTD-2026-000001"},),
        outputs_snapshot={},
    ).ok
    assert not create_decision_trace(
        inputs_snapshot={"payload": object()},
        matched_rule_ids=(),
        reason_codes=(),
        path=(),
        outputs_snapshot={},
    ).ok
    assert not create_decision_trace(
        inputs_snapshot={"score": nan},
        matched_rule_ids=(),
        reason_codes=(),
        path=(),
        outputs_snapshot={},
    ).ok


def test_d8_risk_score_uses_distinct_open_findings_and_caps_at_100() -> None:
    findings = (
        OpenFinding(FindingCode.DUPLICATE_RECEIPT, AuditFindingStatus.OPEN),
        OpenFinding(FindingCode.DUPLICATE_RECEIPT, AuditFindingStatus.OPEN),
        OpenFinding(FindingCode.MISSING_RECEIPT, AuditFindingStatus.OPEN),
        OpenFinding(FindingCode.SPLIT_CLAIM, AuditFindingStatus.RESOLVED),
    )
    score = calculate_risk_score(findings)
    assert score.value == 65
    assert score.reason_codes == ("DUPLICATE_RECEIPT", "MISSING_RECEIPT")
    capped = calculate_risk_score(
        (
            OpenFinding(FindingCode.DUPLICATE_RECEIPT, AuditFindingStatus.OPEN),
            OpenFinding(FindingCode.DATE_OUTSIDE_EMPLOYMENT, AuditFindingStatus.OPEN),
            OpenFinding(FindingCode.OVERLAP, AuditFindingStatus.OPEN),
        )
    )
    assert capped.value == 100
    assert calculate_risk_score(()).reason_codes == ("NO_OPEN_FINDINGS",)
