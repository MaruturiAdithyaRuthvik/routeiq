"""Stable CSV/JSON export and checksum manifest generation."""

from __future__ import annotations

import csv
import hashlib
import io
import json
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
    return manifest


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
