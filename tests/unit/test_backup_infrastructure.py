import logging
import shutil
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from friday.application.event_bus import EventBus
from friday.bootstrap.config import ApplicationSettings, load_settings
from friday.infrastructure.backup import (
    BackupConfiguration,
    BackupCreatedEvent,
    BackupDeletedEvent,
    BackupEvent,
    BackupFile,
    BackupManifest,
    BackupRestoredEvent,
    BackupService,
    BackupValidatedEvent,
    build_file_manifest,
    content_hash,
    ensure_backup_directory,
    file_sha256,
    read_manifest,
    resolve_backup_configuration,
    validate_backup,
    validate_backup_configuration,
)
from friday.infrastructure.persistence import (
    DatabaseConfiguration,
    DatabaseInfrastructure,
    SqlAlchemySessionFactory,
)
from friday.shared.clock import FixedClock
from friday.shared.errors import (
    ConfigurationError,
    InfrastructureError,
    ValidationError,
)
from friday.shared.identifiers import EntityId, TypedId


class DeterministicIdGenerator:
    def __init__(self, values: list[UUID]) -> None:
        self.values = values

    def new_id(self, id_type: type[TypedId]) -> TypedId:
        return id_type.from_uuid(self.values.pop(0))


class RecordingAuditService:
    def __init__(self) -> None:
        self.operations: list[str] = []

    def try_record(self, **metadata: object) -> bool:
        self.operations.append(str(metadata["operation"]))
        return True


class RecordingHandler:
    def __init__(self) -> None:
        self.events: list[str] = []

    def handle(self, event: BackupCreatedEvent) -> None:
        self.events.append(event.name)


class FailingHandler:
    def handle(self, event: BackupEvent) -> None:
        raise InfrastructureError(
            "Event handler failed.",
            technical_message=f"Handler failed for {event.name}.",
        )


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


def _manifest() -> BackupManifest:
    files = (
        BackupFile(
            path="database.sqlite",
            size_bytes=5,
            sha256="0" * 64,
        ),
    )
    return BackupManifest(
        backup_id=EntityId.from_string("00000000-0000-4000-8000-000000000117"),
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        application_version="0.1.0",
        schema_version="base",
        files=files,
        total_size_bytes=5,
        content_sha256=content_hash(files),
    )


def _configuration(temporary_directory: Path) -> BackupConfiguration:
    return BackupConfiguration(
        directory=temporary_directory / "backups",
        max_backups=10,
        retention_days=30,
        extension=".friday-backup",
        manifest_name="manifest.json",
        database_name="database.sqlite",
        metadata_directory_name="metadata",
        logs_directory_name="logs",
    )


def _database(temporary_directory: Path) -> DatabaseInfrastructure:
    path = temporary_directory / "data" / "friday.db"
    path.parent.mkdir(parents=True)
    engine = create_engine(f"sqlite+pysqlite:///{path.as_posix()}", poolclass=NullPool)
    with engine.begin() as connection:
        connection.execute(text("create table alembic_version (version_num text)"))
        connection.execute(
            text("insert into alembic_version values ('0002_technical_audit')")
        )
    return DatabaseInfrastructure(
        configuration=DatabaseConfiguration(
            path=path,
            url=f"sqlite+pysqlite:///{path.as_posix()}",
        ),
        engine=engine,
        session_factory=SqlAlchemySessionFactory.from_engine(engine),
    )


def _service(temporary_directory: Path) -> tuple[BackupService, RecordingAuditService]:
    settings = _settings(temporary_directory)
    configuration = _configuration(temporary_directory)
    database = _database(temporary_directory)
    audit = RecordingAuditService()
    event_bus = EventBus(logger=logging.getLogger("friday.tests.backup"))
    return (
        BackupService(
            settings=settings,
            configuration=configuration,
            database=database,
            clock=FixedClock(datetime(2026, 1, 1, 12, 0, tzinfo=UTC)),
            id_generator=DeterministicIdGenerator(
                [
                    UUID("00000000-0000-4000-8000-000000000117"),
                    UUID("00000000-0000-4000-8000-000000000118"),
                    UUID("00000000-0000-4000-8000-000000000119"),
                    UUID("00000000-0000-4000-8000-000000000120"),
                    UUID("00000000-0000-4000-8000-000000000121"),
                    UUID("00000000-0000-4000-8000-000000000122"),
                ]
            ),
            logger=logging.getLogger("friday.tests.backup"),
            audit_service=audit,
            event_bus=event_bus,
        ),
        audit,
    )


