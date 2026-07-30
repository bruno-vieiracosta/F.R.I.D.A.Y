import tomllib
from pathlib import Path

import pytest


def _pyproject() -> dict[str, object]:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    return tomllib.loads(pyproject_path.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_runtime_dependencies_remain_empty() -> None:
    project = _pyproject()["project"]

    assert isinstance(project, dict)
    assert project["dependencies"] == []


@pytest.mark.unit
def test_quality_tools_are_declared_as_development_dependencies() -> None:
    project = _pyproject()["project"]

    assert isinstance(project, dict)
    optional_dependencies = project["optional-dependencies"]
    assert isinstance(optional_dependencies, dict)

    dev_dependencies = optional_dependencies["dev"]
    assert isinstance(dev_dependencies, list)

    assert any(dependency.startswith("ruff") for dependency in dev_dependencies)
    assert any(dependency.startswith("mypy") for dependency in dev_dependencies)
    assert any(dependency.startswith("pytest") for dependency in dev_dependencies)
    assert any(dependency.startswith("pytest-cov") for dependency in dev_dependencies)


@pytest.mark.unit
def test_ruff_and_mypy_share_the_project_python_target() -> None:
    pyproject = _pyproject()
    ruff = pyproject["tool"]["ruff"]
    mypy = pyproject["tool"]["mypy"]

    assert isinstance(ruff, dict)
    assert isinstance(mypy, dict)
    assert ruff["target-version"] == "py311"
    assert mypy["python_version"] == "3.11"


@pytest.mark.unit
def test_ruff_controls_import_sorting_and_unused_imports() -> None:
    ruff_lint = _pyproject()["tool"]["ruff"]["lint"]

    assert isinstance(ruff_lint, dict)
    selected_rules = ruff_lint["select"]
    assert isinstance(selected_rules, list)

    assert "I" in selected_rules
    assert "F" in selected_rules
