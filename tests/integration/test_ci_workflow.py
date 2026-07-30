from pathlib import Path

import pytest

WORKFLOW_PATH = Path(".github/workflows/ci.yml")
EXPECTED_COMMANDS = (
    'python -m pip install -e ".[dev]"',
    "python -m ruff check .",
    "python -m ruff format --check .",
    "python -m mypy friday",
    "python -m pytest",
    "python -m pytest --cov=friday",
    "python -m build",
)


@pytest.mark.integration
def test_ci_workflow_exists() -> None:
    assert WORKFLOW_PATH.is_file()


@pytest.mark.integration
def test_ci_workflow_runs_on_push_and_pull_request() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "  push:" in workflow
    assert "  pull_request:" in workflow


@pytest.mark.integration
def test_ci_workflow_uses_python_311() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert 'python-version: "3.11"' in workflow


@pytest.mark.integration
def test_ci_workflow_preserves_validation_command_order() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    command_positions = [workflow.index(command) for command in EXPECTED_COMMANDS]

    assert command_positions == sorted(command_positions)


@pytest.mark.integration
def test_ci_workflow_does_not_publish_packages() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8").lower()

    assert "pypi" not in workflow
    assert "twine" not in workflow
