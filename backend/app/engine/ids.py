"""Formatting, parsing, and validation for immutable RouteIQ identifiers (G1, D1)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from .models import CountryCode
from .results import RuleResult, failure, success


class IdKind(StrEnum):
    EMPLOYEE = "EMPLOYEE"
    LEAVE_REQUEST = "LEAVE_REQUEST"
    EXPENSE_CLAIM = "EXPENSE_CLAIM"
    EXPENSE_LINE = "EXPENSE_LINE"
    APPROVAL_STEP = "APPROVAL_STEP"
    REIMBURSEMENT = "REIMBURSEMENT"
    LEAVE_POLICY = "LEAVE_POLICY"
    EXPENSE_POLICY = "EXPENSE_POLICY"
    COST_CENTER = "COST_CENTER"
    APPROVAL_RULE = "APPROVAL_RULE"
    LEAVE_BALANCE = "LEAVE_BALANCE"
    HOLIDAY = "HOLIDAY"
    LEAVE_LEDGER_ENTRY = "LEAVE_LEDGER_ENTRY"
    LEAVE_REQUEST_EVENT = "LEAVE_REQUEST_EVENT"
    EXPENSE_CLAIM_EVENT = "EXPENSE_CLAIM_EVENT"
    DECISION_AUDIT = "DECISION_AUDIT"
    AUDIT_FINDING = "AUDIT_FINDING"
    AUDIT_FINDING_EVENT = "AUDIT_FINDING_EVENT"
    GROUND_TRUTH_ANOMALY = "GROUND_TRUTH_ANOMALY"
    GROUND_TRUTH_DECISION = "GROUND_TRUTH_DECISION"


@dataclass(frozen=True, slots=True)
class ParsedId:
    kind: IdKind
    sequence: int
    parent_id: str | None = None
    employee_id: str | None = None
    policy_id: str | None = None
    country: CountryCode | None = None


_PATTERNS: tuple[tuple[IdKind, re.Pattern[str]], ...] = (
    (IdKind.EMPLOYEE, re.compile(r"^EMP-(?P<sequence>\d{6})$")),
    (IdKind.LEAVE_REQUEST, re.compile(r"^LVE-2026-(?P<sequence>\d{6})$")),
    (IdKind.EXPENSE_CLAIM, re.compile(r"^EXP-2026-(?P<sequence>\d{6})$")),
    (
        IdKind.EXPENSE_LINE,
        re.compile(r"^EXPL-(?P<parent_id>EXP-2026-\d{6})-(?P<sequence>\d{2})$"),
    ),
    (
        IdKind.APPROVAL_STEP,
        re.compile(r"^APR-(?P<parent_id>(?:LVE|EXP)-2026-\d{6})-(?P<sequence>\d{2})$"),
    ),
    (IdKind.REIMBURSEMENT, re.compile(r"^RMB-2026-(?P<sequence>\d{6})$")),
    (IdKind.LEAVE_POLICY, re.compile(r"^LPO-(?P<sequence>00[1-6])$")),
    (IdKind.EXPENSE_POLICY, re.compile(r"^XPO-(?P<sequence>\d{4})$")),
    (IdKind.COST_CENTER, re.compile(r"^CC-(?P<sequence>\d{4})$")),
    (IdKind.APPROVAL_RULE, re.compile(r"^ARL-(?P<sequence>\d{3})$")),
    (
        IdKind.LEAVE_BALANCE,
        re.compile(r"^LBL-(?P<employee_id>EMP-\d{6})-(?P<policy_id>LPO-00[1-6])-2026$"),
    ),
    (
        IdKind.HOLIDAY,
        re.compile(r"^HOL-2026-(?P<country>IN|US|GB|DE|SG)-(?P<sequence>0[1-8])$"),
    ),
    (IdKind.LEAVE_LEDGER_ENTRY, re.compile(r"^LLE-2026-(?P<sequence>\d{6})$")),
    (IdKind.LEAVE_REQUEST_EVENT, re.compile(r"^LRE-2026-(?P<sequence>\d{6})$")),
    (IdKind.EXPENSE_CLAIM_EVENT, re.compile(r"^ECE-2026-(?P<sequence>\d{6})$")),
    (IdKind.DECISION_AUDIT, re.compile(r"^DAU-2026-(?P<sequence>\d{6})$")),
    (IdKind.AUDIT_FINDING, re.compile(r"^AFN-2026-(?P<sequence>\d{6})$")),
    (IdKind.AUDIT_FINDING_EVENT, re.compile(r"^AFE-2026-(?P<sequence>\d{6})$")),
    (IdKind.GROUND_TRUTH_ANOMALY, re.compile(r"^GTA-2026-(?P<sequence>\d{6})$")),
    (IdKind.GROUND_TRUTH_DECISION, re.compile(r"^GTD-2026-(?P<sequence>\d{6})$")),
)


def parse_id(value: str) -> RuleResult[ParsedId]:
    """Parse a documented entity ID without coercing malformed IDs (G1, D1)."""

    if not isinstance(value, str):
        return failure(
            reason_codes=("INVALID_ID_FORMAT",), rule_ids=("G1",), message="ID must be a string."
        )
    for kind, pattern in _PATTERNS:
        match = pattern.fullmatch(value)
        if match is None:
            continue
        groups = match.groupdict()
        sequence = int(groups["sequence"]) if groups.get("sequence") else 0
        if groups.get("sequence") and sequence == 0:
            return failure(
                reason_codes=("INVALID_ID_SEQUENCE",),
                rule_ids=("G1", "D1"),
                message="Identifier sequence must be greater than zero.",
            )
        parsed = ParsedId(
            kind=kind,
            sequence=sequence,
            parent_id=groups.get("parent_id"),
            employee_id=groups.get("employee_id"),
            policy_id=groups.get("policy_id"),
            country=CountryCode(groups["country"]) if groups.get("country") else None,
        )
        return success(
            parsed,
            reason_codes=("ID_PARSED",),
            rule_ids=("G1", "D1"),
            message=f"Parsed {kind.value} identifier.",
        )
    return failure(
        reason_codes=("INVALID_ID_FORMAT",),
        rule_ids=("G1", "D1"),
        message="ID does not match any documented RouteIQ identifier format.",
    )


def validate_id(value: str, kind: IdKind | None = None) -> RuleResult[bool]:
    """Validate an identifier, optionally requiring a specific entity kind (G1, D1)."""

    parsed = parse_id(value)
    if not parsed.ok or parsed.value is None:
        return failure(
            reason_codes=parsed.reason_codes,
            rule_ids=parsed.rule_ids,
            message=parsed.messages[0],
            value=False,
        )
    if kind is not None and parsed.value.kind != kind:
        return failure(
            reason_codes=("ID_KIND_MISMATCH",),
            rule_ids=("G1", "D1"),
            message=f"Expected {kind.value}, received {parsed.value.kind.value}.",
            value=False,
        )
    return success(
        True,
        reason_codes=("ID_VALID",),
        rule_ids=("G1", "D1"),
        message=f"{parsed.value.kind.value} identifier is valid.",
    )


def format_id(
    kind: IdKind,
    sequence: int,
    *,
    parent_id: str | None = None,
    employee_id: str | None = None,
    policy_id: str | None = None,
    country: CountryCode | None = None,
) -> RuleResult[str]:
    """Format one immutable identifier using its documented zero-padding (G1, D1)."""

    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        return failure(
            reason_codes=("INVALID_ID_SEQUENCE",),
            rule_ids=("G1", "D1"),
            message="Identifier sequence must be a positive integer.",
        )

    simple_prefixes = {
        IdKind.EMPLOYEE: ("EMP-", 6, 999_999),
        IdKind.LEAVE_REQUEST: ("LVE-2026-", 6, 999_999),
        IdKind.EXPENSE_CLAIM: ("EXP-2026-", 6, 999_999),
        IdKind.REIMBURSEMENT: ("RMB-2026-", 6, 999_999),
        IdKind.LEAVE_POLICY: ("LPO-", 3, 6),
        IdKind.EXPENSE_POLICY: ("XPO-", 4, 9_999),
        IdKind.COST_CENTER: ("CC-", 4, 9_999),
        IdKind.APPROVAL_RULE: ("ARL-", 3, 999),
        IdKind.LEAVE_LEDGER_ENTRY: ("LLE-2026-", 6, 999_999),
        IdKind.LEAVE_REQUEST_EVENT: ("LRE-2026-", 6, 999_999),
        IdKind.EXPENSE_CLAIM_EVENT: ("ECE-2026-", 6, 999_999),
        IdKind.DECISION_AUDIT: ("DAU-2026-", 6, 999_999),
        IdKind.AUDIT_FINDING: ("AFN-2026-", 6, 999_999),
        IdKind.AUDIT_FINDING_EVENT: ("AFE-2026-", 6, 999_999),
        IdKind.GROUND_TRUTH_ANOMALY: ("GTA-2026-", 6, 999_999),
        IdKind.GROUND_TRUTH_DECISION: ("GTD-2026-", 6, 999_999),
    }

    if kind in simple_prefixes:
        prefix, width, maximum = simple_prefixes[kind]
        if sequence > maximum:
            return failure(
                reason_codes=("INVALID_ID_SEQUENCE",),
                rule_ids=("G1", "D1"),
                message=f"{kind.value} sequence exceeds its supported range.",
            )
        candidate = f"{prefix}{sequence:0{width}d}"
    elif kind in (IdKind.EXPENSE_LINE, IdKind.APPROVAL_STEP):
        parent_kind = IdKind.EXPENSE_CLAIM if kind == IdKind.EXPENSE_LINE else None
        parsed_parent = parse_id(parent_id or "")
        valid_parent = parsed_parent.ok and parsed_parent.value is not None
        if (
            not valid_parent
            or (parent_kind is not None and parsed_parent.value.kind != parent_kind)
            or (
                kind == IdKind.APPROVAL_STEP
                and parsed_parent.value.kind
                not in (
                    IdKind.LEAVE_REQUEST,
                    IdKind.EXPENSE_CLAIM,
                )
            )
        ):
            return failure(
                reason_codes=("INVALID_ID_PARENT",),
                rule_ids=("G1", "D1"),
                message=f"{kind.value} requires a valid parent request ID.",
            )
        if sequence > 99:
            return failure(
                reason_codes=("INVALID_ID_SEQUENCE",),
                rule_ids=("G1", "D1"),
                message=f"{kind.value} sequence must fit its two-digit suffix.",
            )
        candidate = f"{'EXPL' if kind == IdKind.EXPENSE_LINE else 'APR'}-{parent_id}-{sequence:02d}"
    elif kind == IdKind.LEAVE_BALANCE:
        if employee_id is None or policy_id is None:
            return failure(
                reason_codes=("ID_COMPONENT_REQUIRED",),
                rule_ids=("G1", "D1"),
                message="Leave-balance IDs require employee_id and leave_policy_id.",
            )
        if (
            not validate_id(employee_id, IdKind.EMPLOYEE).ok
            or not validate_id(policy_id, IdKind.LEAVE_POLICY).ok
        ):
            return failure(
                reason_codes=("INVALID_ID_COMPONENT",),
                rule_ids=("G1", "D1"),
                message="Leave-balance ID components must be valid employee and policy IDs.",
            )
        if sequence != 2026:
            return failure(
                reason_codes=("INVALID_ID_YEAR",),
                rule_ids=("G1", "D1"),
                message="Leave-balance IDs are fixed to balance year 2026.",
            )
        candidate = f"LBL-{employee_id}-{policy_id}-2026"
    elif kind == IdKind.HOLIDAY:
        if country is None or sequence > 8:
            return failure(
                reason_codes=("INVALID_HOLIDAY_ID_COMPONENT",),
                rule_ids=("G3",),
                message="Holiday IDs require a supported country and sequence from 1 through 8.",
            )
        candidate = f"HOL-2026-{country.value}-{sequence:02d}"
    else:
        return failure(
            reason_codes=("UNSUPPORTED_ID_KIND",),
            rule_ids=("G1", "D1"),
            message="Unsupported identifier kind.",
        )

    validated = validate_id(candidate, kind)
    if not validated.ok:
        return failure(
            reason_codes=validated.reason_codes,
            rule_ids=validated.rule_ids,
            message=validated.messages[0],
        )
    return success(
        candidate,
        reason_codes=("ID_FORMATTED",),
        rule_ids=("G1", "D1"),
        message=f"Formatted {kind.value} identifier.",
    )
