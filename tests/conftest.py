import shutil
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest


@pytest.fixture
def temporary_directory() -> Iterator[Path]:
    root = Path(".test_tmp")
    path = root / uuid4().hex
    path.mkdir(parents=True)

    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
        if root.exists() and not any(root.iterdir()):
            root.rmdir()


@pytest.fixture
def fixed_clock() -> Callable[[], datetime]:
    fixed_instant = datetime(2026, 1, 1, tzinfo=UTC)

    def now() -> datetime:
        return fixed_instant

    return now


@pytest.fixture
def temporary_paths(temporary_directory: Path) -> dict[str, Path]:
    paths = {
        "input": temporary_directory / "input",
        "output": temporary_directory / "output",
        "cache": temporary_directory / "cache",
    }

    for path in paths.values():
        path.mkdir()

    return paths


@pytest.fixture
def read_text_file() -> Callable[[Path], str]:
    def read(path: Path) -> str:
        return path.read_text(encoding="utf-8")

    return read
