import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import text

from friday.application.event_bus import EventBus
from friday.bootstrap.config import ApplicationSettings, load_settings
from friday.bootstrap.container import ServiceContainer, build_container
from friday.bootstrap.logging import configure_logging
from friday.infrastructure.audit import TechnicalAuditRepository
from friday.infrastructure.backup import (
    BackupCreatedEvent,
    BackupDeletedEvent,
    BackupRestoredEvent,
    BackupService,
    BackupValidatedEvent,
    read_manifest,
)
from friday.infrastructure.persistence import DatabaseInfrastructure, upgrade_database
from friday.shared.clock import Clock, FixedClock
from friday.shared.identifiers import IdGenerator, TypedId


class DeterministicIdGenerator:
    def __init__(self, values: list[UUID]) -> None:
        self.values = values

    def new_id(self, id_type: type[TypedId]) -> TypedId:
        return id_type.from_uuid(self.values.pop(0))


class RecordingBackupHandler:
    def __init__(self) -> None:
        self.events: list[str] = []

    def handle(
        self,
        event: BackupCreatedEvent
        | BackupValidatedEvent
        | BackupRestoredEvent
        | BackupDeletedEvent,
    ) -> None:
        self.events.append(event.name)


def _settings(temporary_directory: Path) -> ApplicationSettings:
    return load_settings(
        {
            "FRIDAY_ENVIRONMENT": "testing",
            "FRIDAY_DATABASE_PATH": str(temporary_directory / "data" / "friday.db"),
            "FRIDAY_BACKUPS_DIR": str(temporary_directory / "backups"),
            "FRIDAY_LOGS_DIR": str(temporary_directory / "logs"),
            "FRIDAY_LOG_MAX_BYTES": "4096",
            "FRIDAY_LOG_BACKUP_COUNT": "1",
        }
    )


def _container(
    temporary_directory: Path,
) -> tuple[ApplicationSettings, ServiceContainer]:
    settings = _settings(temporary_directory)
    container = build_container(settings)
    container.register_instance(
        Clock,
        FixedClock(datetime(2026, 1, 1, 12, 0, tzinfo=UTC)),
        replace=True,
    )
    container.register_instance(
        IdGenerator,
        DeterministicIdGenerator(
            [UUID(f"00000000-0000-4000-8000-{index:012d}") for index in range(201, 225)]
        ),
        replace=True,
    )
    return settings, container


@pytest.fixture(autouse=True)
def reset_friday_logger() -> None:
    logger = logging.getLogger("friday")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


@pytest.mark.integration
def test_backup_flow_uses_container_audit_event_bus_and_persistence(
    temporary_directory: Path,
) -> None:
    settings, container = _container(temporary_directory)
    logger = configure_logging(settings).get_logger("migrations")
    upgrade_database(settings, logger)
    database = container.resolve(DatabaseInfrastructure)
    event_bus = container.resolve(EventBus)
    handler = RecordingBackupHandler()
    event_bus.subscribe(BackupCreatedEvent, handler)
    event_bus.subscribe(BackupValidatedEvent, handler)
    event_bus.subscribe(BackupRestoredEvent, handler)
    event_bus.subscribe(BackupDeletedEvent, handler)

    with database.engine.begin() as connection:
        connection.execute(
            text(
                "insert into application_metadata "
                "(key, value, created_at, updated_at) "
                "values ('backup-test', 'original', "
                "'2026-01-01T12:00:00+00:00', '2026-01-01T12:00:00+00:00')"
            )
        )

    service = container.resolve(BackupService)
    manifest = service.create_backup()
    backup_path = service.configuration.directory / (
        "backup-20260101-120000-00000000.friday-backup"
    )
    assert (backup_path / service.configuration.database_name).is_file()

    assert read_manifest(backup_path, service.configuration) == manifest
    assert service.list_backups() == (manifest,)
    assert service.validate_backup(backup_path) == manifest
    audit_before_restore = [
        record.operation
        for record in container.resolve(TechnicalAuditRepository).list_records()
    ]
    assert "created" in audit_before_restore
    assert "validated" in audit_before_restore

    database.engine.dispose()
    database.configuration.path.write_bytes(b"corrupted")

    assert service.restore_backup(backup_path) == manifest
    with database.engine.connect() as connection:
        restored_value = connection.execute(
            text("select value from application_metadata where key = 'backup-test'")
        ).scalar_one()
    assert restored_value == "original"
    assert service.remove_backup(backup_path) == manifest
    assert not backup_path.exists()

    audit_records = container.resolve(TechnicalAuditRepository).list_records()
    audit_operations = [record.operation for record in audit_records]
    assert "restored" in audit_operations
    assert "deleted" in audit_operations
    assert handler.events == [
        "infrastructure.backup.created",
        "infrastructure.backup.validated",
        "infrastructure.backup.restored",
        "infrastructure.backup.deleted",
    ]

    database.engine.dispose()
