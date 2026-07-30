from pathlib import Path

import pytest


@pytest.mark.integration
def test_pytest_discovers_nested_test_suite(pytestconfig: pytest.Config) -> None:
    testpaths = pytestconfig.getini("testpaths")

    assert testpaths == ["tests"]
    assert Path("tests/unit").is_dir()
    assert Path("tests/integration").is_dir()
    assert Path("tests/architecture").is_dir()


@pytest.mark.integration
def test_official_markers_are_registered(pytestconfig: pytest.Config) -> None:
    registered_markers = {
        marker.split(":", maxsplit=1)[0] for marker in pytestconfig.getini("markers")
    }

    assert {"unit", "integration", "architecture", "slow"}.issubset(registered_markers)


@pytest.mark.integration
def test_coverage_configuration_is_available() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "[tool.coverage.run]" in pyproject
    assert 'source = ["friday"]' in pyproject
    assert "[tool.coverage.report]" in pyproject