@pytest.mark.unit
def test_backup_configuration_uses_application_settings(
    temporary_directory: Path,
) -> None:
    settings = _settings(temporary_directory)

    configuration = resolve_backup_configuration(settings)

    assert configuration.directory == temporary_directory / "backups"
    assert configuration.max_backups == 10
    assert configuration.retention_days == 30
    assert configuration.extension == ".friday-backup"


@pytest.mark.unit
def test_backup_configuration_validates_limits(temporary_directory: Path) -> None:
    configuration = _configuration(temporary_directory)

    with pytest.raises(ConfigurationError):
        validate_backup_configuration(
            BackupConfiguration(
                directory=configuration.directory,
                max_backups=0,
                retention_days=configuration.retention_days,
                extension=configuration.extension,
                manifest_name=configuration.manifest_name,
                database_name=configuration.database_name,
                metadata_directory_name=configuration.metadata_directory_name,
                logs_directory_name=configuration.logs_directory_name,
            )
        )

    with pytest.raises(ConfigurationError):
        validate_backup_configuration(
            BackupConfiguration(
                directory=configuration.directory,
                max_backups=configuration.max_backups,
                retention_days=0,
                extension="backup",
                manifest_name="nested/manifest.json",
                database_name=configuration.database_name,
                metadata_directory_name=configuration.metadata_directory_name,
                logs_directory_name=configuration.logs_directory_name,
            )
        )


@pytest.mark.unit
def test_backup_configuration_validates_file_names(temporary_directory: Path) -> None:
    configuration = _configuration(temporary_directory)

    with pytest.raises(ConfigurationError, match="Backup extension is invalid"):
        validate_backup_configuration(
            BackupConfiguration(
                directory=configuration.directory,
                max_backups=configuration.max_backups,
                retention_days=configuration.retention_days,
                extension="backup",
                manifest_name=configuration.manifest_name,
                database_name=configuration.database_name,
                metadata_directory_name=configuration.metadata_directory_name,
                logs_directory_name=configuration.logs_directory_name,
            )
        )

    with pytest.raises(ConfigurationError, match="Backup path name is invalid"):
        validate_backup_configuration(
            BackupConfiguration(
                directory=configuration.directory,
                max_backups=configuration.max_backups,
                retention_days=configuration.retention_days,
                extension=configuration.extension,
                manifest_name=" ",
                database_name=configuration.database_name,
                metadata_directory_name=configuration.metadata_directory_name,
                logs_directory_name=configuration.logs_directory_name,
            )
        )

    with pytest.raises(ConfigurationError, match="Backup path name is invalid"):
        validate_backup_configuration(
            BackupConfiguration(
                directory=configuration.directory,
                max_backups=configuration.max_backups,
                retention_days=configuration.retention_days,
                extension=configuration.extension,
                manifest_name="nested/manifest.json",
                database_name=configuration.database_name,
                metadata_directory_name=configuration.metadata_directory_name,
                logs_directory_name=configuration.logs_directory_name,
            )
        )


@pytest.mark.unit
def test_backup_directory_is_created(temporary_directory: Path) -> None:
    configuration = _configuration(temporary_directory)

    ensure_backup_directory(configuration)

    assert configuration.directory.is_dir()


@pytest.mark.unit
def test_backup_manifest_is_immutable_and_serializable() -> None:
    manifest = _manifest()

    decoded = BackupManifest.from_json(manifest.to_json())

    assert decoded == manifest
    assert decoded.to_dict()["backup_id"] == "00000000-0000-4000-8000-000000000117"
    with pytest.raises(FrozenInstanceError):
        manifest.schema_version = "changed"


@pytest.mark.unit
def test_backup_manifest_rejects_invalid_values() -> None:
    with pytest.raises(ValidationError):
        BackupFile(path="../database.sqlite", size_bytes=1, sha256="0" * 64)

    with pytest.raises(ValidationError):
        BackupFile(path="database.sqlite", size_bytes=-1, sha256="0" * 64)

    with pytest.raises(ValidationError):
        BackupManifest.from_json("{")

    with pytest.raises(ValidationError):
        BackupManifest.from_json("[]")


