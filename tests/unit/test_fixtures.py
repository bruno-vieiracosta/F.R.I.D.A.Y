from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest


@pytest.mark.unit
def test_temporary_directory_fixture_provides_isolated_path(
    temporary_directory: Path,
) -> None:
    assert temporary_directory.is_dir()


@pytest.mark.unit
def test_temporary_paths_fixture_creates_common_paths(
    temporary_paths: dict[str, Path],
) -> None:
    assert set(temporary_paths) == {"input", "output", "cache"}
    assert all(path.is_dir() for path in temporary_paths.values())


@pytest.mark.unit
def test_fixed_clock_fixture_is_deterministic(
    fixed_clock: Callable[[], datetime],
) -> None:
    assert fixed_clock() == datetime(2026, 1, 1, tzinfo=UTC)
    assert fixed_clock() == fixed_clock()


@pytest.mark.unit
def test_read_text_file_fixture_reads_utf8_text(
    temporary_directory: Path,
    read_text_file: Callable[[Path], str],
) -> None:
    path = temporary_directory / "sample.txt"
    path.write_text("friday", encoding="utf-8")

    assert read_text_file(path) == "friday"
