from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from friday.application.events import ApplicationEvent
from friday.infrastructure.backup.manifest import BackupManifest
from friday.shared.clock import Clock
from friday.shared.identifiers import EntityId, IdGenerator


@dataclass(frozen=True, slots=True)
class BackupEvent(ApplicationEvent):
    backup_id: EntityId
    backup_path: str

    event_name: ClassVar[str] = "infrastructure.backup.event"

    @classmethod
    def create(
        cls,
        *,
        clock: Clock,
        id_generator: IdGenerator,
        manifest: BackupManifest,
        backup_path: Path,
    ) -> BackupEvent:
        metadata = cls.new_metadata(clock, id_generator)
        return cls(
            event_id=metadata.event_id,
            occurred_at=metadata.occurred_at,
            backup_id=manifest.backup_id,
            backup_path=str(backup_path),
        )

    def to_dict(self) -> dict[str, object]:
        data = super().to_dict()
        data.update(
            {
                "backup_id": str(self.backup_id),
                "backup_path": self.backup_path,
            }
        )
        return data


@dataclass(frozen=True, slots=True)
class BackupCreatedEvent(BackupEvent):
    event_name: ClassVar[str] = "infrastructure.backup.created"


@dataclass(frozen=True, slots=True)
class BackupValidatedEvent(BackupEvent):
    event_name: ClassVar[str] = "infrastructure.backup.validated"


@dataclass(frozen=True, slots=True)
class BackupRestoredEvent(BackupEvent):
    event_name: ClassVar[str] = "infrastructure.backup.restored"


@dataclass(frozen=True, slots=True)
class BackupDeletedEvent(BackupEvent):
    event_name: ClassVar[str] = "infrastructure.backup.deleted"