@pytest.mark.unit
def test_backup_manifest_rejects_invalid_fields() -> None:
    manifest_data = _manifest().to_dict()

    invalid_backup_id = dict(manifest_data)
    invalid_backup_id["backup_id"] = 123
    with pytest.raises(ValidationError, match="Backup manifest is invalid"):
        BackupManifest.from_dict(invalid_backup_id)

    invalid_files = dict(manifest_data)
    invalid_files["files"] = {}
    with pytest.raises(ValidationError, match="Backup manifest is invalid"):
        BackupManifest.from_dict(invalid_files)

    invalid_file_entry = dict(manifest_data)
    invalid_file_entry["files"] = ["database.sqlite"]
    with pytest.raises(ValidationError, match="Backup manifest is invalid"):
        BackupManifest.from_dict(invalid_file_entry)

    invalid_total = dict(manifest_data)
    invalid_total["total_size_bytes"] = "5"
    with pytest.raises(ValidationError, match="Backup manifest is invalid"):
        BackupManifest.from_dict(invalid_total)


@pytest.mark.unit
def test_backup_manifest_rejects_invalid_identity_version_and_hash() -> None:
    files = (
        BackupFile(
            path="database.sqlite",
            size_bytes=5,
            sha256="0" * 64,
        ),
    )

    with pytest.raises(ValidationError, match="Backup identifier is invalid"):
        BackupManifest(
            backup_id="not-an-entity-id",
            created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            application_version="0.1.0",
            schema_version="base",
            files=files,
            total_size_bytes=5,
            content_sha256=content_hash(files),
        )

    with pytest.raises(ValidationError, match="Backup application version is invalid"):
        BackupManifest(
            backup_id=EntityId.from_string("00000000-0000-4000-8000-000000000117"),
            created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            application_version=" ",
            schema_version="base",
            files=files,
            total_size_bytes=5,
            content_sha256=content_hash(files),
        )

    with pytest.raises(ValidationError, match="Backup schema version is invalid"):
        BackupManifest(
            backup_id=EntityId.from_string("00000000-0000-4000-8000-000000000117"),
            created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            application_version="0.1.0",
            schema_version=" ",
            files=files,
            total_size_bytes=5,
            content_sha256=content_hash(files),
        )

    with pytest.raises(ValidationError, match="Backup total size is invalid"):
        BackupManifest(
            backup_id=EntityId.from_string("00000000-0000-4000-8000-000000000117"),
            created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            application_version="0.1.0",
            schema_version="base",
            files=files,
            total_size_bytes=99,
            content_sha256=content_hash(files),
        )

    with pytest.raises(ValidationError, match="Backup hash is invalid"):
        BackupManifest(
            backup_id=EntityId.from_string("00000000-0000-4000-8000-000000000117"),
            created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            application_version="0.1.0",
            schema_version="base",
            files=files,
            total_size_bytes=5,
            content_sha256="x" * 64,
        )


@pytest.mark.unit
def test_backup_file_hash_and_manifest_validation(temporary_directory: Path) -> None:
    configuration = _configuration(temporary_directory)
    backup_path = (
        configuration.directory / "backup-20260101-120000-00000000.friday-backup"
    )
    backup_path.mkdir(parents=True)
    (backup_path / "database.sqlite").write_bytes(b"database")
    files = (build_file_manifest(backup_path, "database.sqlite"),)
    manifest = BackupManifest(
        backup_id=EntityId.from_string("00000000-0000-4000-8000-000000000117"),
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        application_version="0.1.0",
        schema_version="base",
        files=files,
        total_size_bytes=sum(file.size_bytes for file in files),
        content_sha256=content_hash(files),
    )
    (backup_path / configuration.manifest_name).write_text(
        manifest.to_json(),
        encoding="utf-8",
    )

    assert file_sha256(backup_path / "database.sqlite") == files[0].sha256
    assert read_manifest(backup_path, configuration) == manifest
    assert (
        validate_backup(backup_path, configuration, application_version="0.1.0")
        == manifest
    )


