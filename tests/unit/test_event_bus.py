import logging
from dataclasses import FrozenInstanceError, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar
from uuid import UUID

import pytest

from friday.application.event_bus import EventBus
from friday.application.events import ApplicationEvent, EventMetadata
from friday.bootstrap.config import ApplicationSettings, load_settings
from friday.bootstrap.container import ServiceContainer, build_container
from friday.bootstrap.logging import configure_logging, log_file_path
from friday.shared.clock import Clock, FixedClock
from friday.shared.errors import ApplicationError, ConfigurationError, ValidationError
from friday.shared.identifiers import EventId, IdGenerator, TypedId


@dataclass(frozen=True, slots=True)
class SampleEvent(ApplicationEvent):
    label: str

    event_name: ClassVar[str] = "sample.event"

    @classmethod
    def create(
        cls,
        clock: Clock,
        id_generator: IdGenerator,
        *,
        label: str = "sample",
    ) -> "SampleEvent":
        metadata = cls.new_metadata(clock, id_generator)
        return cls(
            event_id=metadata.event_id,
            occurred_at=metadata.occurred_at,
            label=label,
        )

    def to_dict(self) -> dict[str, str]:
        return {**super().to_dict(), "label": self.label}


@dataclass(frozen=True, slots=True)
class OtherEvent(ApplicationEvent):
    event_name: ClassVar[str] = "other.event"


class DeterministicIdGenerator:
    def __init__(self, value: UUID) -> None:
        self.value = value

    def new_id(self, id_type: type[TypedId]) -> TypedId:
        return id_type.from_uuid(self.value)


class RecordingHandler:
    def __init__(self, calls: list[str], name: str) -> None:
        self.calls = calls
        self.name = name

    def handle(self, event: SampleEvent) -> None:
        self.calls.append(f"{self.name}:{event.label}")


class FailingHandler:
    def handle(self, _event: SampleEvent) -> None:
        raise RuntimeError("handler failed token=secret")


class OfficialErrorHandler:
    def handle(self, _event: SampleEvent) -> None:
        raise ValidationError(
            "Event data is invalid.",
            technical_message="Handler rejected event payload.",
        )


def _settings(temporary_directory: Path) -> ApplicationSettings:
    return load_settings(
        {
            "FRIDAY_ENVIRONMENT": "testing",
            "FRIDAY_LOGS_DIR": str(temporary_directory / "logs"),
            "FRIDAY_LOG_MAX_BYTES": "4096",
            "FRIDAY_LOG_BACKUP_COUNT": "1",
        }
    )


def _event(label: str = "sample") -> SampleEvent:
    clock = FixedClock(datetime(2026, 1, 1, 12, 0, tzinfo=UTC))
    generator = DeterministicIdGenerator(UUID("00000000-0000-4000-8000-000000000012"))
    return SampleEvent.create(clock, generator, label=label)


def _bus() -> EventBus:
    return EventBus(logger=logging.getLogger("friday.tests.events"))


@pytest.fixture(autouse=True)
def reset_friday_logger() -> None:
    logger = logging.getLogger("friday")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


@pytest.mark.unit
def test_event_metadata_uses_clock_and_event_id_generator() -> None:
    clock = FixedClock(datetime(2026, 1, 1, 12, 0, tzinfo=UTC))
    generator = DeterministicIdGenerator(UUID("00000000-0000-4000-8000-000000000012"))

    metadata = EventMetadata.new(clock, generator)

    assert metadata.event_id == EventId.from_string(
        "00000000-0000-4000-8000-000000000012"
    )
    assert metadata.occurred_at == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.mark.unit
def test_event_is_immutable_and_serializable() -> None:
    event = _event("created")

    assert event.name == "sample.event"
    assert event.occurred_at.tzinfo is UTC
    assert str(event) == ("sample.event(00000000-0000-4000-8000-000000000012)")
    assert event.to_dict() == {
        "event_id": "00000000-0000-4000-8000-000000000012",
        "event_name": "sample.event",
        "occurred_at": "2026-01-01T12:00:00+00:00",
        "label": "created",
    }

    with pytest.raises(FrozenInstanceError):
        event.label = "updated"


@pytest.mark.unit
def test_event_rejects_invalid_identifier() -> None:
    with pytest.raises(ValidationError, match="Event identifier is invalid"):
        SampleEvent(
            event_id="not-an-event-id",
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
            label="invalid",
        )


@pytest.mark.unit
def test_event_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError, match="Datetime must include timezone"):
        SampleEvent(
            event_id=EventId.new(),
            occurred_at=datetime(2026, 1, 1),
            label="invalid",
        )


@pytest.mark.unit
def test_event_equality_uses_value() -> None:
    first = _event("same")
    second = _event("same")

    assert first == second


@pytest.mark.unit
def test_register_single_handler_and_publish() -> None:
    calls: list[str] = []
    handler = RecordingHandler(calls, "handler")
    bus = _bus()

    bus.subscribe(SampleEvent, handler)
    bus.publish(_event("published"))

    assert calls == ["handler:published"]
    assert bus.handlers_for(SampleEvent) == (handler,)


