from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType

from friday.infrastructure.audit.serializers import JsonValue, normalize_metadata
from friday.shared.clock import Clock, normalize_to_utc, serialize_datetime
from friday.shared.errors import ValidationError
from friday.shared.identifiers import EntityId, IdGenerator


class AuditCategory(StrEnum):
    ADMINISTRATION = "administration"
    EVENT_BUS = "event_bus"
    INFRASTRUCTURE = "infrastructure"
    MIGRATION = "migration"
    PERSISTENCE = "persistence"


class AuditLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class TechnicalAuditRecord:
    record_id: EntityId
    occurred_at: datetime
    category: AuditCategory
    origin: str
    operation: str
    level: AuditLevel
    message: str
    metadata: Mapping[str, JsonValue]

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
    ) -> TechnicalAuditRecord:
        return cls(
            record_id=id_generator.new_id(EntityId),
            occurred_at=clock.now(),
            category=category,
            origin=origin,
            operation=operation,
            level=level,
            message=message,
            metadata=normalize_metadata(metadata),
        )

    def __post_init__(self) -> None:
        if not isinstance(self.record_id, EntityId):
            raise ValidationError(
                "Audit record identifier is invalid.",
                technical_message="TechnicalAuditRecord requires an EntityId.",
            )

        object.__setattr__(self, "occurred_at", normalize_to_utc(self.occurred_at))
        object.__setattr__(self, "origin", _required_text(self.origin, "origin"))
        object.__setattr__(
            self,
            "operation",
            _required_text(self.operation, "operation"),
        )
        object.__setattr__(self, "message", _required_text(self.message, "message"))
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(normalize_metadata(self.metadata)),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": str(self.record_id),
            "occurred_at": serialize_datetime(self.occurred_at),
            "category": self.category.value,
            "origin": self.origin,
            "operation": self.operation,
            "level": self.level.value,
            "message": self.message,
            "metadata": dict(self.metadata),
        }

    def __str__(self) -> str:
        return (
            f"{self.category.value}.{self.origin}.{self.operation}[{self.level.value}]"
        )


def _required_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(
            "Audit record text is invalid.",
            technical_message=f"Audit field {field_name} must not be empty.",
            metadata={"field": field_name},
        )
    return cleaned
