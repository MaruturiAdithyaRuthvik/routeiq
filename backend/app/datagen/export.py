"""Stable CSV/JSON export and checksum manifest generation."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from .context import GenerationContext, Row

_GROUND_TRUTH_TABLES = ("ground_truth_anomaly", "ground_truth_decision")
_GENERATOR_VERSION = "1.0.0"


def export_dataset(context: GenerationContext, output_directory: Path) -> dict[str, Any]:
    """Write deterministic operational CSVs, isolated labels, and a checksummed manifest."""

    operational_dir = output_directory / "operational"
    ground_truth_dir = output_directory / "ground_truth"
    operational_dir.mkdir(parents=True, exist_ok=True)
    ground_truth_dir.mkdir(parents=True, exist_ok=True)

    checksums: dict[str, str] = {}
    operational_counts: dict[str, int] = {}
    ground_truth_counts: dict[str, int] = {}
    for table in sorted(context.frames):
        rows = context.get_rows(table)
        if table in _GROUND_TRUTH_TABLES:
            relative = f"ground_truth/{table}.csv"
            csv_path = output_directory / relative
            _write_csv(csv_path, rows)
            checksums[relative] = _checksum(csv_path)
            ground_truth_counts[table] = len(rows)
        else:
            relative = f"operational/{table}.csv"
            csv_path = output_directory / relative
            _write_csv(csv_path, rows)
            checksums[relative] = _checksum(csv_path)
            operational_counts[table] = len(rows)

    ground_truth_json = {
        "anomalies": context.get_rows("ground_truth_anomaly"),
        "decisions": context.get_rows("ground_truth_decision"),
    }
    json_path = ground_truth_dir / "ground_truth.json"
    _write_json(json_path, ground_truth_json)
    checksums["ground_truth/ground_truth.json"] = _checksum(json_path)

    manifest: dict[str, Any] = {
        "generator": "RouteIQ synthetic datagen",
        "generator_version": _GENERATOR_VERSION,
        "engine_version": "1.0.0",
        "seed": context.seed,
        "scale": context.preset.name,
        "as_of_date": context.as_of_date.isoformat(),
        "synthetic_only": True,
        "currency_reporting": "USD",
        "policy_cost_factors": {
            country: str(factor)
            for country, factor in sorted(context.references["policy_cost_factors"].items())
        },
        "operational_row_counts": operational_counts,
        "ground_truth_row_counts": ground_truth_counts,
        "checksums_sha256": dict(sorted(checksums.items())),
    }
    manifest_path = output_directory / "manifest.json"
    _write_json(manifest_path, manifest)
    _write_submission_pack(context, output_directory, manifest)
    return manifest


def _write_submission_pack(
    context: GenerationContext, output_directory: Path, manifest: dict[str, Any]
) -> None:
    csv_dir, json_dir = output_directory / "csv", output_directory / "json"
    csv_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted((output_directory / "operational").glob("*.csv")):
        shutil.copyfile(path, csv_dir / path.name)
        rows = context.get_rows(path.stem)
        _write_json(json_dir / f"{path.stem}.json", rows)
    gt_dir = output_directory / "ground_truth"
    anomaly_rows = []
    split_groups: dict[str, str] = {}
    for row in context.get_rows("ground_truth_anomaly"):
        targets = [
            ("LEAVE_REQUEST", row["leave_request_id"]),
            ("LEAVE_BALANCE", row["leave_balance_id"]),
            ("EXPENSE_CLAIM", row["expense_claim_id"]),
            ("EXPENSE_LINE", row["expense_line_id"]),
            ("APPROVAL_STEP", row["approval_step_id"]),
            ("REIMBURSEMENT", row["reimbursement_id"]),
        ]
        entity_type, entity_id = next(((kind, value) for kind, value in targets if value), ("", ""))
        issue = {
            "NEGATIVE_LEAVE_BALANCE": "NEGATIVE_BALANCE",
            "EXPENSE_OUTSIDE_EMPLOYMENT": "EXPENSE_DATE_OUTSIDE_EMPLOYMENT",
            "SELF_APPROVAL": "APPROVAL_BY_REQUESTER",
            "DUPLICATE_RECEIPT": "DUPLICATE_RECEIPT_HASH",
        }.get(row["issue_type"], row["issue_type"])
        details = row.get("details") or {}
        rule_ids = row.get("violation_rule_ids") or []
        is_baseline = row["issue_type"] in {
            "MISSING_RECEIPT", "POLICY_LIMIT_BREACH", "INSUFFICIENT_BALANCE",
            "DUPLICATE_RECEIPT", "ZERO_BUSINESS_DAY_SPAN",
        }
        split_group = ""
        if issue == "SPLIT_CLAIM":
            group_key = str(details.get("employee_id", ""))
            split_groups.setdefault(group_key, f"SPL-{len(split_groups) + 1:03d}")
            split_group = split_groups[group_key]
        anomaly_rows.append({
            "gt_id": row["ground_truth_anomaly_id"], "entity_type": entity_type,
            "entity_id": entity_id, "issue_type": issue, "injected": not is_baseline,
            "control_outcome": (
                "CAUGHT_BY_CONTROL"
                if row.get("expected_finding_code")
                else "SLIPPED_THROUGH"
            ),
            "severity": "ERROR", "rule_id": rule_ids[0] if rule_ids else "",
            "split_group_id": split_group,
            "explanation": json.dumps(details, sort_keys=True, default=_json_value),
        })
    _write_csv(gt_dir / "ground_truth_anomalies.csv", anomaly_rows)
    decision_rows = []
    for row in context.get_rows("ground_truth_decision"):
        decision_rows.append({
            "entity_id": row.get("leave_request_id") or row.get("expense_claim_id"),
            "expected_status": row["expected_status"],
            "expected_approver_path": row["expected_approval_path"],
            "expected_reason_codes": row["expected_reason_codes"],
        })
    _write_csv(gt_dir / "ground_truth_decisions.csv", decision_rows)
    _write_json(gt_dir / "ground_truth.json", {
        "anomalies": anomaly_rows, "decisions": decision_rows,
    })

    schema_dir = output_directory / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    for source in (output_directory.parent / "docs" / "DATA_DICTIONARY.md",
                   output_directory.parent / "docs" / "ERD.md"):
        if source.exists():
            shutil.copyfile(source, schema_dir / source.name)
    sql_dir = output_directory / "sql"
    sql_dir.mkdir(parents=True, exist_ok=True)
    operational_tables = [name for name in context.frames if name not in _GROUND_TRUTH_TABLES]
    with (sql_dir / "seed.sql").open("w", encoding="utf-8") as stream:
        stream.write("BEGIN;\nSET CONSTRAINTS ALL DEFERRED;\n")
        for table in operational_tables:
            rows = context.get_rows(table)
            if not rows:
                continue
            columns = list(rows[0])
            for row in rows:
                values = ", ".join(_sql_value(row.get(column)) for column in columns)
                stream.write(
                    f"INSERT INTO public.{table} ({', '.join(columns)}) VALUES ({values});\n"
                )
        stream.write("COMMIT;\n")
    source_manifest = {
        "synthetic_only": True, "external_data": False, "seed": context.seed,
        "as_of_date": context.as_of_date.isoformat(), "command":
            "make generate (seed 20261022; scale full)",
        "row_counts": manifest["operational_row_counts"],
    }
    _write_json(output_directory / "SOURCE_MANIFEST.json", source_manifest)
    (output_directory / "GENERATOR_COMMAND.txt").write_text(
        "make generate\n# equivalent: cd backend && uv run python -m app.datagen "
        "--seed 20261022 --scale full --out ../data\n", encoding="utf-8"
    )


def _sql_value(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (dict, list, tuple)):
        payload = json.dumps(value, sort_keys=True, default=_json_value).replace("'", "''")
        return f"'{payload}'::jsonb"
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    return "'" + _csv_value(value).replace("'", "''") + "'"


def _write_csv(path: Path, rows: list[Row]) -> None:
    columns = list(rows[0]) if rows else []
    if not columns:
        from .tables import TABLE_COLUMNS

        columns = list(TABLE_COLUMNS[path.stem])
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({column: _csv_value(row.get(column)) for column in columns})
    path.write_text(output.getvalue(), encoding="utf-8", newline="")


def _csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json_value)
    return str(value)


def _json_value(value: Any) -> str:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "value"):
        return str(value.value)
    raise TypeError(f"cannot serialize {type(value).__name__} to JSON")


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, sort_keys=True, indent=2, default=_json_value) + "\n",
        encoding="utf-8",
    )


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
