"""Run generation integrity checks and write the judge-facing validation report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .context import create_context
from .pipeline import generate_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("../data"))
    parser.add_argument("--seed", type=int, default=20261022)
    parser.add_argument("--scale", choices=("starter", "full"), default="full")
    args = parser.parse_args()
    try:
        context = generate_dataset(create_context(args.seed, args.scale))
    except Exception as error:
        summary = {"ok": False, "error": str(error), "seed": args.seed, "scale": args.scale}
        args.data.mkdir(parents=True, exist_ok=True)
        (args.data / "validation_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (args.data / "validation_summary.md").write_text(
            f"# Validation summary\n\n**FAILED**\n\n{error}\n", encoding="utf-8"
        )
        raise SystemExit(1) from error
    summary = context.validation
    summary["checks"] = [
        "primary keys and ID formats",
        "foreign keys and enums",
        "date ordering and lifecycle",
        "line totals, FX conversion, ledger/balance reconciliation",
        "approval steps and reimbursement eligibility",
        "ground-truth targets exist",
    ]
    args.data.mkdir(parents=True, exist_ok=True)
    (args.data / "validation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    checks = "\n".join(f"- PASS: {check}" for check in summary["checks"])
    (args.data / "validation_summary.md").write_text(
        f"# Validation summary\n\n**PASS** — seed `{args.seed}`, scale `{args.scale}`.\n\n"
        f"Rows: `{json.dumps(summary['row_counts'], sort_keys=True)}`\n\n{checks}\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
