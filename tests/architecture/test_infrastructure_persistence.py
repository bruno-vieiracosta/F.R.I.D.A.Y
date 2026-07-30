import ast
from pathlib import Path

import pytest

FORBIDDEN_INFRASTRUCTURE_PERSISTENCE_IMPORTS = {
    "friday.ai",
    "friday.desktop",
    "friday.domain",
    "friday.integrations",
}
FORBIDDEN_APPLICATION_IMPORTS = {
    "alembic",
    "sqlite3",
    "sqlalchemy",
    "friday.infrastructure",
}
FORBIDDEN_ORM_MODEL_MARKERS = {
    "DeclarativeBase",
    "Mapped[",
    "declarative_base",
    "mapped_column",
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


def _source_from_files(root: Path) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.py"))


@pytest.mark.architecture
def test_infrastructure_persistence_does_not_depend_on_forbidden_layers() -> None:
    root = Path(__file__).resolve().parents[2] / "friday" / "infrastructure"
    persistence_root = root / "persistence"

    imports: set[str] = set()
    for path in persistence_root.rglob("*.py"):
        imports.update(_imports_from_file(path))

    for forbidden_import in FORBIDDEN_INFRASTRUCTURE_PERSISTENCE_IMPORTS:
        assert forbidden_import not in imports
        assert not any(
            imported.startswith(f"{forbidden_import}.") for imported in imports
        )


@pytest.mark.architecture
def test_application_remains_independent_from_database_technology() -> None:
    application_root = Path(__file__).resolve().parents[2] / "friday" / "application"

    imports: set[str] = set()
    for path in application_root.rglob("*.py"):
        imports.update(_imports_from_file(path))

    for forbidden_import in FORBIDDEN_APPLICATION_IMPORTS:
        assert forbidden_import not in imports
        assert not any(
            imported.startswith(f"{forbidden_import}.") for imported in imports
        )


@pytest.mark.architecture
def test_database_foundation_does_not_define_orm_models() -> None:
    persistence_root = (
        Path(__file__).resolve().parents[2] / "friday" / "infrastructure"
    ) / "persistence"
    source = _source_from_files(persistence_root)

    for marker in FORBIDDEN_ORM_MODEL_MARKERS:
        assert marker not in source
