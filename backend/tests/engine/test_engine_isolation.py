"""Protect the pure engine boundary from database and ground-truth access."""

import ast
from pathlib import Path

ENGINE_DIRECTORY = Path(__file__).parents[2] / "app" / "engine"
FORBIDDEN_IMPORT_ROOTS = {
    "fastapi",
    "sqlalchemy",
    "psycopg",
    "ground_truth",
}
FORBIDDEN_DATABASE_CALLS = {"connect", "execute", "exec_driver_sql", "query"}


def test_engine_has_no_database_framework_or_ground_truth_imports() -> None:
    for source_path in sorted(ENGINE_DIRECTORY.glob("*.py")):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots = {alias.name.split(".", maxsplit=1)[0] for alias in node.names}
                assert not imported_roots.intersection(FORBIDDEN_IMPORT_ROOTS), source_path
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".", maxsplit=1)[0]
                assert root not in FORBIDDEN_IMPORT_ROOTS, source_path
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in FORBIDDEN_DATABASE_CALLS, source_path


def test_engine_contains_no_ground_truth_schema_sql() -> None:
    for source_path in sorted(ENGINE_DIRECTORY.glob("*.py")):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                normalized = " ".join(node.value.casefold().split())
                assert "ground_truth." not in normalized, source_path
                assert "from ground_truth" not in normalized, source_path
                assert "join ground_truth" not in normalized, source_path
