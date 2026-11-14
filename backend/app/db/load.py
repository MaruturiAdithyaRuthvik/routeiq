"""Load generated operational CSVs into PostgreSQL in foreign-key-safe order."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg

TABLE_ORDER = (
    "employee", "leave_policy", "expense_category", "cost_center", "leave_balance",
    "leave_request", "expense_policy", "expense_claim", "expense_line", "approval_rule",
    "employee_cost_center_assignment", "approval_rule_category", "approval_step",
    "reimbursement", "holiday", "leave_request_event", "expense_claim_event",
    "leave_ledger_entry", "decision_audit", "audit_finding", "audit_finding_event",
)


def _database_url() -> str:
    if "DATABASE_URL" in os.environ:
        return os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    root = Path(__file__).resolve().parents[3]
    env_file = root / ".env"
    values = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key] = value
    return values.get("DATABASE_URL", "postgresql://routeiq_app_login:routeiq_app_dev_only@localhost:5432/routeiq").replace(
        "postgresql+psycopg://", "postgresql://"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="source", type=Path, required=True)
    args = parser.parse_args()
    with psycopg.connect(_database_url()) as connection, connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL DEFERRED")
        for table in TABLE_ORDER:
            path = args.source / f"{table}.csv"
            if not path.exists():
                continue
            header = path.read_text(encoding="utf-8").splitlines()[0]
            columns = ", ".join(f'"{column}"' for column in header.split(","))
            with cursor.copy(
                f"COPY public.{table} ({columns}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
            ) as copy:
                copy.write(path.read_bytes())
    print(f"Loaded operational CSVs from {args.source}")


if __name__ == "__main__":
    main()
