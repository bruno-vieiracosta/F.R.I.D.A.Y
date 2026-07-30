import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from friday.bootstrap.config import ApplicationSettings, load_settings
from friday.bootstrap.container import ServiceContainer, build_container
from friday.bootstrap.logging import configure_logging
from friday.infrastructure.audit import TechnicalAuditRepository
from friday.infrastructure.backup import BackupService
from friday.infrastructure.persistence import DatabaseInfrastructure, upgrade_database
from friday.security.hardening import (
    HardenedPathPurpose,
    PathTraversalError,
    SecureFilesystem,
    SecurityPolicy,
)
from friday.security.secrets import FileSecretProvider, SecretIdentifier
from friday.shared.clock import Clock, FixedClock
from friday.shared.identifiers import IdGenerator, TypedId


class DeterministicIdGenerator:
    def __init__(self, values: list[UUID]) -> None:
        self.values = values

    def new_id(self, id_type: type[TypedId]) -> TypedId:
        return id_type.from_uuid(self.values.pop(0))


def _settings(temporary_directory: Path) -> ApplicationSettings:
    return load_settings(
        {
            "FRIDAY_ENVIRONMENT": "testing",
            "FRIDAY_DATABASE_PATH": str(temporary_directory / "data" / "friday.db"),
            "FRIDAY_BACKUPS_DIR": str(temporary_directory / "backups"),
            "FRIDAY_SECRETS_FILE": str(temporary_directory / "config" / "secrets.json"),
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
            [UUID(f"00000000-0000-4000-8000-{index:012d}") for index in range(401, 440)]
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
def test_hardening_uses_container_configuration_logging_and_audit(
    temporary_directory: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings, container = _container(temporary_directory)
    upgrade_database(settings, configure_logging(settings).get_logger("migrations"))

    try:
        filesystem = container.resolve(SecureFilesystem)
        assert isinstance(container.resolve(SecurityPolicy), SecurityPolicy)

        filesystem.ensure_directory(
            settings.directories.data,
            Path("technical"),
            purpose=HardenedPathPurpose.TECHNICAL,
        )
        filesystem.atomic_write_text(
            settings.directories.data,
            Path("technical") / "metadata.json",
            '{"status":"ok"}',
            purpose=HardenedPathPurpose.TECHNICAL,
        )

        with (
            caplog.at_level(logging.WARNING),
            pytest.raises(PathTraversalError),
        ):
            filesystem.atomic_write_text(
                settings.directories.data,
                Path("..") / "outside.txt",
                "sensitive-content",
                purpose=HardenedPathPurpose.TECHNICAL,
            )

        audit_records = container.resolve(TechnicalAuditRepository).list_records()
        operations = [record.operation for record in audit_records]
        assert "directory_created" in operations
        assert "atomic_file_written" in operations
        assert "operation_rejected" in operations
        assert "sensitive-content" not in caplog.text
        audit_payload = str([record.to_dict() for record in audit_records])
        assert "sensitive-content" not in audit_payload
    finally:
        container.resolve(DatabaseInfrastructure).engine.dispose()


@pytest.mark.integration
def test_backup_and_secret_management_use_secure_filesystem(
    temporary_directory: Path,
) -> None:
    settings, container = _container(temporary_directory)
    upgrade_database(settings, configure_logging(settings).get_logger("migrations"))

    try:
        settings.secrets.file_path.parent.mkdir(parents=True)
        settings.secrets.file_path.write_text(
            '{"secrets":{"FRIDAY_SECRET_API_KEY":"secret-from-file"}}',
            encoding="utf-8",
        )

        secret_provider = container.resolve(FileSecretProvider)
        secret = secret_provider.get_secret(SecretIdentifier("FRIDAY_SECRET_API_KEY"))
        backup_service = container.resolve(BackupService)
        manifest = backup_service.create_backup()

        assert secret.reveal() == "secret-from-file"
        assert backup_service.secure_filesystem is container.resolve(SecureFilesystem)
        assert manifest.application_version == settings.version
    finally:
        container.resolve(DatabaseInfrastructure).engine.dispose()
