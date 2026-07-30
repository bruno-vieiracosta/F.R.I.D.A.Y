from datetime import UTC, datetime, timedelta

import pytest

from friday.shared.clock import (
    Clock,
    FixedClock,
    SystemClock,
    convert_utc_to_timezone,
    ensure_timezone_aware,
    normalize_to_utc,
    serialize_datetime,
    timezone_from_name,
)
from friday.shared.errors import ValidationError


def _read_clock(clock: Clock) -> datetime:
    return clock.now()


@pytest.mark.unit
def test_system_clock_returns_timezone_aware_utc_datetime() -> None:
    clock = SystemClock()

    first = clock.now()
    second = clock.now()

    assert first.tzinfo is UTC
    assert second.tzinfo is UTC
    assert second >= first


@pytest.mark.unit
def test_fixed_clock_is_deterministic() -> None:
    instant = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    clock = FixedClock(instant)

    assert clock.now() == instant
    assert clock.now() == clock.now()


@pytest.mark.unit
def test_fixed_clock_normalizes_initial_instant_to_utc() -> None:
    sao_paulo = timezone_from_name("America/Sao_Paulo")
    instant = datetime(2026, 1, 1, 9, 0, tzinfo=sao_paulo)

    clock = FixedClock(instant)

    assert clock.now() == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.mark.unit
def test_fixed_clock_can_be_set_explicitly() -> None:
    clock = FixedClock(datetime(2026, 1, 1, tzinfo=UTC))

    clock.set(datetime(2026, 2, 1, tzinfo=UTC))

    assert clock.now() == datetime(2026, 2, 1, tzinfo=UTC)


@pytest.mark.unit
def test_fixed_clock_can_advance_without_sleep() -> None:
    clock = FixedClock(datetime(2026, 1, 1, tzinfo=UTC))

    clock.advance(timedelta(hours=3, minutes=30))

    assert clock.now() == datetime(2026, 1, 1, 3, 30, tzinfo=UTC)


@pytest.mark.unit
def test_fixed_clock_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError, match="Datetime must include timezone"):
        FixedClock(datetime(2026, 1, 1))


@pytest.mark.unit
def test_clock_protocol_allows_substitution() -> None:
    instant = datetime(2026, 1, 1, tzinfo=UTC)
    clock: Clock = FixedClock(instant)

    assert _read_clock(clock) == instant


@pytest.mark.unit
def test_timezone_helpers_reject_naive_datetime() -> None:
    with pytest.raises(ValidationError, match="Datetime must include timezone"):
        ensure_timezone_aware(datetime(2026, 1, 1))


@pytest.mark.unit
def test_normalize_to_utc_preserves_instant() -> None:
    sao_paulo = timezone_from_name("America/Sao_Paulo")
    value = datetime(2026, 1, 1, 9, 0, tzinfo=sao_paulo)

    assert normalize_to_utc(value) == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.mark.unit
def test_convert_utc_to_timezone_is_explicit() -> None:
    value = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    converted = convert_utc_to_timezone(value, "America/Sao_Paulo")

    assert converted.isoformat() == "2026-01-01T09:00:00-03:00"
    assert converted.astimezone(UTC) == value


@pytest.mark.unit
def test_unknown_timezone_raises_official_error() -> None:
    with pytest.raises(ValidationError, match="Timezone is unknown"):
        timezone_from_name("Unknown/Nowhere")


@pytest.mark.unit
def test_empty_timezone_name_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Timezone name must not be empty"):
        timezone_from_name(" ")


@pytest.mark.unit
def test_datetime_serialization_uses_iso_8601() -> None:
    value = datetime(2026, 1, 1, 12, 30, tzinfo=UTC)

    assert serialize_datetime(value) == "2026-01-01T12:30:00+00:00"