@pytest.mark.unit
def test_backup_validation_rejects_incomplete_or_incompatible_backup(
    temporary_directory: Path,
) -> None:
    configuration = _configuration(temporary_directory)
    missing = configuration.directory / "missing.friday-backup"

    with pytest.raises(ValidationError, match="Backup path is invalid"):
        validate_backup(missing, configuration, application_version="0.1.0")

    backup_path = configuration.directory / "backup-20260101-120000-1.friday-backup"
    backup_path.mkdir(parents=True)
    (backup_path / configuration.manifest_name).write_text(
        _manifest().to_json(),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="Backup version is incompatible"):
        validate_backup(backup_path, configuration, application_version="9.9.9")

    with pytest.raises(ValidationError, match="Backup structure is incomplete"):
        validate_backup(backup_path, configuration, application_version="0.1.0")


@pytest.mark.unit
def test_backup_validation_rejects_paths_outside_directory_or_files(
    temporary_directory: Path,
) -> None:
    configuration = _configuration(temporary_directory)
    outside = temporary_directory / "outside.friday-backup"
    outside.mkdir()

    with pytest.raises(ValidationError, match="Backup path is invalid"):
        validate_backup(outside, configuration, application_version="0.1.0")

    file_path = configuration.directory / "file.friday-backup"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("not a directory", encoding="utf-8")

    with pytest.raises(ValidationError, match="Backup path is invalid"):
        validate_backup(file_path, configuration, application_version="0.1.0")

    wrong_extension = configuration.directory / "backup"
    wrong_extension.mkdir()

    with pytest.raises(ValidationError, match="Backup path is invalid"):
        validate_backup(wrong_extension, configuration, application_version="0.1.0")


@pytest.mark.unit
def test_backup_validation_rejects_tampered_content(
    temporary_directory: Path,
) -> None:
    configuration = _configuration(temporary_directory)
    backup_path = (
        configuration.directory / "backup-20260101-120000-00000000.friday-backup"
    )
    backup_path.mkdir(parents=True)
    (backup_path / "database.sqlite").write_bytes(b"database")
    files = (build_file_manifest(backup_path, "database.sqlite"),)
    manifest = BackupManifest(
        backup_id=EntityId.from_string("00000000-0000-4000-8000-000000000117"),
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        application_version="0.1.0",
        schema_version="base",
        files=files,
        total_size_bytes=sum(file.size_bytes for file in files),
        content_sha256=content_hash(files),
    )
    (backup_path / configuration.manifest_name).write_text(
        manifest.to_json(),
        encoding="utf-8",
    )
    (backup_path / "database.sqlite").write_bytes(b"tampered")

    with pytest.raises(ValidationError, match="Backup integrity is invalid"):
        validate_backup(backup_path, configuration, application_version="0.1.0")


@pytest.mark.unit
def test_backup_service_creates_lists_validates_restores_and_removes(
    temporary_directory: Path,
) -> None:
    service, audit = _service(temporary_directory)
    handler = RecordingHandler()
    service.event_bus.subscribe(BackupCreatedEvent, handler)

    manifest = service.create_backup()
    backup_path = service.configuration.directory / (
        "backup-20260101-120000-00000000.friday-backup"
    )
    original_database = (backup_path / service.configuration.database_name).read_bytes()

    assert backup_path.is_dir()
    assert (backup_path / service.configuration.manifest_name).is_file()
    assert original_database
    assert service.list_backups() == (manifest,)
    assert service.validate_backup(backup_path) == manifest
    service.database.configuration.path.write_bytes(b"changed")

    restored = service.restore_backup(backup_path)

    assert restored == manifest
    assert service.database.configuration.path.read_bytes() == original_database
    removed = service.remove_backup(backup_path)
    assert removed == manifest
    assert not backup_path.exists()
    assert "created" in audit.operations
    assert "restored" in audit.operations
    assert "deleted" in audit.operations
    assert handler.events == ["infrastructure.backup.created"]


@pytest.mark.unit
def test_backup_events_are_serializable(temporary_directory: Path) -> None:
    service, _audit = _service(temporary_directory)
    manifest = service.create_backup()
    backup_path = service.configuration.directory / (
        "backup-20260101-120000-00000000.friday-backup"
    )

    event = BackupValidatedEvent.create(
        clock=service.clock,
        id_generator=service.id_generator,
        manifest=manifest,
        backup_path=backup_path,
    )

    assert event.name == "infrastructure.backup.validated"
    assert event.to_dict()["backup_id"] == str(manifest.backup_id)
    assert event.to_dict()["backup_path"] == str(backup_path)
    assert BackupRestoredEvent.event_name == "infrastructure.backup.restored"
    assert BackupDeletedEvent.event_name == "infrastructure.backup.deleted"


