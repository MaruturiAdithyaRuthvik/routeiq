"""Command-line entry point for deterministic RouteIQ synthetic data generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .context import create_context
from .export import export_dataset
from .pipeline import generate_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a synthetic RouteIQ dataset.")
    parser.add_argument("--seed", type=int, default=20261022)
    parser.add_argument("--scale", choices=("starter", "full"), default="starter")
    parser.add_argument("--out", type=Path, default=Path("../data"))
    arguments = parser.parse_args()

    context = generate_dataset(create_context(arguments.seed, arguments.scale))
    manifest = export_dataset(context, arguments.out)
    print(
        json.dumps(
            {
                "validation": context.validation,
                "manifest": manifest,
                "output_directory": str(arguments.out),
            },
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
