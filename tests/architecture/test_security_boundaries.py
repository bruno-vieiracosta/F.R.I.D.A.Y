import ast
from pathlib import Path

import pytest

FORBIDDEN_HARDENING_IMPORTS = {
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
    "friday.security.hardening.filesystem",
    "friday.security.hardening.paths",
    "friday.security.hardening.permissions",
    "friday.security.hardening.policies",
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
def test_hardening_stays_inside_security_layer() -> None:
    hardening_root = Path(__file__).resolve().parents[2] / "friday" / "security"

    assert (hardening_root / "hardening").is_dir()


@pytest.mark.architecture
def test_hardening_does_not_depend_on_forbidden_layers() -> None:
    hardening_root = (
        Path(__file__).resolve().parents[2] / "friday" / "security" / "hardening"
    )

    imports: set[str] = set()
    for path in hardening_root.rglob("*.py"):
        imports.update(_imports_from_file(path))

    for forbidden_import in FORBIDDEN_HARDENING_IMPORTS:
        assert forbidden_import not in imports
        assert not any(
            imported.startswith(f"{forbidden_import}.") for imported in imports
        )


@pytest.mark.architecture
def test_business_layers_do_not_depend_on_concrete_hardening() -> None:
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
def test_hardening_pr_does_not_add_database_migrations() -> None:
    versions_root = Path(__file__).resolve().parents[2] / "alembic" / "versions"

    revisions = {path.name for path in versions_root.glob("*.py")}

    assert revisions == {
        "0001_initial_revision.py",
        "0002_technical_audit.py",
    }
