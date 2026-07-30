from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, tzinfo
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from friday.shared.errors import ValidationError


class Clock(Protocol):
    def now(self) -> datetime:
        pass


@dataclass(frozen=True, slots=True)
class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass(slots=True)
class FixedClock:
    _instant: datetime

    def __post_init__(self) -> None:
        self._instant = normalize_to_utc(self._instant)

    def now(self) -> datetime:
        return self._instant

    def set(self, instant: datetime) -> None:
        self._instant = normalize_to_utc(instant)

    def advance(self, delta: timedelta) -> None:
        self._instant = normalize_to_utc(self._instant + delta)


def ensure_timezone_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError(
            "Datetime must include timezone information.",
            technical_message="Naive datetimes are not accepted.",
        )
    return value


def normalize_to_utc(value: datetime) -> datetime:
    return ensure_timezone_aware(value).astimezone(UTC)


def convert_utc_to_timezone(value: datetime, timezone_name: str) -> datetime:
    instant = normalize_to_utc(value)
    timezone = timezone_from_name(timezone_name)
    return instant.astimezone(timezone)


def timezone_from_name(timezone_name: str) -> tzinfo:
    name = timezone_name.strip()
    if not name:
        raise ValidationError("Timezone name must not be empty.")

    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as error:
        raise ValidationError(
            "Timezone is unknown.",
            technical_message="ZoneInfo could not resolve timezone.",
            cause=error,
            metadata={"timezone": timezone_name},
        ) from error


def serialize_datetime(value: datetime) -> str:
    return ensure_timezone_aware(value).isoformat()