@pytest.mark.unit
def test_register_multiple_handlers_preserves_order() -> None:
    calls: list[str] = []
    first = RecordingHandler(calls, "first")
    second = RecordingHandler(calls, "second")
    bus = _bus()

    bus.subscribe(SampleEvent, first)
    bus.subscribe(SampleEvent, second)
    bus.publish(_event("ordered"))

    assert calls == ["first:ordered", "second:ordered"]


@pytest.mark.unit
def test_unsubscribe_removes_handler() -> None:
    calls: list[str] = []
    handler = RecordingHandler(calls, "handler")
    bus = _bus()
    bus.subscribe(SampleEvent, handler)

    bus.unsubscribe(SampleEvent, handler)
    bus.publish(_event("ignored"))

    assert calls == []
    assert bus.handlers_for(SampleEvent) == ()


@pytest.mark.unit
def test_unsubscribe_unknown_handler_raises_official_error() -> None:
    with pytest.raises(ConfigurationError, match="Event handler is not registered"):
        _bus().unsubscribe(SampleEvent, RecordingHandler([], "missing"))


@pytest.mark.unit
def test_duplicate_handler_registration_is_rejected() -> None:
    handler = RecordingHandler([], "handler")
    bus = _bus()
    bus.subscribe(SampleEvent, handler)

    with pytest.raises(ConfigurationError, match="Event handler is already registered"):
        bus.subscribe(SampleEvent, handler)


@pytest.mark.unit
def test_publish_without_handlers_is_accepted() -> None:
    _bus().publish(_event("no-handlers"))


@pytest.mark.unit
def test_publish_different_events_uses_matching_handlers() -> None:
    calls: list[str] = []
    handler = RecordingHandler(calls, "sample")
    bus = _bus()
    bus.subscribe(SampleEvent, handler)

    bus.publish(
        OtherEvent(
            event_id=EventId.new(),
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    bus.publish(_event("matched"))

    assert calls == ["sample:matched"]


@pytest.mark.unit
def test_invalid_event_handler_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="Event handler is invalid"):
        _bus().subscribe(SampleEvent, object())


@pytest.mark.unit
def test_handler_failure_is_logged_and_raised(
    temporary_directory: Path,
) -> None:
    settings = _settings(temporary_directory)
    factory = configure_logging(settings)
    calls: list[str] = []
    bus = EventBus(logger=factory.get_logger("events"))
    bus.subscribe(SampleEvent, FailingHandler())
    bus.subscribe(SampleEvent, RecordingHandler(calls, "after-failure"))

    with pytest.raises(ApplicationError, match="Event publication failed") as error:
        bus.publish(_event("failure"))

    assert isinstance(error.value.cause, ApplicationError)
    assert calls == ["after-failure:failure"]
    contents = log_file_path(settings).read_text(encoding="utf-8")
    assert "Event handler failed" in contents
    assert "secret" not in contents
    assert "token=***" in contents


@pytest.mark.unit
def test_official_handler_error_is_wrapped() -> None:
    bus = _bus()
    bus.subscribe(SampleEvent, OfficialErrorHandler())

    with pytest.raises(ApplicationError) as error:
        bus.publish(_event("official-error"))

    assert isinstance(error.value.cause, ApplicationError)
    assert isinstance(error.value.cause.cause, ValidationError)


@pytest.mark.unit
def test_event_bus_remains_usable_after_failure() -> None:
    calls: list[str] = []
    failing = FailingHandler()
    handler = RecordingHandler(calls, "healthy")
    bus = _bus()
    bus.subscribe(SampleEvent, failing)

    with pytest.raises(ApplicationError):
        bus.publish(_event("first"))

    bus.unsubscribe(SampleEvent, failing)
    bus.subscribe(SampleEvent, handler)
    bus.publish(_event("second"))

    assert calls == ["healthy:second"]


@pytest.mark.unit
def test_event_bus_is_registered_as_container_singleton(
    temporary_directory: Path,
) -> None:
    container = build_container(_settings(temporary_directory))

    first = container.resolve(EventBus)
    second = container.resolve(EventBus)

    assert isinstance(first, EventBus)
    assert first is second


@pytest.mark.unit
def test_event_bus_resolved_from_container_can_publish(
    temporary_directory: Path,
) -> None:
    container = build_container(_settings(temporary_directory))
    bus = container.resolve(EventBus)
    calls: list[str] = []
    bus.subscribe(SampleEvent, RecordingHandler(calls, "container"))

    bus.publish(_event("resolved"))

    assert calls == ["container:resolved"]


@pytest.mark.unit
def test_event_bus_can_be_replaced_in_container_tests(
    temporary_directory: Path,
) -> None:
    container = build_container(_settings(temporary_directory))
    replacement = _bus()

    container.register_instance(EventBus, replacement, replace=True)

    assert container.resolve(EventBus) is replacement


@pytest.mark.unit
def test_event_bus_instances_are_isolated_between_containers(
    temporary_directory: Path,
) -> None:
    first_container = build_container(_settings(temporary_directory / "first"))
    second_container = build_container(_settings(temporary_directory / "second"))

    assert first_container.resolve(EventBus) is not second_container.resolve(EventBus)
    assert isinstance(first_container, ServiceContainer)
