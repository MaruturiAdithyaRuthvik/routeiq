"""Deterministic operational exception risk scoring (D8, AU1)."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final

from .models import AuditFindingStatus, FindingCode, OpenFinding
from .results import RuleResult, success

RISK_WEIGHTS: Final = MappingProxyType(
    {
        FindingCode.INVALID_DATE_RANGE: 25,
        FindingCode.ZERO_BUSINESS_DAYS: 20,
        FindingCode.EMPLOYEE_NOT_ACTIVE: 40,
        FindingCode.TENURE_INELIGIBLE: 25,
        FindingCode.MAX_CONSECUTIVE_DAYS: 20,
        FindingCode.OVERLAP: 35,
        FindingCode.INSUFFICIENT_BALANCE: 30,
        FindingCode.POLICY_LIMIT_BREACH: 20,
        FindingCode.MISSING_RECEIPT: 15,
        FindingCode.DUPLICATE_RECEIPT: 50,
        FindingCode.MISSING_COST_CENTER: 30,
        FindingCode.DATE_OUTSIDE_EMPLOYMENT: 50,
        FindingCode.FUTURE_EXPENSE_DATE: 40,
        FindingCode.SPLIT_CLAIM: 40,
        FindingCode.SELF_APPROVAL_PREVENTED: 10,
        FindingCode.UNRESOLVED_APPROVER: 25,
        FindingCode.DUPLICATE_REIMBURSEMENT: 50,
    }
)


def calculate_risk_score(
    findings: tuple[OpenFinding, ...],
) -> RuleResult[int]:
    """Sum fixed weights for distinct currently open finding codes, capped at 100 (D8)."""

    open_codes = sorted(
        {finding.finding_code for finding in findings if finding.status == AuditFindingStatus.OPEN},
        key=lambda code: code.value,
    )
    score = min(100, sum(RISK_WEIGHTS[code] for code in open_codes))
    codes = tuple(code.value for code in open_codes) or ("NO_OPEN_FINDINGS",)
    return success(
        score,
        reason_codes=codes,
        rule_ids=("D8", "AU1"),
        message=f"Calculated deterministic open-finding risk score {score}.",
    )
