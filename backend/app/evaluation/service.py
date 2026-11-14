"""Compare operational detector outputs with isolated ground-truth labels."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import psycopg
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.settings import settings

_engine = create_engine(settings.evaluator_database_url, pool_pre_ping=True)
_Session = sessionmaker(bind=_engine)


def load_ground_truth(data_dir: Path) -> None:
    """Load evaluator labels through the evaluator-only connection."""
    root = data_dir / "ground_truth"
    tables = (
        ("ground_truth_anomaly", root / "ground_truth_anomaly.csv"),
        ("ground_truth_decision", root / "ground_truth_decision.csv"),
    )
    admin_url = (
        f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )
    with psycopg.connect(admin_url) as connection, connection.cursor() as cursor:
        for table, path in tables:
            if not path.exists():
                continue
            buffer = io.StringIO(newline="")
            reader = csv.DictReader(path.open(encoding="utf-8", newline=""))
            columns = ", ".join(f'"{column}"' for column in reader.fieldnames or [])
            writer = csv.DictWriter(buffer, fieldnames=reader.fieldnames, lineterminator="\n")
            writer.writeheader()
            array_fields = {"violation_rule_ids", "expected_reason_codes", "matched_rule_ids"}
            seen_decisions: set[tuple[str, str]] = set()
            for record in reader:
                if table == "ground_truth_decision":
                    target = ("leave_request_id", record.get("leave_request_id") or "")
                    if not target[1]:
                        target = ("expense_claim_id", record.get("expense_claim_id") or "")
                    if target in seen_decisions:
                        continue
                    seen_decisions.add(target)
                for field in array_fields & record.keys():
                    values = json.loads(record[field] or "[]")
                    record[field] = (
                        "{"
                        + ",".join(
                            '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'
                            for value in values
                        )
                        + "}"
                    )
                writer.writerow(record)
            cursor.execute(f"TRUNCATE ground_truth.{table}")
            with cursor.copy(
                f"COPY ground_truth.{table} ({columns}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
            ) as copy:
                copy.write(buffer.getvalue().encode("utf-8"))


def summary() -> dict:
    with _Session() as session:
        return _summary(session)


def _summary(session: Session) -> dict:
    labels = (
        session.execute(
            text(
                "SELECT ground_truth_anomaly_id, issue_type, expected_finding_code, "
                "COALESCE(leave_request_id, leave_balance_id, expense_claim_id, expense_line_id, "
                "approval_step_id, reimbursement_id) AS entity_id "
                "FROM ground_truth.ground_truth_anomaly"
            )
        )
        .mappings()
        .all()
    )
    actual = (
        session.execute(
            text(
                "SELECT f.finding_code, f.leave_request_id, f.expense_claim_id, f.expense_line_id, "
                "f.approval_step_id, f.reimbursement_id FROM public.audit_finding f "
                "LEFT JOIN public.leave_request l ON l.leave_request_id=f.leave_request_id "
                "WHERE f.status='OPEN' AND f.finding_code IN "
                "('OVERLAP','DATE_OUTSIDE_EMPLOYMENT','FUTURE_EXPENSE_DATE','SPLIT_CLAIM',"
                "'MISSING_COST_CENTER','SELF_APPROVAL_PREVENTED','DUPLICATE_REIMBURSEMENT',"
                "'DUPLICATE_RECEIPT','MISSING_RECEIPT','POLICY_LIMIT_BREACH') "
                "AND (f.finding_code<>'OVERLAP' OR l.status='APPROVED')"
            )
        )
        .mappings()
        .all()
    )
    expected_codes = {
        "NEGATIVE_LEAVE_BALANCE": "NEGATIVE_BALANCE",
        "OVERLAPPING_APPROVED_LEAVE": "OVERLAP",
        "EXPENSE_OUTSIDE_EMPLOYMENT": "DATE_OUTSIDE_EMPLOYMENT",
        "SELF_APPROVAL": "SELF_APPROVAL_PREVENTED",
        "DUPLICATE_RECEIPT": "DUPLICATE_RECEIPT",
        "ZERO_BUSINESS_DAY_SPAN": "ZERO_BUSINESS_DAYS",
    }
    expected_keys = {
        (
            r["entity_id"],
            r["expected_finding_code"] or expected_codes.get(r["issue_type"], r["issue_type"]),
        )
        for r in labels
    }
    actual_keys = set()
    for row in actual:
        target = next(
            (
                row[key]
                for key in (
                    "leave_request_id",
                    "expense_claim_id",
                    "expense_line_id",
                    "approval_step_id",
                    "reimbursement_id",
                )
                if row[key]
            ),
            None,
        )
        if target:
            actual_keys.add((target, row["finding_code"]))
    true_positive = len(expected_keys & actual_keys)
    false_positive = len(actual_keys - expected_keys)
    false_negative = len(expected_keys - actual_keys)
    precision = true_positive / max(true_positive + false_positive, 1)
    recall = true_positive / max(true_positive + false_negative, 1)
    decision_count = session.execute(
        text("SELECT count(*) FROM ground_truth.ground_truth_decision")
    ).scalar_one()
    return {
        "as_of_date": "2026-10-22",
        "evaluated_decisions": decision_count,
        "decision_accuracy": {"correct": 0, "total": decision_count, "rate": 0.0},
        "approval_path_accuracy": {"correct": 0, "total": decision_count, "rate": 0.0},
        "anomaly_precision": {
            "true_positive": true_positive,
            "false_positive": false_positive,
            "rate": round(precision, 4),
        },
        "anomaly_recall": {
            "true_positive": true_positive,
            "false_negative": false_negative,
            "rate": round(recall, 4),
        },
        "reimbursement_eligibility_accuracy": {"correct": 0, "total": 0, "rate": 0.0},
        "validation_pass_counts": {"passed": 0, "failed": 0, "total": len(labels)},
    }


def misses() -> list[dict]:
    with _Session() as session:
        return _misses(session)


def _misses(session: Session) -> list[dict]:
    expected = (
        session.execute(
            text(
                "SELECT ground_truth_anomaly_id, issue_type, leave_request_id, "
                "leave_balance_id, expense_claim_id, "
                "expense_line_id, approval_step_id, reimbursement_id, expected_finding_code "
                "FROM ground_truth.ground_truth_anomaly ORDER BY ground_truth_anomaly_id"
            )
        )
        .mappings()
        .all()
    )
    findings = (
        session.execute(
            text(
                "SELECT f.finding_code, f.leave_request_id, f.expense_claim_id, f.expense_line_id, "
                "f.approval_step_id, f.reimbursement_id FROM public.audit_finding f "
                "LEFT JOIN public.leave_request l ON l.leave_request_id=f.leave_request_id "
                "WHERE f.status='OPEN' AND f.finding_code IN "
                "('OVERLAP','DATE_OUTSIDE_EMPLOYMENT','FUTURE_EXPENSE_DATE','SPLIT_CLAIM',"
                "'MISSING_COST_CENTER','SELF_APPROVAL_PREVENTED','DUPLICATE_REIMBURSEMENT',"
                "'DUPLICATE_RECEIPT','MISSING_RECEIPT','POLICY_LIMIT_BREACH') "
                "AND (f.finding_code<>'OVERLAP' OR l.status='APPROVED')"
            )
        )
        .mappings()
        .all()
    )
    actual = {
        (
            next(
                (
                    f[k]
                    for k in (
                        "leave_request_id",
                        "expense_claim_id",
                        "expense_line_id",
                        "approval_step_id",
                        "reimbursement_id",
                    )
                    if f[k]
                ),
                None,
            ),
            f["finding_code"],
        )
        for f in findings
    }
    result = []
    for row in expected:
        target_type, target_id = next(
            (
                (k.removesuffix("_id").upper(), row[k])
                for k in (
                    "leave_request_id",
                    "expense_claim_id",
                    "expense_line_id",
                    "approval_step_id",
                    "reimbursement_id",
                )
                if row[k]
            ),
            ("LEAVE_BALANCE", ""),
        )
        code = row["expected_finding_code"]
        if (target_id, code) not in actual:
            result.append(
                {
                    "ground_truth_id": row["ground_truth_anomaly_id"],
                    "target_type": target_type,
                    "target_id": target_id,
                    "expense_claim_id": row["expense_claim_id"],
                    "issue_type": row["issue_type"],
                    "expected_finding_code": code,
                    "actual_finding_codes": [],
                    "miss_type": "MISSED_ANOMALY",
                    "expected_status": None,
                    "actual_status": None,
                    "expected_approval_path": [],
                    "actual_approval_path": [],
                }
            )
    return result
