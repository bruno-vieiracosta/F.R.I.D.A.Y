from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from friday.bootstrap.config import ApplicationSettings
from friday.shared.errors import ConfigurationError, InfrastructureError


@dataclass(frozen=True, slots=True)
class BackupConfiguration:
    directory: Path
    max_backups: int
    retention_days: int
    extension: str
    manifest_name: str
    database_name: str
    metadata_directory_name: str
    logs_directory_name: str


def resolve_backup_configuration(settings: ApplicationSettings) -> BackupConfiguration:
    configuration = BackupConfiguration(
        directory=settings.directories.backups.expanduser(),
        max_backups=10,
        retention_days=30,
        extension=".friday-backup",
        manifest_name="manifest.json",
        database_name="database.sqlite",
        metadata_directory_name="metadata",
        logs_directory_name="logs",
    )
    validate_backup_configuration(configuration)
    return configuration


def validate_backup_configuration(configuration: BackupConfiguration) -> None:
    if configuration.max_backups < 1:
        raise ConfigurationError(
            "Backup retention is invalid.",
            technical_message="Backup max_backups must be greater than zero.",
        )

    if configuration.retention_days < 1:
        raise ConfigurationError(
            "Backup retention is invalid.",
            technical_message="Backup retention_days must be greater than zero.",
        )

    if not configuration.extension.startswith("."):
        raise ConfigurationError(
            "Backup extension is invalid.",
            technical_message="Backup extension must start with a dot.",
        )

    for value, field_name in {
        configuration.manifest_name: "manifest_name",
        configuration.database_name: "database_name",
        configuration.metadata_directory_name: "metadata_directory_name",
        configuration.logs_directory_name: "logs_directory_name",
    }.items():
        _validate_path_name(value, field_name)


def ensure_backup_directory(configuration: BackupConfiguration) -> None:
    try:
        configuration.directory.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise InfrastructureError(
            "Backup directory could not be created.",
            technical_message="Backup directory creation failed.",
            cause=error,
            metadata={"path": str(configuration.directory)},
        ) from error


def _validate_path_name(value: str, field_name: str) -> None:
    if not value.strip():
        raise ConfigurationError(
            "Backup path name is invalid.",
            technical_message="Backup path names must not be empty.",
            metadata={"field": field_name},
        )

    if Path(value).name != value:
        raise ConfigurationError(
            "Backup path name is invalid.",
            technical_message="Backup path names must not include directories.",
            metadata={"field": field_name},
        )
