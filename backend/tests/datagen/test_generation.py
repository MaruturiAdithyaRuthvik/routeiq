"""End-to-end invariants for the deterministic starter dataset."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd
import pytest

from app.datagen.context import GenerationContext, Row, create_context
from app.datagen.export import export_dataset
from app.datagen.pipeline import generate_dataset
from app.engine.ids import IdKind, validate_id
from app.engine.leave import balance_from_ledger


@pytest.fixture(scope="module")
def generated() -> GenerationContext:
    return generate_dataset(create_context(20261022, "starter"))


def test_starter_counts_and_entity_ids(generated: GenerationContext) -> None:
    assert len(generated.get_rows("employee")) == 40
    assert len(generated.get_rows("leave_policy")) == 6
    assert len(generated.get_rows("leave_request")) == 80
    assert len(generated.get_rows("expense_claim")) == 100

    entity_ids = (
        ("employee", "employee_id", IdKind.EMPLOYEE),
        ("leave_request", "leave_request_id", IdKind.LEAVE_REQUEST),
        ("expense_claim", "expense_claim_id", IdKind.EXPENSE_CLAIM),
        ("expense_line", "expense_line_id", IdKind.EXPENSE_LINE),
        ("approval_step", "approval_step_id", IdKind.APPROVAL_STEP),
        ("reimbursement", "reimbursement_id", IdKind.REIMBURSEMENT),
    )
    for table, field, kind in entity_ids:
        for row in generated.get_rows(table):
            assert validate_id(row[field], kind).ok


def test_foreign_keys_hierarchy_and_assignments(generated: GenerationContext) -> None:
    employees = {row["employee_id"]: row for row in generated.get_rows("employee")}
    centers = {row["cost_center_id"]: row for row in generated.get_rows("cost_center")}
    leave_ids = {row["leave_request_id"] for row in generated.get_rows("leave_request")}
    claim_ids = {row["expense_claim_id"] for row in generated.get_rows("expense_claim")}
    line_ids = {row["expense_line_id"] for row in generated.get_rows("expense_line")}
    policy_ids = {row["expense_policy_id"] for row in generated.get_rows("expense_policy")}

    for employee in employees.values():
        assert employee["manager_id"] is None or employee["manager_id"] in employees
        assert employee["cost_center_id"] in centers
        visited: set[str] = set()
        current = employee
        while current["manager_id"] is not None:
            assert current["employee_id"] not in visited
            visited.add(current["employee_id"])
            current = employees[current["manager_id"]]

    assigned = {row["employee_id"] for row in generated.get_rows("employee_cost_center_assignment")}
    assert assigned == set(employees)
    assert {row["system_role"] for row in employees.values()} == {
        "REQUESTER",
        "APPROVER",
        "PROCESS_OWNER",
        "ANALYST",
        "ADMIN",
    }
    assert all(row["owner_employee_id"] in employees for row in centers.values())
    assert all(
        row["leave_request_id"] in leave_ids
        for row in generated.get_rows("leave_ledger_entry")
        if row["leave_request_id"]
    )
    assert all(row["expense_claim_id"] in claim_ids for row in generated.get_rows("expense_line"))
    assert all(row["expense_policy_id"] in policy_ids for row in generated.get_rows("expense_line"))
    assert all(
        row["expense_line_id"] in line_ids
        for row in generated.get_rows("audit_finding")
        if row["expense_line_id"]
    )


def test_approval_and_reimbursement_invariants(generated: GenerationContext) -> None:
    claims = {row["expense_claim_id"]: row for row in generated.get_rows("expense_claim")}
    steps = generated.get_rows("approval_step")
    steps_by_claim: dict[str, list[Row]] = {}
    for step in steps:
        if step["expense_claim_id"] is not None:
            steps_by_claim.setdefault(step["expense_claim_id"], []).append(step)

    for reimbursement in generated.get_rows("reimbursement"):
        claim = claims[reimbursement["expense_claim_id"]]
        assert claim["status"] == "REIMBURSED"
        assert steps_by_claim[claim["expense_claim_id"]]
        assert all(
            step["status"] == "APPROVED" for step in steps_by_claim[claim["expense_claim_id"]]
        )

    assert generated.validation["multi_level_share"] >= 0.15
    assert generated.references["leave_paths"]["LVE-2026-000052"]


def test_injected_anomalies_are_labeled(generated: GenerationContext) -> None:
    anomalies = generated.get_rows("ground_truth_anomaly")
    balances = {row["leave_balance_id"]: row for row in generated.get_rows("leave_balance")}
    claims = {row["expense_claim_id"]: row for row in generated.get_rows("expense_claim")}
    reimbursements = {row["reimbursement_id"]: row for row in generated.get_rows("reimbursement")}
    labels = {row["issue_type"] for row in anomalies}
    assert {
        "NEGATIVE_LEAVE_BALANCE",
        "OVERLAPPING_APPROVED_LEAVE",
        "ZERO_BUSINESS_DAY_SPAN",
        "INSUFFICIENT_BALANCE",
        "MISSING_RECEIPT",
        "DUPLICATE_RECEIPT",
        "POLICY_LIMIT_BREACH",
        "MISSING_COST_CENTER",
        "EXPENSE_OUTSIDE_EMPLOYMENT",
        "FUTURE_EXPENSE_DATE",
        "SELF_APPROVAL",
        "DUPLICATE_REIMBURSEMENT",
    }.issubset(labels)
    for anomaly in anomalies:
        targets = (
            anomaly["leave_request_id"],
            anomaly["leave_balance_id"],
            anomaly["expense_claim_id"],
            anomaly["expense_line_id"],
            anomaly["approval_step_id"],
            anomaly["reimbursement_id"],
        )
        assert sum(target is not None for target in targets) == 1
        if anomaly["issue_type"] == "NEGATIVE_LEAVE_BALANCE":
            assert balances[anomaly["leave_balance_id"]]["available_days"] < 0
        if anomaly["issue_type"] == "DUPLICATE_REIMBURSEMENT":
            assert anomaly["reimbursement_id"] in reimbursements
    exceptional_claims = {
        row["expense_claim_id"]
        for row in anomalies
        if row["issue_type"] in ("EXPENSE_OUTSIDE_EMPLOYMENT", "FUTURE_EXPENSE_DATE")
    }
    for claim in claims.values():
        if (
            claim["submitted_at"] is not None
            and claim["expense_claim_id"] not in exceptional_claims
        ):
            assert claim["expense_date"] < claim["submitted_at"].date()


def test_leave_ledger_reconciles_snapshots(generated: GenerationContext) -> None:
    ledger_models = generated.references["ledger_models"]
    for balance in generated.get_rows("leave_balance"):
        entries = tuple(
            entry
            for entry in ledger_models
            if entry.employee_id == balance["employee_id"]
            and entry.leave_policy_id == balance["leave_policy_id"]
        )
        result = balance_from_ledger(entries, policy_id=balance["leave_policy_id"])
        assert result.value == balance["available_days"]


def test_generation_is_deterministic(generated: GenerationContext) -> None:
    second = generate_dataset(create_context(20261022, "starter"))
    assert generated.frames.keys() == second.frames.keys()
    for table in sorted(generated.frames):
        pd.testing.assert_frame_equal(generated.frames[table], second.frames[table])


def test_export_keeps_ground_truth_separate(generated: GenerationContext, tmp_path: Path) -> None:
    manifest = export_dataset(generated, tmp_path)
    operational_files = {path.name for path in (tmp_path / "operational").glob("*.csv")}
    assert "ground_truth_anomaly.csv" not in operational_files
    assert "ground_truth_decision.csv" not in operational_files
    assert (tmp_path / "ground_truth" / "ground_truth_anomaly.csv").is_file()
    ground_truth = json.loads((tmp_path / "ground_truth" / "ground_truth.json").read_text())
    assert (
        len(ground_truth["anomalies"])
        == manifest["ground_truth_row_counts"]["ground_truth_anomaly"]
    )
    assert "ground_truth/ground_truth.json" in manifest["checksums_sha256"]


def test_engine_has_no_ground_truth_imports() -> None:
    engine_directory = Path(__file__).parents[2] / "app" / "engine"
    backend_directory = engine_directory.parent
    guarded_sources = [
        *engine_directory.rglob("*.py"),
        backend_directory / "datagen" / "pipeline.py",
        backend_directory / "datagen" / "validation.py",
    ]
    for source in sorted(guarded_sources):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        imported_modules = [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        ]
        imported_modules.extend(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        assert all("ground_truth" not in name for name in imported_modules), source
        if source.parent.name == "datagen":
            assert "ground_truth" not in source.read_text(encoding="utf-8"), source
