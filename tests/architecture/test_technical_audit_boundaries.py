import ast
from pathlib import Path

import pytest

FORBIDDEN_LAYER_IMPORTS = {
    "friday.infrastructure.audit",
}

FORBIDDEN_AUDIT_IMPORTS = {
    "friday.ai",
    "friday.desktop",
    "friday.domain",
    "friday.integrations",
}

FORBIDDEN_AUDIT_TERMS = {
    "account",
    "asset",
    "budget",
    "cash_flow",
    "goal",
    "portfolio",
    "transaction",
    "wealth",
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
def test_business_layers_do_not_depend_on_technical_audit() -> None:
    root = Path(__file__).resolve().parents[2] / "friday"
    layer_roots = [
        root / "application",
        root / "desktop",
        root / "domain",
        root / "shared",
    ]

    imports: set[str] = set()
    for layer_root in layer_roots:
        for path in layer_root.rglob("*.py"):
            imports.update(_imports_from_file(path))

    for forbidden_import in FORBIDDEN_LAYER_IMPORTS:
        assert forbidden_import not in imports
        assert not any(
            imported.startswith(f"{forbidden_import}.") for imported in imports
        )


@pytest.mark.architecture
def test_technical_audit_does_not_depend_on_forbidden_layers() -> None:
    audit_root = (
        Path(__file__).resolve().parents[2] / "friday" / "infrastructure" / "audit"
    )

    imports: set[str] = set()
    for path in audit_root.rglob("*.py"):
        imports.update(_imports_from_file(path))

    for forbidden_import in FORBIDDEN_AUDIT_IMPORTS:
        assert forbidden_import not in imports
        assert not any(
            imported.startswith(f"{forbidden_import}.") for imported in imports
        )


@pytest.mark.architecture
def test_technical_audit_does_not_define_business_audit_terms() -> None:
    audit_root = (
        Path(__file__).resolve().parents[2] / "friday" / "infrastructure" / "audit"
    )
    source = "\n".join(
        path.read_text(encoding="utf-8").lower() for path in audit_root.rglob("*.py")
    )

    for forbidden_term in FORBIDDEN_AUDIT_TERMS:
        assert forbidden_term not in source