@pytest.mark.unit
def test_backup_service_keeps_working_when_event_publication_fails(
    temporary_directory: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    service, audit = _service(temporary_directory)
    service.event_bus.subscribe(BackupCreatedEvent, FailingHandler())

    with caplog.at_level(logging.ERROR):
        manifest = service.create_backup()

    assert manifest.backup_id == EntityId.from_string(
        "00000000-0000-4000-8000-000000000117"
    )
    assert "created" in audit.operations
    assert "Backup event publication failed" in caplog.text


@pytest.mark.unit
def test_backup_service_applies_retention(temporary_directory: Path) -> None:
    service, _audit = _service(temporary_directory)
    service = BackupService(
        settings=service.settings,
        configuration=BackupConfiguration(
            directory=service.configuration.directory,
            max_backups=1,
            retention_days=service.configuration.retention_days,
            extension=service.configuration.extension,
            manifest_name=service.configuration.manifest_name,
            database_name=service.configuration.database_name,
            metadata_directory_name=service.configuration.metadata_directory_name,
            logs_directory_name=service.configuration.logs_directory_name,
        ),
        database=service.database,
        clock=service.clock,
        id_generator=service.id_generator,
        logger=service.logger,
        audit_service=service.audit_service,
        event_bus=service.event_bus,
    )

    first = service.create_backup()
    service.clock.advance(timedelta(seconds=1))
    second = service.create_backup()

    backups = service.list_backups()
    first_path = service.configuration.directory / (
        "backup-20260101-120000-00000000.friday-backup"
    )

    assert backups == (second,)
    assert not first_path.exists()
    assert first not in backups


@pytest.mark.unit
def test_backup_service_reports_validation_failures(
    temporary_directory: Path,
) -> None:
    service, audit = _service(temporary_directory)

    with pytest.raises(ValidationError):
        service.validate_backup(
            service.configuration.directory / "missing.friday-backup",
        )

    assert "validate" in audit.operations


@pytest.mark.unit
def test_backup_service_rejects_duplicate_backup_path(
    temporary_directory: Path,
) -> None:
    service, audit = _service(temporary_directory)
    duplicate_path = service.configuration.directory / (
        "backup-20260101-120000-00000000.friday-backup"
    )
    duplicate_path.mkdir(parents=True)

    with pytest.raises(InfrastructureError, match="Backup already exists"):
        service.create_backup()

    assert "create" in audit.operations


@pytest.mark.unit
def test_backup_service_wraps_restore_and_remove_errors(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, audit = _service(temporary_directory)
    manifest = service.create_backup()
    backup_path = service.configuration.directory / (
        "backup-20260101-120000-00000000.friday-backup"
    )

    def fail_copy(source: Path, destination: Path) -> None:
        raise OSError("copy failed")

    monkeypatch.setattr(shutil, "copy2", fail_copy)
    with pytest.raises(InfrastructureError, match="Backup could not be restored"):
        service.restore_backup(backup_path)

    def fail_rmtree(path: Path) -> None:
        raise OSError("remove failed")

    monkeypatch.setattr(shutil, "rmtree", fail_rmtree)
    with pytest.raises(InfrastructureError, match="Backup could not be removed"):
        service.remove_backup(backup_path)

    assert manifest.backup_id == EntityId.from_string(
        "00000000-0000-4000-8000-000000000117"
    )
    assert "restore" in audit.operations
    assert "delete" in audit.operations


@pytest.mark.unit
def test_backup_service_wraps_missing_database(
    temporary_directory: Path,
) -> None:
    service, audit = _service(temporary_directory)
    service.database.engine.dispose()
    service.database.configuration.path.unlink()

    with pytest.raises(InfrastructureError, match="Backup source database is missing"):
        service.create_backup()

    assert "create" in audit.operations


@pytest.mark.unit
def test_backup_service_is_registered_in_container(temporary_directory: Path) -> None:
    from friday.bootstrap.container import build_container

    container = build_container(_settings(temporary_directory))

    assert isinstance(container.resolve(BackupService), BackupService)
    assert isinstance(container.resolve(BackupConfiguration), BackupConfiguration)
