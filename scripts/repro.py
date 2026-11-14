"""Generate twice into scratch directories and compare every output checksum."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "data" / "tmp"


def hashes(directory: Path) -> dict[str, str]:
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main() -> int:
    shutil.rmtree(TMP / "run1", ignore_errors=True)
    shutil.rmtree(TMP / "run2", ignore_errors=True)
    for name in ("run1", "run2"):
        subprocess.run(
            [sys.executable, "-m", "app.datagen", "--seed", "20261022", "--scale", "full",
             "--out", str(TMP / name)],
            cwd=ROOT / "backend", check=True, stdout=subprocess.DEVNULL,
        )
    first, second = hashes(TMP / "run1"), hashes(TMP / "run2")
    equal = first == second
    lines = [
        "# Reproducibility report", "",
        f"Result: **{'PASS' if equal else 'FAIL'}**",
        "Seed: `20261022`; scale: `full`.",
        f"Files compared: {len(first)} vs {len(second)}.",
        "", "| File | SHA-256 run 1 | SHA-256 run 2 | Match |",
        "|---|---|---|---|",
    ]
    for name in sorted(first.keys() | second.keys()):
        lines.append(f"| `{name}` | `{first.get(name, 'MISSING')}` | "
                     f"`{second.get(name, 'MISSING')}` | {first.get(name) == second.get(name)} |")
    (ROOT / "data" / "reproducibility_report.md").write_text("\n".join(lines) + "\n")
    return 0 if equal else 1


if __name__ == "__main__":
    raise SystemExit(main())
