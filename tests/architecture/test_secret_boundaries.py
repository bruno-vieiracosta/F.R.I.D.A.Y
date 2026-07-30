import ast
from pathlib import Path

import pytest

FORBIDDEN_SECRET_IMPORTS = {
    "alembic",
    "friday.ai",
    "friday.application",
    "friday.desktop",
    "friday.domain",
    "friday.infrastructure",
    "friday.integrations",
    "sqlalchemy",
}

FORBIDDEN_CONSUMER_IMPORTS = {
    "friday.security.secrets.environment",
    "friday.security.secrets.file_provider",
    "friday.security.secrets.resolver",
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
def test_secret_management_stays_inside_security_layer() -> None:
    root = Path(__file__).resolve().parents[2] / "friday"
    secret_root = root / "security" / "secrets"

    assert secret_root.is_dir()
    assert all(path.is_file() for path in secret_root.glob("*.py"))


@pytest.mark.architecture
def test_secret_management_does_not_depend_on_forbidden_layers() -> None:
    secret_root = (
        Path(__file__).resolve().parents[2] / "friday" / "security" / "secrets"
    )

    imports: set[str] = set()
    for path in secret_root.rglob("*.py"):
        imports.update(_imports_from_file(path))

    for forbidden_import in FORBIDDEN_SECRET_IMPORTS:
        assert forbidden_import not in imports
        assert not any(
            imported.startswith(f"{forbidden_import}.") for imported in imports
        )


@pytest.mark.architecture
def test_business_layers_do_not_depend_on_concrete_secret_providers() -> None:
    root = Path(__file__).resolve().parents[2] / "friday"
    layer_roots = [
        root / "application",
        root / "desktop",
        root / "domain",
        root / "integrations",
        root / "shared",
    ]

    imports: set[str] = set()
    for layer_root in layer_roots:
        for path in layer_root.rglob("*.py"):
            imports.update(_imports_from_file(path))

    for forbidden_import in FORBIDDEN_CONSUMER_IMPORTS:
        assert forbidden_import not in imports
        assert not any(
            imported.startswith(f"{forbidden_import}.") for imported in imports
        )


@pytest.mark.architecture
def test_secret_management_does_not_add_database_migrations() -> None:
    versions_root = Path(__file__).resolve().parents[2] / "alembic" / "versions"

    revisions = {path.name for path in versions_root.glob("*.py")}

    assert revisions == {
        "0001_initial_revision.py",
        "0002_technical_audit.py",
    }
