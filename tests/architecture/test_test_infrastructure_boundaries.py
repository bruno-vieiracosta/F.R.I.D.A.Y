import ast
from pathlib import Path

import pytest

FORBIDDEN_TEST_INFRASTRUCTURE_IMPORTS = (
    "friday.ai",
    "friday.application",
    "friday.bootstrap",
    "friday.desktop",
    "friday.domain",
    "friday.infrastructure",
    "friday.integrations",
    "friday.security",
    "friday.shared",
)


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
def test_shared_test_infrastructure_does_not_import_application_layers() -> None:
    tests_root = Path(__file__).resolve().parents[1]
    infrastructure_paths = [
        tests_root / "conftest.py",
        *tests_root.joinpath("fixtures").rglob("*.py"),
    ]

    imports: set[str] = set()
    for path in infrastructure_paths:
        imports.update(_imports_from_file(path))

    for forbidden_import in FORBIDDEN_TEST_INFRASTRUCTURE_IMPORTS:
        assert forbidden_import not in imports
        assert not any(
            imported.startswith(f"{forbidden_import}.") for imported in imports
        )
