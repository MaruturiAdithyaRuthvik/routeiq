"""Operational-only audit detectors. No ground-truth imports or queries."""

# SQL statements intentionally follow the database column names.
# ruff: noqa: E501

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

DETECTORS = (
    (
        "OVERLAP",
        """SELECT a.leave_request_id, NULL::text expense_claim_id, NULL::text expense_line_id,
        NULL::text approval_step_id, NULL::text reimbursement_id,
        jsonb_build_object('overlapping_request_id',b.leave_request_id) details
        FROM public.leave_request a JOIN public.leave_request b ON a.employee_id=b.employee_id
        AND a.leave_request_id<>b.leave_request_id AND a.start_date<=b.end_date AND b.start_date<=a.end_date
        WHERE a.status='APPROVED' AND b.status='APPROVED'""",
    ),
    (
        "DATE_OUTSIDE_EMPLOYMENT",
        """SELECT NULL::text leave_request_id,c.expense_claim_id,NULL::text expense_line_id,
        NULL::text approval_step_id,NULL::text reimbursement_id,
        jsonb_build_object('expense_date',c.expense_date) details
        FROM public.expense_claim c JOIN public.employee e USING(employee_id)
        WHERE c.expense_date<e.hire_date OR (e.termination_date IS NOT NULL AND c.expense_date>e.termination_date)""",
    ),
    (
        "MISSING_COST_CENTER",
        """SELECT NULL::text leave_request_id,c.expense_claim_id,NULL::text expense_line_id,
        NULL::text approval_step_id,NULL::text reimbursement_id,'{}'::jsonb details
        FROM public.expense_claim c WHERE c.cost_center_id IS NULL""",
    ),
    (
        "SELF_APPROVAL_PREVENTED",
        """SELECT NULL::text leave_request_id,NULL::text expense_claim_id,NULL::text expense_line_id,
        s.approval_step_id,NULL::text reimbursement_id,jsonb_build_object('approver_id',s.approver_employee_id) details
        FROM public.approval_step s LEFT JOIN public.leave_request l USING(leave_request_id)
        LEFT JOIN public.expense_claim c USING(expense_claim_id)
        WHERE s.approver_employee_id=COALESCE(l.employee_id,c.employee_id)""",
    ),
    (
        "DUPLICATE_REIMBURSEMENT",
        """SELECT NULL::text leave_request_id,NULL::text expense_claim_id,NULL::text expense_line_id,
        NULL::text approval_step_id,r.reimbursement_id,jsonb_build_object('expense_claim_id',r.expense_claim_id) details
        FROM public.reimbursement r WHERE r.reimbursement_id<>(SELECT min(r2.reimbursement_id)
        FROM public.reimbursement r2 WHERE r2.expense_claim_id=r.expense_claim_id)""",
    ),
    (
        "DUPLICATE_RECEIPT",
        """SELECT NULL::text leave_request_id,NULL::text expense_claim_id,l.expense_line_id,
        NULL::text approval_step_id,NULL::text reimbursement_id,jsonb_build_object('receipt_hash',l.receipt_hash) details
        FROM public.expense_line l WHERE l.receipt_hash IS NOT NULL AND EXISTS
        (SELECT 1 FROM public.expense_line x WHERE x.receipt_hash=l.receipt_hash AND x.expense_line_id<l.expense_line_id)""",
    ),
    (
        "MISSING_RECEIPT",
        """SELECT NULL::text leave_request_id,NULL::text expense_claim_id,l.expense_line_id,
        NULL::text approval_step_id,NULL::text reimbursement_id,'{}'::jsonb details
        FROM public.expense_line l JOIN public.expense_claim c USING(expense_claim_id)
        JOIN public.employee e USING(employee_id) JOIN public.expense_policy p
        ON p.category=l.category AND p.country=e.country WHERE l.amount_usd>p.receipt_threshold_usd
        AND NOT l.receipt_present AND c.expense_date>=p.effective_from""",
    ),
    (
        "POLICY_LIMIT_BREACH",
        """SELECT NULL::text leave_request_id,NULL::text expense_claim_id,l.expense_line_id,
        NULL::text approval_step_id,NULL::text reimbursement_id,jsonb_build_object('amount_usd',l.amount_usd) details
        FROM public.expense_line l JOIN public.expense_claim c USING(expense_claim_id)
        JOIN public.employee e USING(employee_id) JOIN public.expense_policy p
        ON p.category=l.category AND p.country=e.country WHERE l.amount_usd>p.per_line_limit_usd
        AND c.expense_date>=p.effective_from""",
    ),
)


def run_operational_audit(session: Session) -> dict:
    """Append findings for detectable operational defects and return this run's counts."""
    findings: list[dict] = []
    for code, query in DETECTORS:
        for row in session.execute(text(query)).mappings():
            finding = dict(row)
            target = next(
                value
                for key, value in finding.items()
                if key.endswith("_id") and key != "details" and value is not None
            )
            target_column = next(
                key
                for key, value in finding.items()
                if key.endswith("_id") and key != "details" and value is not None
            )
            exists = session.execute(
                text(
                    f"SELECT EXISTS(SELECT 1 FROM public.audit_finding WHERE finding_code=:code "
                    f"AND {target_column}=:target)"
                ),
                {"code": code, "target": target},
            ).scalar_one()
            if not exists:
                findings.append({"code": code, **finding})
    seq = session.execute(
        text(
            "SELECT COALESCE(max(substring(audit_finding_id from 10)::int),0)+1 FROM public.audit_finding"
        )
    ).scalar_one()
    ids, by_code = [], {}
    for finding in findings:
        identifier = f"AFN-2026-{seq:06d}"
        session.execute(
            text(
                "INSERT INTO public.audit_finding (audit_finding_id,leave_request_id,expense_claim_id,"
                "expense_line_id,approval_step_id,reimbursement_id,finding_code,severity,status,details,detected_at) "
                "VALUES (:id,:leave_request_id,:expense_claim_id,:expense_line_id,:approval_step_id,"
                ":reimbursement_id,:code,'ERROR','OPEN',CAST(:details AS jsonb),TIMESTAMPTZ '2026-10-22 16:00:00+00')"
            ),
            {
                "id": identifier,
                **{
                    k: finding[k]
                    for k in (
                        "leave_request_id",
                        "expense_claim_id",
                        "expense_line_id",
                        "approval_step_id",
                        "reimbursement_id",
                        "code",
                    )
                },
                "details": json.dumps(finding["details"], default=str),
            },
        )
        ids.append(identifier)
        by_code[finding["code"]] = by_code.get(finding["code"], 0) + 1
        seq += 1
    session.commit()
    count = session.execute(text("SELECT count(*) FROM public.leave_request")).scalar_one()
    count += session.execute(text("SELECT count(*) FROM public.expense_claim")).scalar_one()
    return {
        "scope": "ALL",
        "as_of_date": "2026-10-22",
        "status": "COMPLETED",
        "scanned_requests": count,
        "findings_created": len(ids),
        "findings_by_code": by_code,
        "finding_ids": ids,
        "decision_audit_ids": [],
    }
