"""Single deterministic pipeline shared by starter and full datasets."""

from __future__ import annotations

from typing import Any

from app.engine.models import (
    AuditFindingStatus,
    FindingCode,
    OpenFinding,
)
from app.engine.risk import calculate_risk_score

from .anomalies import inject_labeled_anomalies
from .context import GenerationContext
from .expenses import generate_expense_data
from .helpers import make_audit_row, utc_at
from .leave import generate_leave_data, rebuild_leave_balances
from .master import generate_master_data
from .tables import TABLE_COLUMNS, set_table
from .validation import validate_dataset


def generate_dataset(context: GenerationContext) -> GenerationContext:
    """Run all master, transaction, injection, reconciliation, and validation stages."""

    generate_master_data(context)
    generate_leave_data(context)
    rebuild_leave_balances(context)
    generate_expense_data(context)
    context.references["expense_claim_rows_by_id"] = {
        row["expense_claim_id"]: row for row in context.references["expense_claim_rows"]
    }
    inject_labeled_anomalies(context)
    for table in TABLE_COLUMNS:
        if table not in context.frames:
            set_table(context, table, [])
    _calculate_risk_scores(context)
    validate_dataset(context)
    return context


def _calculate_risk_scores(context: GenerationContext) -> None:
    findings = context.references["finding_rows"]
    leave_steps = {
        row["approval_step_id"]: row["leave_request_id"]
        for row in context.references.get("approval_step_rows", [])
        if row["leave_request_id"] is not None
    }
    expense_lines = {
        row["expense_line_id"]: row["expense_claim_id"]
        for row in context.references["expense_line_rows"]
    }
    expense_steps = {
        row["approval_step_id"]: row["expense_claim_id"]
        for row in context.references.get("approval_step_rows", [])
        if row["expense_claim_id"] is not None
    }
    expense_reimbursements = {
        row["reimbursement_id"]: row["expense_claim_id"]
        for row in context.references["reimbursement_rows"]
    }

    def open_findings_for(predicate: Any) -> tuple[OpenFinding, ...]:
        return tuple(
            OpenFinding(
                finding_code=FindingCode(row["finding_code"]),
                status=AuditFindingStatus.OPEN,
            )
            for row in findings
            if row["status"] == AuditFindingStatus.OPEN.value and predicate(row)
        )

    audit_rows = context.references["decision_audit_rows"]
    next_audit = int(context.references["next_audit_sequence"])
    as_of_time = utc_at(context.as_of_date, 16 * 60)
    for request in context.references["leave_request_rows"]:
        request_id = request["leave_request_id"]
        relevant = open_findings_for(
            lambda finding, request_id=request_id: (
                finding["leave_request_id"] == request_id
                or leave_steps.get(finding["approval_step_id"]) == request_id
            )
        )
        score = calculate_risk_score(relevant)
        if score.value is None:
            raise ValueError(score.messages[0])
        request["risk_score"] = score.value
        audit_rows.append(
            make_audit_row(
                context,
                next_audit,
                request_id=request_id,
                request_type="LEAVE",
                decision_kind="RISK_SCORE",
                inputs={"finding_codes": sorted({item.finding_code.value for item in relevant})},
                outputs={"risk_score": score.value},
                matched_rule_ids=score.rule_ids,
                reason_codes=score.reason_codes,
                recorded_at=as_of_time,
            )
        )
        next_audit += 1

    for claim in context.references["expense_claim_rows"]:
        claim_id = claim["expense_claim_id"]
        relevant = open_findings_for(
            lambda finding, claim_id=claim_id: (
                finding["expense_claim_id"] == claim_id
                or expense_lines.get(finding["expense_line_id"]) == claim_id
                or expense_steps.get(finding["approval_step_id"]) == claim_id
                or expense_reimbursements.get(finding["reimbursement_id"]) == claim_id
            )
        )
        score = calculate_risk_score(relevant)
        if score.value is None:
            raise ValueError(score.messages[0])
        claim["risk_score"] = score.value
        audit_rows.append(
            make_audit_row(
                context,
                next_audit,
                request_id=claim_id,
                request_type="EXPENSE",
                decision_kind="RISK_SCORE",
                inputs={"finding_codes": sorted({item.finding_code.value for item in relevant})},
                outputs={"risk_score": score.value},
                matched_rule_ids=score.rule_ids,
                reason_codes=score.reason_codes,
                recorded_at=as_of_time,
            )
        )
        next_audit += 1
    context.references["next_audit_sequence"] = next_audit
    set_table(context, "leave_request", context.references["leave_request_rows"])
    set_table(context, "expense_claim", context.references["expense_claim_rows"])
    set_table(context, "decision_audit", audit_rows)
