from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from friday.shared.errors import ValidationError
from friday.shared.types import (
    ConfidenceLevel,
    DateRange,
    HasIdentifier,
    OperationStatus,
    PagedResult,
    Result,
    SharedTypeError,
    SupportsText,
    SupportsToDict,
    calculate_total_pages,
)


@pytest.mark.unit
def test_success_result_exposes_value() -> None:
    result: Result[int, str] = Result.success(10)

    assert result.is_success is True
    assert result.is_failure is False
    assert result.value == 10
    assert result.value_or(0) == 10


@pytest.mark.unit
def test_failure_result_exposes_error() -> None:
    result: Result[int, str] = Result.failure("failed")

    assert result.is_success is False
    assert result.is_failure is True
    assert result.error == "failed"
    assert result.error_or("default") == "failed"


@pytest.mark.unit
def test_result_blocks_unsafe_access() -> None:
    success: Result[int, str] = Result.success(1)
    failure: Result[int, str] = Result.failure("failed")

    with pytest.raises(SharedTypeError):
        _ = success.error

    with pytest.raises(SharedTypeError):
        _ = failure.value


@pytest.mark.unit
def test_result_map_transforms_success_only() -> None:
    success: Result[int, str] = Result.success(2)
    failure: Result[int, str] = Result.failure("failed")

    assert success.map(lambda value: value * 3).value == 6
    assert failure.map(lambda value: value * 3).error == "failed"


@pytest.mark.unit
def test_result_serializes_error_hierarchy_safely() -> None:
    error = ValidationError("Invalid input.", technical_message="token=secret")
    result: Result[int, ValidationError] = Result.failure(error)

    assert result.to_dict() == {
        "success": False,
        "error": {
            "code": "FRIDAY-VALIDATION-001",
            "category": "VALIDATION",
            "message": "Invalid input.",
        },
    }


@pytest.mark.unit
def test_paged_result_exposes_pagination_metadata() -> None:
    page = PagedResult(
        items=("a", "b"), page=2, page_size=2, total_items=5, total_pages=3
    )

    assert page.has_previous_page is True
    assert page.has_next_page is True
    assert page.to_dict() == {
        "items": ["a", "b"],
        "page": 2,
        "page_size": 2,
        "total_items": 5,
        "total_pages": 3,
        "has_previous_page": True,
        "has_next_page": True,
    }


@pytest.mark.unit
def test_paged_result_is_immutable() -> None:
    page = PagedResult(items=(), page=1, page_size=10, total_items=0, total_pages=0)

    with pytest.raises(FrozenInstanceError):
        page.page = 2


@pytest.mark.unit
def test_paged_result_validates_values() -> None:
    with pytest.raises(SharedTypeError, match="Page must"):
        PagedResult(items=(), page=0, page_size=10, total_items=0, total_pages=0)

    with pytest.raises(SharedTypeError, match="Total pages is inconsistent"):
        PagedResult(items=(), page=1, page_size=10, total_items=11, total_pages=1)

    with pytest.raises(SharedTypeError, match="Items must not exceed"):
        PagedResult(items=(1, 2, 3), page=1, page_size=2, total_items=3, total_pages=2)


@pytest.mark.unit
def test_calculate_total_pages() -> None:
    assert calculate_total_pages(total_items=0, page_size=10) == 0
    assert calculate_total_pages(total_items=1, page_size=10) == 1
    assert calculate_total_pages(total_items=11, page_size=10) == 2


@pytest.mark.unit
def test_date_range_validates_chronology() -> None:
    valid = DateRange(start=date(2026, 1, 1), end=date(2026, 1, 31))

    assert valid.contains(date(2026, 1, 15)) is True
    assert valid.contains(date(2026, 2, 1)) is False

    with pytest.raises(SharedTypeError, match="start must not be after end"):
        DateRange(start=date(2026, 2, 1), end=date(2026, 1, 1))


@pytest.mark.unit
def test_date_range_serializes_to_simple_dict() -> None:
    date_range = DateRange(start=date(2026, 1, 1), end=date(2026, 1, 31))

    assert date_range.to_dict() == {
        "start": "2026-01-01",
        "end": "2026-01-31",
    }


@pytest.mark.unit
def test_shared_enums_are_stable() -> None:
    assert [level.value for level in ConfidenceLevel] == ["LOW", "MEDIUM", "HIGH"]
    assert [status.value for status in OperationStatus] == [
        "PENDING",
        "RUNNING",
        "COMPLETED",
        "FAILED",
        "CANCELLED",
    ]


class SerializableSample:
    def to_dict(self) -> dict[str, object]:
        return {"value": "sample"}


class IdentifiedSample:
    @property
    def identifier(self) -> str:
        return "sample-id"


@pytest.mark.unit
def test_shared_protocols_are_structural() -> None:
    serializable = SerializableSample()
    identified = IdentifiedSample()

    assert isinstance(serializable, SupportsToDict)
    assert isinstance(serializable, SupportsText)
    assert identified.identifier == "sample-id"
    assert _identifier(identified) == "sample-id"


def _identifier(value: HasIdentifier) -> str:
    return value.identifier
