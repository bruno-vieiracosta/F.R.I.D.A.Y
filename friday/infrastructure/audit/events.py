from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import ClassVar

from friday.application.events import ApplicationEvent
from friday.infrastructure.audit.models import AuditCategory, AuditLevel
from friday.infrastructure.audit.serializers import JsonValue, normalize_metadata
from friday.infrastructure.audit.service import TechnicalAuditService
from friday.shared.clock import Clock
from friday.shared.identifiers import IdGenerator


@dataclass(frozen=True, slots=True)
class TechnicalAuditEvent(ApplicationEvent):
    category: AuditCategory
    origin: str
    operation: str
    level: AuditLevel
    message: str
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    event_name: ClassVar[str] = "infrastructure.audit.technical_event"

    @classmethod
    def create(
        cls,
        *,
        clock: Clock,
        id_generator: IdGenerator,
        category: AuditCategory,
        origin: str,
        operation: str,
        level: AuditLevel,
        message: str,
        metadata: Mapping[str, object] | None = None,
    ) -> TechnicalAuditEvent:
        event_metadata = cls.new_metadata(clock, id_generator)
        return cls(
            event_id=event_metadata.event_id,
            occurred_at=event_metadata.occurred_at,
            category=category,
            origin=origin,
            operation=operation,
            level=level,
            message=message,
            metadata=normalize_metadata(metadata),
        )

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(normalize_metadata(self.metadata)),
        )

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = super().to_dict()
        data.update(
            {
                "category": self.category.value,
                "origin": self.origin,
                "operation": self.operation,
                "level": self.level.value,
                "message": self.message,
                "metadata": dict(self.metadata),
            }
        )
        return data


@dataclass(frozen=True, slots=True)
class TechnicalAuditEventHandler:
    service: TechnicalAuditService

    def handle(self, event: TechnicalAuditEvent) -> None:
        self.service.try_record(
            category=event.category,
            origin=event.origin,
            operation=event.operation,
            level=event.level,
            message=event.message,
            metadata=event.metadata,
        )
