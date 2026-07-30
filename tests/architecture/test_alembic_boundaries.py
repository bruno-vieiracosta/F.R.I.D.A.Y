import ast
from pathlib import Path

import pytest

FORBIDDEN_APPLICATION_IMPORTS = {
    "alembic",
    "sqlalchemy",
    "friday.infrastructure",
}
FORBIDDEN_DOMAIN_IMPORTS = {
    "alembic",
    "sqlalchemy",
    "friday.application",
    "friday.infrastructure",
}
FORBIDDEN_DESKTOP_IMPORTS = {
    "alembic",
    "sqlalchemy",
    "friday.infrastructure",
}
FORBIDDEN_MIGRATION_TERMS = {
    "account",
    "asset",
    "cash_flow",
    "portfolio",
    "transaction",
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


def _imports_from_package(package: str) -> set[str]:
    root = Path(__file__).resolve().parents[2].joinpath(*package.split("."))
    imports: set[str] = set()

    for path in root.rglob("*.py"):
        imports.update(_imports_from_file(path))

    return imports


@pytest.mark.architecture
def test_application_remains_independent_from_alembic_and_database() -> None:
    imports = _imports_from_package("friday.application")

    for forbidden_import in FORBIDDEN_APPLICATION_IMPORTS:
        assert forbidden_import not in imports
        assert not any(
            imported.startswith(f"{forbidden_import}.") for imported in imports
        )


@pytest.mark.architecture
def test_domain_remains_independent_from_migrations() -> None:
    imports = _imports_from_package("friday.domain")

    for forbidden_import in FORBIDDEN_DOMAIN_IMPORTS:
        assert forbidden_import not in imports
        assert not any(
            imported.startswith(f"{forbidden_import}.") for imported in imports
        )


@pytest.mark.architecture
def test_desktop_does_not_depend_on_migrations_or_database() -> None:
    imports = _imports_from_package("friday.desktop")

    for forbidden_import in FORBIDDEN_DESKTOP_IMPORTS:
        assert forbidden_import not in imports
        assert not any(
            imported.startswith(f"{forbidden_import}.") for imported in imports
        )


@pytest.mark.architecture
def test_initial_migration_contains_only_technical_schema() -> None:
    migration = Path("alembic/versions/0001_initial_revision.py").read_text(
        encoding="utf-8"
    )

    assert "application_metadata" in migration
    for forbidden_term in FORBIDDEN_MIGRATION_TERMS:
        assert forbidden_term not in migration


@pytest.mark.architecture
def test_technical_audit_migration_contains_only_technical_schema() -> None:
    migration = Path("alembic/versions/0002_technical_audit.py").read_text(
        encoding="utf-8"
    )

    assert "technical_audit_records" in migration
    for forbidden_term in FORBIDDEN_MIGRATION_TERMS:
        assert forbidden_term not in migration
