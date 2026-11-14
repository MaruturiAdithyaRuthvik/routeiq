"""Inject documented, loadable edge cases and isolate their evaluation labels."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.engine.ids import IdKind
from app.engine.models import (
    ApprovalRole,
    LeaveEffectBucket,
    LeaveLedgerEntry,
    LeaveLedgerEntryType,
    ReimbursementStatus,
)

from .context import GenerationContext, Row
from .helpers import add_workdays, new_id, utc_at
from .leave import _add_finding, rebuild_leave_balances
from .tables import set_table

_AS_OF_TIME = utc_at(date(2026, 10, 22), 16 * 60)


def inject_labeled_anomalies(context: GenerationContext) -> None:
    """Apply labeled mutations only after rule-driven baseline transactions are built."""

    leave_rows: list[Row] = context.references["leave_request_rows"]
    expense_rows: list[Row] = context.references["expense_claim_rows"]
    line_rows: list[Row] = context.references["expense_line_rows"]
    balance_rows: list[Row] = context.get_rows("leave_balance")
    reimbursement_rows: list[Row] = context.references["reimbursement_rows"]
    finding_rows: list[Row] = context.references["finding_rows"]
    anomaly_rows: list[Row] = []
    decision_rows: list[Row] = []

    leave_by_id = {row["leave_request_id"]: row for row in leave_rows}
    expense_by_id = {row["expense_claim_id"]: row for row in expense_rows}
    line_by_claim_number = {(row["expense_claim_id"], row["line_number"]): row for row in line_rows}

    annual_balances = sorted(
        (
            row
            for row in balance_rows
            if row["leave_policy_id"] == "LPO-001" and row["available_days"] >= Decimal("0")
        ),
        key=lambda row: row["employee_id"],
    )
    if not annual_balances:
        raise ValueError("no annual balance is available for the negative-balance scenario")
    negative_balance = annual_balances[0]
    adjustment = -(negative_balance["available_days"] + Decimal("1.000000"))
    ledger_sequence = int(context.references["next_ledger_sequence"])
    negative_entry = LeaveLedgerEntry(
        leave_ledger_entry_id=new_id(IdKind.LEAVE_LEDGER_ENTRY, ledger_sequence),
        employee_id=negative_balance["employee_id"],
        leave_policy_id="LPO-001",
        entry_type=LeaveLedgerEntryType.ADJUSTMENT,
        effect_bucket=LeaveEffectBucket.AVAILABLE,
        delta_days=adjustment,
        entry_date=context.as_of_date,
    )
    context.references["ledger_models"].append(negative_entry)
    context.references["ledger_rows"].append(
        {
            "leave_ledger_entry_id": negative_entry.leave_ledger_entry_id,
            "employee_id": negative_entry.employee_id,
            "leave_policy_id": negative_entry.leave_policy_id,
            "leave_request_id": None,
            "entry_type": negative_entry.entry_type.value,
            "effect_bucket": negative_entry.effect_bucket.value,
            "delta_days": negative_entry.delta_days,
            "prior_year_closing_days": None,
            "entry_date": negative_entry.entry_date,
            "reversal_of_entry_id": None,
            "source_event_id": None,
        }
    )
    context.references["next_ledger_sequence"] = ledger_sequence + 1
    _add_anomaly(
        anomaly_rows,
        issue_type="NEGATIVE_LEAVE_BALANCE",
        violation_rule_ids=("L3",),
        leave_balance_id=negative_balance["leave_balance_id"],
        details={"employee_id": negative_balance["employee_id"], "available_days": "-1.000000"},
    )

    overlap_request_id = "LVE-2026-000052"
    overlap_request = leave_by_id[overlap_request_id]
    overlap_peer = next(
        row
        for row in leave_rows
        if row["employee_id"] == overlap_request["employee_id"]
        and row["leave_request_id"] != overlap_request_id
        and row["start_date"] == overlap_request["start_date"]
        and row["status"] == "APPROVED"
    )
    _add_finding(
        context,
        leave_request_id=overlap_request_id,
        finding_code="OVERLAP",
        severity="ERROR",
        details={"overlapping_request_id": overlap_peer["leave_request_id"], "rule_id": "L4"},
        detected_at=_AS_OF_TIME,
    )
    _add_anomaly(
        anomaly_rows,
        issue_type="OVERLAPPING_APPROVED_LEAVE",
        violation_rule_ids=("L4",),
        expected_finding_code="OVERLAP",
        leave_request_id=overlap_request_id,
        details={"overlapping_request_id": overlap_peer["leave_request_id"]},
    )
    _add_decision(
        context,
        decision_rows,
        leave_request_id=overlap_request_id,
        expected_status="DRAFT",
        expected_reason_codes=("OVERLAP",),
        matched_rule_ids=("L4",),
        expected_path=(),
        expected_reimbursement=None,
        expected_risk_score=None,
    )

    zero_request_id = "LVE-2026-000001"
    zero_request = leave_by_id[zero_request_id]
    _add_anomaly(
        anomaly_rows,
        issue_type="ZERO_BUSINESS_DAY_SPAN",
        violation_rule_ids=("L4",),
        expected_finding_code="ZERO_BUSINESS_DAYS",
        leave_request_id=zero_request_id,
        details={
            "start_date": zero_request["start_date"].isoformat(),
            "end_date": zero_request["end_date"].isoformat(),
        },
    )
    _add_decision(
        context,
        decision_rows,
        leave_request_id=zero_request_id,
        expected_status="DRAFT",
        expected_reason_codes=("ZERO_BUSINESS_DAYS",),
        matched_rule_ids=("L4",),
        expected_path=(),
        expected_reimbursement=None,
        expected_risk_score=None,
    )

    insufficient_id = "LVE-2026-000002"
    insufficient = leave_by_id[insufficient_id]
    _add_anomaly(
        anomaly_rows,
        issue_type="INSUFFICIENT_BALANCE",
        violation_rule_ids=("L4",),
        expected_finding_code="INSUFFICIENT_BALANCE",
        leave_request_id=insufficient_id,
        details={
            "employee_id": insufficient["employee_id"],
            "business_days": insufficient["business_days"],
        },
    )
    _add_decision(
        context,
        decision_rows,
        leave_request_id=insufficient_id,
        expected_status="DRAFT",
        expected_reason_codes=("INSUFFICIENT_BALANCE",),
        matched_rule_ids=("L4",),
        expected_path=(),
        expected_reimbursement=None,
        expected_risk_score=None,
    )

    _add_expense_anomaly(
        context,
        anomaly_rows,
        decision_rows,
        expense_by_id,
        line_by_claim_number,
        claim_id="EXP-2026-000001",
        issue_type="MISSING_RECEIPT",
        rule_ids=("E3",),
        finding="MISSING_RECEIPT",
        line_number=1,
        expected_reasons=("MISSING_RECEIPT",),
        expected_reimbursement=None,
    )
    _add_expense_anomaly(
        context,
        anomaly_rows,
        decision_rows,
        expense_by_id,
        line_by_claim_number,
        claim_id="EXP-2026-000002",
        issue_type="DUPLICATE_RECEIPT",
        rule_ids=("E3", "E4"),
        finding="DUPLICATE_RECEIPT",
        line_number=1,
        expected_reasons=("DUPLICATE_RECEIPT",),
        expected_reimbursement=False,
    )
    _add_expense_anomaly(
        context,
        anomaly_rows,
        decision_rows,
        expense_by_id,
        line_by_claim_number,
        claim_id="EXP-2026-000003",
        issue_type="POLICY_LIMIT_BREACH",
        rule_ids=("E3",),
        finding="POLICY_LIMIT_BREACH",
        line_number=1,
        expected_reasons=("POLICY_LIMIT_BREACH",),
        expected_reimbursement=None,
    )
    _add_expense_anomaly(
        context,
        anomaly_rows,
        decision_rows,
        expense_by_id,
        line_by_claim_number,
        claim_id="EXP-2026-000004",
        issue_type="POLICY_LIMIT_BREACH",
        rule_ids=("E3", "E4"),
        finding="POLICY_LIMIT_BREACH",
        line_number=1,
        expected_reasons=("POLICY_LIMIT_BREACH",),
        expected_reimbursement=False,
    )
    _add_expense_anomaly(
        context,
        anomaly_rows,
        decision_rows,
        expense_by_id,
        line_by_claim_number,
        claim_id="EXP-2026-000005",
        issue_type="MISSING_COST_CENTER",
        rule_ids=("E3", "E4"),
        finding="MISSING_COST_CENTER",
        expected_reasons=("MISSING_COST_CENTER",),
        expected_reimbursement=False,
    )

    outside_sequence = max(15, round(context.preset.expense_claims * 0.45))
    outside_claim_id = f"EXP-2026-{outside_sequence:06d}"
    _add_expense_anomaly(
        context,
        anomaly_rows,
        decision_rows,
        expense_by_id,
        line_by_claim_number,
        claim_id=outside_claim_id,
        issue_type="EXPENSE_OUTSIDE_EMPLOYMENT",
        rule_ids=("E3", "E4"),
        finding="DATE_OUTSIDE_EMPLOYMENT",
        expected_reasons=("DATE_OUTSIDE_EMPLOYMENT",),
        expected_reimbursement=False,
    )
    _add_expense_anomaly(
        context,
        anomaly_rows,
        decision_rows,
        expense_by_id,
        line_by_claim_number,
        claim_id="EXP-2026-000007",
        issue_type="FUTURE_EXPENSE_DATE",
        rule_ids=("E4",),
        finding="FUTURE_EXPENSE_DATE",
        expected_reasons=("FUTURE_EXPENSE_DATE",),
        expected_reimbursement=False,
    )

    for claim_id in sorted(context.references.get("split_claim_ids", set())):
        claim = expense_by_id[claim_id]
        _add_anomaly(
            anomaly_rows,
            issue_type="SPLIT_CLAIM",
            violation_rule_ids=("E10",),
            expected_finding_code="SPLIT_CLAIM",
            expense_claim_id=claim_id,
            details={"employee_id": claim["employee_id"], "total_usd": str(claim["total_usd"])},
        )
        _add_decision(
            context,
            decision_rows,
            expense_claim_id=claim_id,
            expected_status=claim["status"],
            expected_reason_codes=("SPLIT_CLAIM",),
            matched_rule_ids=("E10", "E9"),
            expected_path=context.references["expense_paths"].get(claim_id, ()),
            expected_reimbursement=False,
            expected_risk_score=None,
        )

    reimbursement_claim_ids = {row["expense_claim_id"] for row in reimbursement_rows}
    self_approval_step = _inject_self_approval(
        context,
        anomaly_rows,
        finding_rows,
        expense_by_id,
        decision_rows,
        reimbursement_claim_ids,
    )
    _add_decision(
        context,
        decision_rows,
        expense_claim_id=self_approval_step["expense_claim_id"],
        expected_status=expense_by_id[self_approval_step["expense_claim_id"]]["status"],
        expected_reason_codes=("SELF_APPROVAL_PREVENTED",),
        matched_rule_ids=("G5", "AU3"),
        expected_path=context.references["expense_paths"].get(
            self_approval_step["expense_claim_id"], ()
        ),
        expected_reimbursement=None,
        expected_risk_score=None,
    )

    duplicate_reimbursement = _inject_duplicate_reimbursement(context, anomaly_rows, finding_rows)
    _add_decision(
        context,
        decision_rows,
        expense_claim_id=duplicate_reimbursement["expense_claim_id"],
        expected_status=expense_by_id[duplicate_reimbursement["expense_claim_id"]]["status"],
        expected_reason_codes=("DUPLICATE_REIMBURSEMENT",),
        matched_rule_ids=("E9", "AU3"),
        expected_path=context.references["expense_paths"].get(
            duplicate_reimbursement["expense_claim_id"], ()
        ),
        expected_reimbursement=False,
        expected_risk_score=None,
    )

    rebuild_leave_balances(context)
    context.references["ground_truth_anomaly_rows"] = anomaly_rows
    context.references["ground_truth_decision_rows"] = decision_rows
    set_table(context, "ground_truth_anomaly", anomaly_rows)
    set_table(context, "ground_truth_decision", decision_rows)
    set_table(context, "audit_finding", finding_rows)
    set_table(context, "approval_step", context.references["approval_step_rows"])
    set_table(context, "leave_ledger_entry", context.references["ledger_rows"])
    set_table(context, "expense_claim_event", context.references["expense_event_rows"])
    set_table(context, "reimbursement", context.references["reimbursement_rows"])


def _add_anomaly(
    rows: list[Row],
    *,
    issue_type: str,
    violation_rule_ids: tuple[str, ...],
    details: dict[str, object],
    leave_request_id: str | None = None,
    leave_balance_id: str | None = None,
    expense_claim_id: str | None = None,
    expense_line_id: str | None = None,
    approval_step_id: str | None = None,
    reimbursement_id: str | None = None,
    expected_finding_code: str | None = None,
) -> None:
    rows.append(
        {
            "ground_truth_anomaly_id": new_id(IdKind.GROUND_TRUTH_ANOMALY, len(rows) + 1),
            "leave_request_id": leave_request_id,
            "leave_balance_id": leave_balance_id,
            "expense_claim_id": expense_claim_id,
            "expense_line_id": expense_line_id,
            "approval_step_id": approval_step_id,
            "reimbursement_id": reimbursement_id,
            "issue_type": issue_type,
            "violation_rule_ids": sorted(set(violation_rule_ids)),
            "expected_finding_code": expected_finding_code,
            "label": "ANOMALY",
            "details": details,
        }
    )


def _add_decision(
    context: GenerationContext,
    rows: list[Row],
    *,
    expected_status: str,
    expected_reason_codes: tuple[str, ...],
    matched_rule_ids: tuple[str, ...],
    expected_path: tuple[object, ...],
    expected_reimbursement: bool | None,
    expected_risk_score: int | None,
    leave_request_id: str | None = None,
    expense_claim_id: str | None = None,
) -> None:
    rows.append(
        {
            "ground_truth_decision_id": new_id(IdKind.GROUND_TRUTH_DECISION, len(rows) + 1),
            "leave_request_id": leave_request_id,
            "expense_claim_id": expense_claim_id,
            "expected_status": expected_status,
            "expected_approval_path": [
                {
                    "level": step.level,
                    "approver_type": step.approver_type.value,
                    "approver_id": step.approver_id,
                    "approver_name": step.approver_name,
                    "reason": step.reason,
                    "rule_ids": list(step.rule_ids),
                }
                for step in expected_path
            ],
            "expected_reason_codes": sorted(set(expected_reason_codes)),
            "matched_rule_ids": sorted(set(matched_rule_ids)),
            "expected_reimbursement": expected_reimbursement,
            "expected_risk_score": expected_risk_score,
            "evaluation_metric": "approval_path_accuracy" if expected_path else "decision_accuracy",
        }
    )


def _add_expense_anomaly(
    context: GenerationContext,
    anomalies: list[Row],
    decisions: list[Row],
    expense_by_id: dict[str, Row],
    lines_by_claim_number: dict[tuple[str, int], Row],
    *,
    claim_id: str,
    issue_type: str,
    rule_ids: tuple[str, ...],
    finding: str,
    expected_reasons: tuple[str, ...],
    expected_reimbursement: bool | None,
    line_number: int | None = None,
) -> None:
    claim = expense_by_id[claim_id]
    line = lines_by_claim_number.get((claim_id, line_number)) if line_number is not None else None
    _add_anomaly(
        anomalies,
        issue_type=issue_type,
        violation_rule_ids=rule_ids,
        expected_finding_code=finding,
        expense_claim_id=None if line is not None else claim_id,
        expense_line_id=None if line is None else line["expense_line_id"],
        details={"claim_id": claim_id, "total_usd": str(claim["total_usd"])},
    )
    path = context.references["expense_paths"].get(claim_id, ())
    _add_decision(
        context,
        decisions,
        expense_claim_id=claim_id,
        expected_status=claim["status"],
        expected_reason_codes=expected_reasons,
        matched_rule_ids=rule_ids,
        expected_path=path,
        expected_reimbursement=expected_reimbursement
        if expected_reimbursement is not None
        else claim["status"] == "REIMBURSED",
        expected_risk_score=None,
    )


def _inject_self_approval(
    context: GenerationContext,
    anomaly_rows: list[Row],
    finding_rows: list[Row],
    expense_by_id: dict[str, Row],
    prior_decisions: list[Row],
    reimbursed_claim_ids: set[str],
) -> Row:
    excluded = {
        "EXP-2026-000001",
        "EXP-2026-000002",
        "EXP-2026-000003",
        "EXP-2026-000004",
        "EXP-2026-000005",
        "EXP-2026-000007",
        *reimbursed_claim_ids,
        *(
            row["expense_claim_id"]
            for row in prior_decisions
            if row["expense_claim_id"] is not None
        ),
    }
    candidates = [
        row
        for row in context.references["approval_step_rows"]
        if row["expense_claim_id"] is not None
        and row["expense_claim_id"] not in excluded
        and row["required_role"] != ApprovalRole.SYSTEM.value
        and row["status"] == "APPROVED"
        and row["approver_employee_id"] != expense_by_id[row["expense_claim_id"]]["employee_id"]
    ]
    if not candidates:
        raise ValueError("no completed human approval step available for self-approval anomaly")
    step = min(candidates, key=lambda row: row["approval_step_id"])
    claim_id = step["expense_claim_id"]
    step["approver_employee_id"] = expense_by_id[claim_id]["employee_id"]
    _add_finding(
        context,
        approval_step_id=step["approval_step_id"],
        finding_code="SELF_APPROVAL_PREVENTED",
        severity="ERROR",
        details={"employee_id": step["approver_employee_id"], "rule_id": "G5"},
        detected_at=_AS_OF_TIME,
    )
    _add_anomaly(
        anomaly_rows,
        issue_type="SELF_APPROVAL",
        violation_rule_ids=("G5",),
        expected_finding_code="SELF_APPROVAL_PREVENTED",
        approval_step_id=step["approval_step_id"],
        details={"expense_claim_id": claim_id, "employee_id": step["approver_employee_id"]},
    )
    return step


def _inject_duplicate_reimbursement(
    context: GenerationContext,
    anomaly_rows: list[Row],
    finding_rows: list[Row],
) -> Row:
    reimbursements: list[Row] = context.references["reimbursement_rows"]
    if not reimbursements:
        raise ValueError("baseline must generate an eligible reimbursement before injection")
    first = min(reimbursements, key=lambda row: row["reimbursement_id"])
    claim = next(
        row
        for row in context.references["expense_claim_rows"]
        if row["expense_claim_id"] == first["expense_claim_id"]
    )
    employee = context.references["employees"][claim["employee_id"]]
    payment_date = add_workdays(context.as_of_date, 5, employee.country.value)
    sequence = len(reimbursements) + 1
    duplicate = {
        "reimbursement_id": new_id(IdKind.REIMBURSEMENT, sequence),
        "expense_claim_id": first["expense_claim_id"],
        "amount_home_currency": first["amount_home_currency"],
        "home_currency": first["home_currency"],
        "payment_date": payment_date,
        "status": ReimbursementStatus.SCHEDULED.value,
        "created_at": _AS_OF_TIME,
        "paid_at": None,
        "payment_reference": f"PAY-2026-{sequence:06d}",
    }
    reimbursements.append(duplicate)
    _add_finding(
        context,
        reimbursement_id=duplicate["reimbursement_id"],
        finding_code="DUPLICATE_REIMBURSEMENT",
        severity="ERROR",
        details={"expense_claim_id": duplicate["expense_claim_id"], "rule_id": "E9"},
        detected_at=_AS_OF_TIME,
    )
    event_rows: list[Row] = context.references["expense_event_rows"]
    next_event_id = int(context.references["next_expense_event_sequence"])
    current_events = [
        row for row in event_rows if row["expense_claim_id"] == duplicate["expense_claim_id"]
    ]
    event_rows.append(
        {
            "event_id": new_id(IdKind.EXPENSE_CLAIM_EVENT, next_event_id),
            "expense_claim_id": duplicate["expense_claim_id"],
            "sequence_number": max((row["sequence_number"] for row in current_events), default=0)
            + 1,
            "event_type": "REIMBURSEMENT_CREATED",
            "from_status": "REIMBURSED",
            "to_status": "REIMBURSED",
            "occurred_at": _AS_OF_TIME,
            "actor_employee_id": None,
            "reason_code": "DUPLICATE_REIMBURSEMENT",
            "event_payload": {
                "reimbursement_id": duplicate["reimbursement_id"],
                "status": "SCHEDULED",
            },
        }
    )
    context.references["next_expense_event_sequence"] = next_event_id + 1
    _add_anomaly(
        anomaly_rows,
        issue_type="DUPLICATE_REIMBURSEMENT",
        violation_rule_ids=("E9",),
        expected_finding_code="DUPLICATE_REIMBURSEMENT",
        reimbursement_id=duplicate["reimbursement_id"],
        details={
            "expense_claim_id": duplicate["expense_claim_id"],
            "original_reimbursement_id": first["reimbursement_id"],
        },
    )
    return duplicate
