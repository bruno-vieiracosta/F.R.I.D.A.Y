import ast
from pathlib import Path

import pytest

FORBIDDEN_PERSISTENCE_IMPORTS = {
    "alembic",
    "sqlite3",
    "sqlalchemy",
    "friday.bootstrap",
    "friday.desktop",
    "friday.infrastructure",
}


def _imports_from_file(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.add(node.module)

    return imports


@pytest.mark.architecture
def test_persistence_contracts_do_not_import_infrastructure_or_database_tools() -> None:
    root = Path(__file__).resolve().parents[2] / "friday" / "application"
    persistence_root = root / "persistence"

    imports: set[str] = set()
    for path in persistence_root.rglob("*.py"):
        imports.update(_imports_from_file(path))

    for forbidden_import in FORBIDDEN_PERSISTENCE_IMPORTS:
        assert forbidden_import not in imports
        assert not any(
            imported.startswith(f"{forbidden_import}.") for imported in imports
        )
