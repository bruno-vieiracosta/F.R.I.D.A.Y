import ast
from pathlib import Path

import pytest

FORBIDDEN_IMPORTS = {
    "friday.bootstrap": {
        "friday.domain",
    },
    "friday.domain": {
        "friday.ai",
        "friday.application",
        "friday.desktop",
        "friday.infrastructure",
        "friday.integrations",
    },
    "friday.application": {
        "friday.ai",
        "friday.desktop",
        "friday.infrastructure",
        "friday.integrations",
        "friday.security",
    },
    "friday.shared": {
        "friday.domain",
        "friday.infrastructure",
    },
}
FORBIDDEN_MODULE_IMPORTS = {
    "friday.shared.types": {
        "friday.bootstrap",
        "friday.domain",
        "friday.infrastructure",
    },
    "friday.shared.finance": {
        "friday.bootstrap",
        "friday.domain",
        "friday.infrastructure",
    },
    "friday.shared.identifiers": {
        "friday.bootstrap",
        "friday.domain",
        "friday.infrastructure",
    },
    "friday.shared.clock": {
        "friday.bootstrap",
        "friday.domain",
        "friday.infrastructure",
    },
    "friday.bootstrap.container": {
        "friday.domain",
    },
    "friday.application.events": {
        "friday.bootstrap",
        "friday.infrastructure",
    },
    "friday.application.event_bus": {
        "friday.bootstrap",
        "friday.desktop",
        "friday.infrastructure",
    },
    "friday.application.persistence.repository": {
        "friday.bootstrap",
        "friday.desktop",
        "friday.infrastructure",
    },
    "friday.application.persistence.unit_of_work": {
        "friday.bootstrap",
        "friday.desktop",
        "friday.infrastructure",
    },
    "friday.application.persistence.transaction": {
        "friday.bootstrap",
        "friday.desktop",
        "friday.infrastructure",
    },
    "friday.application.persistence.specifications": {
        "friday.bootstrap",
        "friday.desktop",
        "friday.infrastructure",
    },
    "friday.application.persistence.pagination": {
        "friday.bootstrap",
        "friday.desktop",
        "friday.infrastructure",
    },
    "friday.infrastructure.persistence.configuration": {
        "friday.domain",
    },
    "friday.infrastructure.persistence.database": {
        "friday.domain",
    },
    "friday.infrastructure.persistence.engine": {
        "friday.domain",
    },
    "friday.infrastructure.persistence.session": {
        "friday.domain",
    },
    "friday.infrastructure.persistence.unit_of_work": {
        "friday.domain",
    },
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


def _package_imports(package: str) -> set[str]:
    root = Path(__file__).resolve().parents[2].joinpath(*package.split("."))
    imports: set[str] = set()

    for path in root.rglob("*.py"):
        imports.update(_imports_from_file(path))

    return imports


def _module_imports(module: str) -> set[str]:
    path = Path(__file__).resolve().parents[2].joinpath(*module.split("."))
    return _imports_from_file(path.with_suffix(".py"))


@pytest.mark.architecture
def test_architecture_boundaries_do_not_import_forbidden_layers() -> None:
    for package, forbidden_imports in FORBIDDEN_IMPORTS.items():
        imports = _package_imports(package)

        for forbidden_import in forbidden_imports:
            assert forbidden_import not in imports
            assert not any(
                imported.startswith(f"{forbidden_import}.") for imported in imports
            )


@pytest.mark.architecture
def test_module_boundaries_do_not_import_forbidden_layers() -> None:
    for module, forbidden_imports in FORBIDDEN_MODULE_IMPORTS.items():
        imports = _module_imports(module)

        for forbidden_import in forbidden_imports:
            assert forbidden_import not in imports
            assert not any(
                imported.startswith(f"{forbidden_import}.") for imported in imports
            )
