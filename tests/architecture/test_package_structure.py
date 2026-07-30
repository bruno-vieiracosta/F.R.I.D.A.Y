import importlib
from pathlib import Path

import pytest

EXPECTED_PACKAGES = (
    "friday.bootstrap",
    "friday.application",
    "friday.domain",
    "friday.infrastructure",
    "friday.desktop",
    "friday.ai",
    "friday.integrations",
    "friday.security",
    "friday.shared",
)


@pytest.mark.architecture
def test_expected_packages_exist() -> None:
    root = Path(__file__).resolve().parents[2]

    for package in EXPECTED_PACKAGES:
        package_path = root.joinpath(*package.split("."))
        assert package_path.is_dir()
        assert package_path.joinpath("__init__.py").is_file()


@pytest.mark.architecture
def test_expected_packages_are_importable() -> None:
    for package in EXPECTED_PACKAGES:
        assert importlib.import_module(package) is not None
