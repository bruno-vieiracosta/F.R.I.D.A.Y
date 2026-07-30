from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Protocol, TypeVar

from friday.shared.clock import Clock, normalize_to_utc, serialize_datetime
from friday.shared.errors import ValidationError
from friday.shared.identifiers import EventId, IdGenerator

EventT_contra = TypeVar(
    "EventT_contra",
    bound="ApplicationEvent",
    contravariant=True,
)


class EventHandler(Protocol[EventT_contra]):
    def handle(self, event: EventT_contra) -> None:
        pass


@dataclass(frozen=True, slots=True)
class EventMetadata:
    event_id: EventId
    occurred_at: datetime

    @classmethod
    def new(cls, clock: Clock, id_generator: IdGenerator) -> EventMetadata:
        return cls(
            event_id=id_generator.new_id(EventId),
            occurred_at=clock.now(),
        )

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, EventId):
            raise ValidationError(
                "Event identifier is invalid.",
                technical_message="Event metadata requires an EventId value.",
            )
        object.__setattr__(self, "occurred_at", normalize_to_utc(self.occurred_at))


@dataclass(frozen=True, slots=True)
class ApplicationEvent:
    event_id: EventId
    occurred_at: datetime

    event_name: ClassVar[str] = "application.event"

    @classmethod
    def new_metadata(cls, clock: Clock, id_generator: IdGenerator) -> EventMetadata:
        return EventMetadata.new(clock, id_generator)

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, EventId):
            raise ValidationError(
                "Event identifier is invalid.",
                technical_message="ApplicationEvent requires an EventId value.",
            )
        object.__setattr__(self, "occurred_at", normalize_to_utc(self.occurred_at))

    @property
    def name(self) -> str:
        return self.event_name

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": str(self.event_id),
            "event_name": self.name,
            "occurred_at": serialize_datetime(self.occurred_at),
        }

    def __str__(self) -> str:
        return f"{self.name}({self.event_id})"
