from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Generic, Protocol, TypeVar, cast, runtime_checkable

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")


class SharedTypeError(ValueError):
    pass


class ConfidenceLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class OperationStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@runtime_checkable
class SupportsToDict(Protocol):
    def to_dict(self) -> object:
        pass


@runtime_checkable
class SupportsPublicDict(Protocol):
    def to_public_dict(self) -> Mapping[str, object]:
        pass


@runtime_checkable
class SupportsText(Protocol):
    def __str__(self) -> str:
        pass


@runtime_checkable
class HasIdentifier(Protocol):
    @property
    def identifier(self) -> str:
        pass


@dataclass(frozen=True, slots=True)
class Result(Generic[T, E]):
    _value: T | None
    _error: E | None
    _is_success: bool

    @classmethod
    def success(cls, value: T) -> Result[T, E]:
        return cls(_value=value, _error=None, _is_success=True)

    @classmethod
    def failure(cls, error: E) -> Result[T, E]:
        return cls(_value=None, _error=error, _is_success=False)

    @property
    def is_success(self) -> bool:
        return self._is_success

    @property
    def is_failure(self) -> bool:
        return not self._is_success

    @property
    def value(self) -> T:
        if self.is_failure:
            raise SharedTypeError("Cannot access value from a failed Result.")
        return cast(T, self._value)

    @property
    def error(self) -> E:
        if self.is_success:
            raise SharedTypeError("Cannot access error from a successful Result.")
        return cast(E, self._error)

    def value_or(self, default: T) -> T:
        if self.is_success:
            return self.value
        return default

    def error_or(self, default: E) -> E:
        if self.is_failure:
            return self.error
        return default

    def map(self, mapper: Callable[[T], U]) -> Result[U, E]:
        if self.is_failure:
            return Result.failure(self.error)
        return Result.success(mapper(self.value))

    def to_dict(self) -> dict[str, object]:
        if self.is_success:
            return {"success": True, "value": _serialize(self.value)}
        return {"success": False, "error": _serialize(self.error)}


@dataclass(frozen=True, slots=True)
class PagedResult(Generic[T]):
    items: tuple[T, ...]
    page: int
    page_size: int
    total_items: int
    total_pages: int

    def __post_init__(self) -> None:
        if self.page < 1:
            raise SharedTypeError("Page must be greater than or equal to 1.")
        if self.page_size < 1:
            raise SharedTypeError("Page size must be greater than or equal to 1.")
        if self.total_items < 0:
            raise SharedTypeError("Total items must be greater than or equal to 0.")
        if self.total_pages < 0:
            raise SharedTypeError("Total pages must be greater than or equal to 0.")

        expected_total_pages = _calculate_total_pages(
            total_items=self.total_items,
            page_size=self.page_size,
        )
        if self.total_pages != expected_total_pages:
            raise SharedTypeError("Total pages is inconsistent with total items.")
        if self.total_pages > 0 and self.page > self.total_pages:
            raise SharedTypeError("Page must not be greater than total pages.")
        if len(self.items) > self.page_size:
            raise SharedTypeError("Items must not exceed page size.")

    @property
    def has_previous_page(self) -> bool:
        return self.page > 1

    @property
    def has_next_page(self) -> bool:
        return self.total_pages > 0 and self.page < self.total_pages

    def to_dict(self) -> dict[str, object]:
        return {
            "items": [_serialize(item) for item in self.items],
            "page": self.page,
            "page_size": self.page_size,
            "total_items": self.total_items,
            "total_pages": self.total_pages,
            "has_previous_page": self.has_previous_page,
            "has_next_page": self.has_next_page,
        }


@dataclass(frozen=True, slots=True)
class DateRange:
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise SharedTypeError("Date range start must not be after end.")

    def contains(self, value: date) -> bool:
        return self.start <= value <= self.end

    def to_dict(self) -> dict[str, str]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
        }


def calculate_total_pages(*, total_items: int, page_size: int) -> int:
    if page_size < 1:
        raise SharedTypeError("Page size must be greater than or equal to 1.")
    if total_items < 0:
        raise SharedTypeError("Total items must be greater than or equal to 0.")
    return _calculate_total_pages(total_items=total_items, page_size=page_size)


def _calculate_total_pages(*, total_items: int, page_size: int) -> int:
    if total_items == 0:
        return 0
    return (total_items + page_size - 1) // page_size


def _serialize(value: object) -> object:
    if isinstance(value, SupportsPublicDict):
        return dict(value.to_public_dict())
    if isinstance(value, SupportsToDict):
        serialized = value.to_dict()
        if isinstance(serialized, Mapping):
            return dict(serialized)
        return serialized
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, tuple | list | set):
        return [_serialize(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _serialize(item) for key, item in value.items()}
    return value
