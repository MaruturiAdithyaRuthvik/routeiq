"""Fail-fast integrity checks for generated operational and ground-truth records."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from app.engine.calendar import add_business_days, business_days_between
from app.engine.ids import IdKind, validate_id
from app.engine.leave import balance_from_ledger
from app.engine.models import CountryCode, CurrencyCode, LeaveLedgerEntry
from app.engine.money import FX_TO_USD, round_half_up

from .context import COUNTRY_CURRENCIES, GenerationContext, Row


def validate_dataset(context: GenerationContext) -> dict[str, Any]:
    """Validate counts, identifiers, relationships, arithmetic, and lifecycle invariants."""

    employees = context.get_rows("employee")
    leave_policies = context.get_rows("leave_policy")
    leave_requests = context.get_rows("leave_request")
    expense_claims = context.get_rows("expense_claim")
    expense_lines = context.get_rows("expense_line")
    balances = context.get_rows("leave_balance")
    ledger_rows = context.get_rows("leave_ledger_entry")
    steps = context.get_rows("approval_step")
    reimbursements = context.get_rows("reimbursement")

    expected_counts = {
        "employee": context.preset.employees,
        "leave_policy": 6,
        "leave_request": context.preset.leave_requests,
        "expense_claim": context.preset.expense_claims,
    }
    actual_counts = {name: len(context.frames[name]) for name in expected_counts}
    if actual_counts != expected_counts:
        raise ValueError(f"dataset counts differ from scale preset: {actual_counts}")

    _validate_primary_ids(context)
    employee_by_id = {row["employee_id"]: row for row in employees}
    policy_ids = {row["leave_policy_id"] for row in leave_policies}
    cost_center_ids = {row["cost_center_id"] for row in context.get_rows("cost_center")}
    leave_ids = {row["leave_request_id"] for row in leave_requests}
    claim_ids = {row["expense_claim_id"] for row in expense_claims}

    if len(employee_by_id) != len(employees):
        raise ValueError("employee primary keys are not unique")
    if {row["country"] for row in employees} != {"IN", "US", "GB", "DE", "SG"}:
        raise ValueError("employees must cover all five supported countries")
    if len(leave_policies) != 6:
        raise ValueError("all six leave policies are required")
    _validate_operational_relations(context)
    _validate_hierarchy(employees)
    _validate_assignments(context, employee_by_id, cost_center_ids)

    employee_rows_by_id = employee_by_id
    for row in leave_requests:
        if (
            row["employee_id"] not in employee_rows_by_id
            or row["leave_policy_id"] not in policy_ids
        ):
            raise ValueError(f"leave request {row['leave_request_id']} has a dangling FK")
        if row["end_date"] < row["start_date"]:
            raise ValueError(f"leave request {row['leave_request_id']} has reversed dates")
        computed = business_days_between(
            row["start_date"],
            row["end_date"],
            CountryCode(employee_rows_by_id[row["employee_id"]]["country"]),
        )
        if computed.value is None or computed.value.count != row["business_days"]:
            raise ValueError(f"leave request {row['leave_request_id']} has incorrect business days")
        if row["status"] in ("APPROVED", "REJECTED") and not row["submitted_at"]:
            raise ValueError(
                f"terminal leave request {row['leave_request_id']} lacks submission time"
            )
    _validate_ledger(context, balances, ledger_rows, employee_by_id, policy_ids, leave_ids)

    lines_by_claim: dict[str, list[Row]] = defaultdict(list)
    for line in expense_lines:
        if line["expense_claim_id"] not in claim_ids:
            raise ValueError(f"expense line {line['expense_line_id']} has no claim")
        if line["line_number"] < 1 or line["line_number"] > 10:
            raise ValueError(f"expense line {line['expense_line_id']} is outside 1-10")
        if line["receipt_present"] != (line["receipt_hash"] is not None):
            raise ValueError(f"expense line {line['expense_line_id']} has invalid receipt metadata")
        lines_by_claim[line["expense_claim_id"]].append(line)
    claim_by_id = {row["expense_claim_id"]: row for row in expense_claims}
    for claim_id, claim_lines in lines_by_claim.items():
        claim_lines.sort(key=lambda row: row["line_number"])
        if [row["line_number"] for row in claim_lines] != list(range(1, len(claim_lines) + 1)):
            raise ValueError(f"claim {claim_id} line numbers are not sequential")
        if not 1 <= len(claim_lines) <= 10:
            raise ValueError(f"claim {claim_id} must have 1-10 lines")
        total = sum((row["amount_usd"] for row in claim_lines), Decimal("0"))
        if total != claim_by_id[claim_id]["total_usd"]:
            raise ValueError(f"claim {claim_id} total does not equal its rounded line totals")
        if claim_by_id[claim_id]["employee_id"] not in employee_by_id:
            raise ValueError(f"claim {claim_id} has a missing employee")
        center = claim_by_id[claim_id]["cost_center_id"]
        if center is not None and center not in cost_center_ids:
            raise ValueError(f"claim {claim_id} has an invalid cost center")

    _validate_steps(context, steps, leave_ids, claim_ids, employee_by_id)
    _validate_reimbursements(
        context,
        reimbursements,
        claim_by_id,
        steps,
        cost_center_ids,
        employee_by_id,
        expense_lines,
    )
    _validate_events(context)

    multi_level = sum(
        1
        for claim_id in claim_ids
        if len(context.references["expense_paths"].get(claim_id, ())) >= 2
    )
    if multi_level / max(len(expense_claims), 1) < 0.15:
        raise ValueError("fewer than 15% of expense claims have multi-level approval paths")

    summary = {
        "ok": True,
        "seed": context.seed,
        "as_of_date": context.as_of_date.isoformat(),
        "scale": context.preset.name,
        "row_counts": {name: len(frame) for name, frame in sorted(context.frames.items())},
        "multi_level_claims": multi_level,
        "multi_level_share": round(multi_level / max(len(expense_claims), 1), 4),
    }
    context.validation = summary
    return summary


def _validate_primary_ids(context: GenerationContext) -> None:
    primary_keys = {
        "employee": ("employee_id", IdKind.EMPLOYEE),
        "leave_request": ("leave_request_id", IdKind.LEAVE_REQUEST),
        "expense_claim": ("expense_claim_id", IdKind.EXPENSE_CLAIM),
        "expense_line": ("expense_line_id", IdKind.EXPENSE_LINE),
        "approval_step": ("approval_step_id", IdKind.APPROVAL_STEP),
        "reimbursement": ("reimbursement_id", IdKind.REIMBURSEMENT),
        "leave_policy": ("leave_policy_id", IdKind.LEAVE_POLICY),
        "expense_policy": ("expense_policy_id", IdKind.EXPENSE_POLICY),
        "cost_center": ("cost_center_id", IdKind.COST_CENTER),
        "approval_rule": ("approval_rule_id", IdKind.APPROVAL_RULE),
        "holiday": ("holiday_id", IdKind.HOLIDAY),
        "leave_balance": ("leave_balance_id", IdKind.LEAVE_BALANCE),
        "leave_ledger_entry": ("leave_ledger_entry_id", IdKind.LEAVE_LEDGER_ENTRY),
        "leave_request_event": ("event_id", IdKind.LEAVE_REQUEST_EVENT),
        "expense_claim_event": ("event_id", IdKind.EXPENSE_CLAIM_EVENT),
        "decision_audit": ("decision_audit_id", IdKind.DECISION_AUDIT),
        "audit_finding": ("audit_finding_id", IdKind.AUDIT_FINDING),
        "audit_finding_event": ("finding_event_id", IdKind.AUDIT_FINDING_EVENT),
    }
    for table, (field, kind) in primary_keys.items():
        identifiers = [row[field] for row in context.get_rows(table)]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError(f"{table} contains duplicate primary keys")
        for identifier in identifiers:
            checked = validate_id(identifier, kind)
            if not checked.ok:
                raise ValueError(f"invalid {table} ID {identifier}: {checked.messages[0]}")


def _validate_operational_relations(context: GenerationContext) -> None:
    employees = {row["employee_id"]: row for row in context.get_rows("employee")}
    centers = {row["cost_center_id"]: row for row in context.get_rows("cost_center")}
    leave_policies = {row["leave_policy_id"] for row in context.get_rows("leave_policy")}
    expense_categories = {row["category"] for row in context.get_rows("expense_category")}
    expense_policies = {row["expense_policy_id"]: row for row in context.get_rows("expense_policy")}
    approval_rules = {row["approval_rule_id"] for row in context.get_rows("approval_rule")}
    leave_requests = {row["leave_request_id"] for row in context.get_rows("leave_request")}
    claims_by_id = {row["expense_claim_id"]: row for row in context.get_rows("expense_claim")}
    expense_claims = set(claims_by_id)
    expense_lines = {row["expense_line_id"] for row in context.get_rows("expense_line")}
    steps = {row["approval_step_id"] for row in context.get_rows("approval_step")}
    reimbursements = {row["reimbursement_id"] for row in context.get_rows("reimbursement")}
    leave_events = {row["event_id"] for row in context.get_rows("leave_request_event")}

    for employee in employees.values():
        if employee["country"] not in COUNTRY_CURRENCIES:
            raise ValueError(f"employee {employee['employee_id']} has an unsupported country")
        if employee["home_currency"] != COUNTRY_CURRENCIES[employee["country"]]:
            raise ValueError(f"employee {employee['employee_id']} has a mismatched currency")
        if not 1 <= employee["job_level"] <= 10:
            raise ValueError(f"employee {employee['employee_id']} has an invalid job level")
        if employee["cost_center_id"] not in centers:
            raise ValueError(f"employee {employee['employee_id']} has no primary cost center")

    for center in centers.values():
        if (
            center["owner_employee_id"] not in employees
            or center["country"] not in COUNTRY_CURRENCIES
        ):
            raise ValueError(
                f"cost center {center['cost_center_id']} has an invalid owner or country"
            )
        if center["budget_year"] != 2026 or center["budget_usd"] < 0:
            raise ValueError(f"cost center {center['cost_center_id']} has an invalid budget")

    for policy in context.get_rows("expense_policy"):
        if policy["category"] not in expense_categories:
            raise ValueError(
                f"expense policy {policy['expense_policy_id']} has an invalid category"
            )
        if policy["per_line_limit_usd"] <= 0 or policy["receipt_threshold_usd"] < 0:
            raise ValueError(f"expense policy {policy['expense_policy_id']} has invalid limits")
        if policy["version"] < 1 or (
            policy["effective_to"] is not None
            and policy["effective_to"] <= policy["effective_from"]
        ):
            raise ValueError(
                f"expense policy {policy['expense_policy_id']} has invalid dates/version"
            )

    for row in context.get_rows("employee_cost_center_assignment"):
        if row["employee_id"] not in employees or row["cost_center_id"] not in centers:
            raise ValueError("employee cost-center assignment has a dangling FK")
        if not Decimal("0") < row["allocation_pct"] <= Decimal("100"):
            raise ValueError("employee cost-center assignment has an invalid allocation")
        if row["effective_to"] is not None and row["effective_to"] <= row["effective_from"]:
            raise ValueError("employee cost-center assignment has reversed dates")

    for row in context.get_rows("approval_rule"):
        if (
            row["designated_employee_id"] is not None
            and row["designated_employee_id"] not in employees
        ):
            raise ValueError(f"approval rule {row['approval_rule_id']} has a dangling holder FK")
    for row in context.get_rows("approval_rule_category"):
        if (
            row["approval_rule_id"] not in approval_rules
            or row["category"] not in expense_categories
        ):
            raise ValueError("approval rule category has a dangling FK")

    for row in context.get_rows("leave_balance"):
        if row["employee_id"] not in employees or row["leave_policy_id"] not in leave_policies:
            raise ValueError(f"leave balance {row['leave_balance_id']} has a dangling FK")
    for row in context.get_rows("expense_claim"):
        if row["employee_id"] not in employees:
            raise ValueError(f"expense claim {row['expense_claim_id']} has no employee")
        if row["cost_center_id"] is not None and row["cost_center_id"] not in centers:
            raise ValueError(f"expense claim {row['expense_claim_id']} has an invalid cost center")

    receipt_ids: set[str] = set()
    for row in context.get_rows("expense_line"):
        if row["expense_claim_id"] not in expense_claims:
            raise ValueError(f"expense line {row['expense_line_id']} has no claim")
        if row["expense_policy_id"] not in expense_policies:
            raise ValueError(f"expense line {row['expense_line_id']} has no policy")
        policy = expense_policies[row["expense_policy_id"]]
        claim = claims_by_id[row["expense_claim_id"]]
        employee = employees[claim["employee_id"]]
        if row["category"] not in expense_categories or row["category"] != policy["category"]:
            raise ValueError(
                f"expense line {row['expense_line_id']} has a mismatched policy category"
            )
        if policy["country"] != employee["country"]:
            raise ValueError(
                f"expense line {row['expense_line_id']} has a mismatched policy country"
            )
        currency = CurrencyCode(row["currency"])
        if row["fx_rate_to_usd"] != FX_TO_USD[currency]:
            raise ValueError(f"expense line {row['expense_line_id']} has an invalid FX rate")
        if row["amount"] <= 0 or row["amount_usd"] <= 0:
            raise ValueError(f"expense line {row['expense_line_id']} has a nonpositive amount")
        expected_usd = round_half_up(row["amount"] * FX_TO_USD[currency], 2)
        if expected_usd.value != row["amount_usd"]:
            raise ValueError(f"expense line {row['expense_line_id']} has an incorrect USD amount")
        if row["receipt_present"]:
            receipt_id = row["receipt_id"]
            if (
                receipt_id is None
                or receipt_id in receipt_ids
                or row["receipt_hash"] is None
                or len(row["receipt_hash"]) != 64
                or any(character not in "0123456789abcdef" for character in row["receipt_hash"])
                or row["file_type"] not in {"PDF", "JPG", "JPEG", "PNG", "HEIC"}
                or row["size_kb"] is None
                or row["size_kb"] <= 0
            ):
                raise ValueError(
                    f"expense line {row['expense_line_id']} has invalid receipt metadata"
                )
            receipt_ids.add(receipt_id)
        elif any(
            row[field] is not None
            for field in ("receipt_id", "receipt_hash", "file_type", "size_kb")
        ):
            raise ValueError(
                f"expense line {row['expense_line_id']} has receipt data without a receipt"
            )

    for row in context.get_rows("approval_step"):
        has_leave = row["leave_request_id"] is not None
        has_expense = row["expense_claim_id"] is not None
        if has_leave == has_expense:
            raise ValueError(f"approval step {row['approval_step_id']} has an invalid parent")
        if has_leave and row["leave_request_id"] not in leave_requests:
            raise ValueError(f"approval step {row['approval_step_id']} has no leave request")
        if has_expense and row["expense_claim_id"] not in expense_claims:
            raise ValueError(f"approval step {row['approval_step_id']} has no expense claim")
        if row["required_role"] == "SYSTEM":
            if row["approver_employee_id"] is not None or row["status"] != "APPROVED":
                raise ValueError("system approval must be an approved, non-employee step")
        elif row["approver_employee_id"] not in employees:
            raise ValueError(f"approval step {row['approval_step_id']} has no employee approver")

    for row in context.get_rows("reimbursement"):
        if row["expense_claim_id"] not in expense_claims:
            raise ValueError(f"reimbursement {row['reimbursement_id']} has no claim")

    ledger_entry_ids = {
        row["leave_ledger_entry_id"] for row in context.get_rows("leave_ledger_entry")
    }
    for row in context.get_rows("leave_ledger_entry"):
        if (
            row["reversal_of_entry_id"] is not None
            and row["reversal_of_entry_id"] not in ledger_entry_ids
        ):
            raise ValueError(
                f"ledger entry {row['leave_ledger_entry_id']} has a dangling reversal FK"
            )
        if row["source_event_id"] is not None and row["source_event_id"] not in leave_events:
            raise ValueError(f"ledger entry {row['leave_ledger_entry_id']} has a dangling event FK")

    for row in context.get_rows("decision_audit"):
        has_leave = row["leave_request_id"] is not None
        has_expense = row["expense_claim_id"] is not None
        if has_leave == has_expense:
            raise ValueError(
                f"decision audit {row['decision_audit_id']} has an invalid request target"
            )
        if has_leave and row["leave_request_id"] not in leave_requests:
            raise ValueError(f"decision audit {row['decision_audit_id']} has no leave request")
        if has_expense and row["expense_claim_id"] not in expense_claims:
            raise ValueError(f"decision audit {row['decision_audit_id']} has no expense claim")
        if row["recorded_at"].date() > context.as_of_date:
            raise ValueError(f"decision audit {row['decision_audit_id']} is after AS_OF_DATE")

    for row in context.get_rows("audit_finding"):
        targets = (
            row["leave_request_id"],
            row["expense_claim_id"],
            row["expense_line_id"],
            row["approval_step_id"],
            row["reimbursement_id"],
        )
        if sum(target is not None for target in targets) != 1:
            raise ValueError(f"audit finding {row['audit_finding_id']} has an invalid target")
        references = (leave_requests, expense_claims, expense_lines, steps, reimbursements)
        if any(
            target is not None and target not in refs
            for target, refs in zip(targets, references, strict=True)
        ):
            raise ValueError(f"audit finding {row['audit_finding_id']} has a dangling target FK")


def _validate_hierarchy(employees: list[Row]) -> None:
    by_id = {row["employee_id"]: row for row in employees}
    ceos = [row for row in employees if row["is_ceo"]]
    if len(ceos) != 1 or ceos[0]["manager_id"] is not None:
        raise ValueError("exactly one CEO with no manager is required")
    for row in employees:
        if row["manager_id"] is not None and row["manager_id"] not in by_id:
            raise ValueError(f"employee {row['employee_id']} has a dangling manager")
        visited: set[str] = set()
        current = row
        while current["manager_id"] is not None:
            if current["employee_id"] in visited:
                raise ValueError(f"manager hierarchy has a cycle at {current['employee_id']}")
            visited.add(current["employee_id"])
            current = by_id[current["manager_id"]]


def _validate_assignments(
    context: GenerationContext,
    employees: dict[str, Row],
    center_ids: set[str],
) -> None:
    assignment_rows = context.get_rows("employee_cost_center_assignment")
    by_employee: dict[str, list[Row]] = defaultdict(list)
    for row in assignment_rows:
        if row["employee_id"] not in employees or row["cost_center_id"] not in center_ids:
            raise ValueError("employee cost-center assignment has a dangling FK")
        by_employee[row["employee_id"]].append(row)
    if set(by_employee) != set(employees):
        raise ValueError("every employee must have at least one cost-center assignment")
    for employee_id, assignments in by_employee.items():
        employee = employees[employee_id]
        assignment_date = min(
            context.as_of_date,
            employee["termination_date"] or context.as_of_date,
        )
        active = [
            row
            for row in assignments
            if row["effective_from"] <= assignment_date
            and (row["effective_to"] is None or assignment_date < row["effective_to"])
        ]
        if not active or sum((row["allocation_pct"] for row in active), Decimal("0")) > Decimal(
            "100"
        ):
            raise ValueError(f"active allocations for {employee_id} are invalid")


def _validate_ledger(
    context: GenerationContext,
    balances: list[Row],
    ledger_rows: list[Row],
    employees: dict[str, Row],
    policy_ids: set[str],
    leave_ids: set[str],
) -> None:
    by_balance = {(row["employee_id"], row["leave_policy_id"]): row for row in balances}
    models: list[LeaveLedgerEntry] = context.references["ledger_models"]
    models_by_key: dict[tuple[str, str], list[LeaveLedgerEntry]] = defaultdict(list)
    for entry in models:
        models_by_key[(entry.employee_id, entry.leave_policy_id)].append(entry)
    for row in ledger_rows:
        if row["employee_id"] not in employees or row["leave_policy_id"] not in policy_ids:
            raise ValueError("leave ledger entry has a dangling employee or policy FK")
        if row["leave_request_id"] is not None and row["leave_request_id"] not in leave_ids:
            raise ValueError("leave ledger entry has a dangling request FK")
    for key, balance in by_balance.items():
        entries = tuple(models_by_key.get(key, ()))
        calculated = balance_from_ledger(entries, policy_id=key[1])
        if calculated.value != balance["available_days"]:
            raise ValueError(f"leave balance {balance['leave_balance_id']} does not reconcile")
        component_totals = {
            "opening_days": sum(
                (entry.delta_days for entry in entries if entry.entry_type.value == "OPENING"),
                Decimal("0"),
            ),
            "accrued_days": sum(
                (entry.delta_days for entry in entries if entry.entry_type.value == "ACCRUAL"),
                Decimal("0"),
            ),
            "adjustments_days": sum(
                (
                    entry.delta_days
                    for entry in entries
                    if (
                        entry.entry_type.value == "ADJUSTMENT"
                        or (
                            entry.entry_type.value == "REVERSAL"
                            and entry.effect_bucket.value == "AVAILABLE"
                        )
                    )
                ),
                Decimal("0"),
            ),
            "used_days": sum(
                (
                    entry.delta_days
                    for entry in entries
                    if (
                        entry.entry_type.value == "DEBIT"
                        or (
                            entry.entry_type.value == "REVERSAL"
                            and entry.effect_bucket.value == "USED"
                        )
                    )
                ),
                Decimal("0"),
            ),
            "pending_days": sum(
                (
                    entry.delta_days
                    for entry in entries
                    if (
                        entry.entry_type.value in ("RESERVE", "RELEASE")
                        or (
                            entry.entry_type.value == "REVERSAL"
                            and entry.effect_bucket.value == "RESERVED"
                        )
                    )
                ),
                Decimal("0"),
            ),
        }
        if any(balance[field] != total for field, total in component_totals.items()):
            raise ValueError(
                f"leave balance {balance['leave_balance_id']} ledger components differ"
            )


def _validate_steps(
    context: GenerationContext,
    steps: list[Row],
    leave_ids: set[str],
    claim_ids: set[str],
    employees: dict[str, Row],
) -> None:
    for step in steps:
        request_id = step["leave_request_id"] or step["expense_claim_id"]
        if (step["leave_request_id"] is not None and request_id not in leave_ids) or (
            step["expense_claim_id"] is not None and request_id not in claim_ids
        ):
            raise ValueError(f"approval step {step['approval_step_id']} has a dangling request")
        if step["required_role"] == "SYSTEM":
            if step["approver_employee_id"] is not None or step["status"] != "APPROVED":
                raise ValueError("system approval must be an approved, non-employee step")
        elif step["approver_employee_id"] not in employees:
            raise ValueError(f"approval step {step['approval_step_id']} has no approver")
        if step["status"] in ("APPROVED", "REJECTED") and step["decided_at"] is None:
            raise ValueError(
                f"terminal approval step {step['approval_step_id']} lacks decision time"
            )
        if step["status"] == "PENDING" and step["decided_at"] is not None:
            raise ValueError(
                f"pending approval step {step['approval_step_id']} has a decision time"
            )
        if step["decided_at"] is not None and step["decided_at"].date() > context.as_of_date:
            raise ValueError("an approval decision occurs after AS_OF_DATE")
    for request_id, path in context.references["expense_paths"].items():
        actual = [row["required_role"] for row in steps if row["expense_claim_id"] == request_id]
        if actual != [step.approver_type.value for step in path]:
            raise ValueError(f"expense approval steps do not match engine path for {request_id}")
    for request_id, path in context.references.get("leave_paths", {}).items():
        actual = [row["required_role"] for row in steps if row["leave_request_id"] == request_id]
        if actual != [step.approver_type.value for step in path]:
            raise ValueError(f"leave approval steps do not match engine path for {request_id}")


def _validate_reimbursements(
    context: GenerationContext,
    rows: list[Row],
    claims: dict[str, Row],
    steps: list[Row],
    center_ids: set[str],
    employees: dict[str, Row],
    expense_lines: list[Row],
) -> None:
    lines_by_id = {row["expense_line_id"]: row for row in expense_lines}
    steps_by_id = {row["approval_step_id"]: row for row in steps}
    findings = context.get_rows("audit_finding")
    duplicate_codes = {"DUPLICATE_RECEIPT", "SPLIT_CLAIM"}
    first_reimbursement_ids: dict[str, str] = {}
    for reimbursement in rows:
        claim_id = reimbursement["expense_claim_id"]
        first_reimbursement_ids[claim_id] = min(
            reimbursement["reimbursement_id"],
            first_reimbursement_ids.get(claim_id, reimbursement["reimbursement_id"]),
        )
    for row in rows:
        claim_id = row["expense_claim_id"]
        if claim_id not in claims:
            raise ValueError(f"reimbursement {row['reimbursement_id']} has no claim")
        claim = claims[claim_id]
        if claim["status"] != "REIMBURSED":
            raise ValueError(f"reimbursement exists for non-approved claim {claim_id}")
        if claim["cost_center_id"] not in center_ids:
            raise ValueError(f"reimbursement claim {claim_id} has no cost center")
        claim_steps = [step for step in steps if step["expense_claim_id"] == claim_id]
        if not claim_steps or any(step["status"] != "APPROVED" for step in claim_steps):
            raise ValueError(f"reimbursement claim {claim_id} has an unapproved step")
        if any(
            finding["finding_code"] in duplicate_codes
            and (
                finding["expense_claim_id"] == claim_id
                or (
                    finding["expense_line_id"] is not None
                    and lines_by_id[finding["expense_line_id"]]["expense_claim_id"] == claim_id
                )
                or (
                    finding["approval_step_id"] is not None
                    and steps_by_id[finding["approval_step_id"]]["expense_claim_id"] == claim_id
                )
            )
            for finding in findings
        ):
            raise ValueError(f"reimbursement claim {claim_id} has an open duplicate finding")
        employee = employees[claim["employee_id"]]
        if row["home_currency"] != employee["home_currency"]:
            raise ValueError(f"reimbursement {row['reimbursement_id']} uses the wrong currency")
        currency = CurrencyCode(row["home_currency"])
        expected_amount = round_half_up(claim["total_usd"] / FX_TO_USD[currency], 2)
        if expected_amount.value != row["amount_home_currency"]:
            raise ValueError(f"reimbursement {row['reimbursement_id']} has an incorrect amount")
        final_approval = max(
            step["decided_at"] for step in claim_steps if step["decided_at"] is not None
        )
        payment_date = add_business_days(final_approval.date(), 5, CountryCode(employee["country"]))
        is_duplicate = row["reimbursement_id"] != first_reimbursement_ids[claim_id]
        if not is_duplicate and payment_date.value != row["payment_date"]:
            raise ValueError(
                f"reimbursement {row['reimbursement_id']} has an incorrect payment date"
            )
        expected_status = "PAID" if row["payment_date"] <= context.as_of_date else "SCHEDULED"
        if row["status"] != expected_status:
            raise ValueError(f"reimbursement {row['reimbursement_id']} has an incorrect status")
        if (row["status"] == "PAID") != (row["paid_at"] is not None):
            raise ValueError(
                f"reimbursement {row['reimbursement_id']} has invalid paid_at metadata"
            )


def _validate_events(context: GenerationContext) -> None:
    employee_ids = {row["employee_id"] for row in context.get_rows("employee")}
    for table, parent in (
        ("leave_request_event", "leave_request_id"),
        ("expense_claim_event", "expense_claim_id"),
    ):
        valid_parents = {
            row["leave_request_id"] if parent == "leave_request_id" else row["expense_claim_id"]
            for row in context.get_rows(
                "leave_request" if parent == "leave_request_id" else "expense_claim"
            )
        }
        grouped: dict[str, list[Row]] = defaultdict(list)
        for row in context.get_rows(table):
            if row[parent] not in valid_parents:
                raise ValueError(f"{table} has an event with a dangling request FK")
            if (
                row["actor_employee_id"] is not None
                and row["actor_employee_id"] not in employee_ids
            ):
                raise ValueError(f"{table} has an event with a dangling actor FK")
            grouped[row[parent]].append(row)
            if row["occurred_at"].date() > context.as_of_date:
                raise ValueError(f"{table} contains an event after AS_OF_DATE")
        for parent_id, events in grouped.items():
            events.sort(key=lambda row: row["sequence_number"])
            numbers = [row["sequence_number"] for row in events]
            if numbers != sorted(set(numbers)):
                raise ValueError(f"{table} sequence is not strictly increasing for {parent_id}")
