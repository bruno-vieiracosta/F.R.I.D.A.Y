from __future__ import annotations

import logging as standard_logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from friday.application.event_bus import EventBus
from friday.bootstrap.config import ApplicationSettings
from friday.infrastructure.audit import AuditCategory, AuditLevel, TechnicalAuditService
from friday.infrastructure.backup.configuration import (
    BackupConfiguration,
    ensure_backup_directory,
)
from friday.infrastructure.backup.events import (
    BackupCreatedEvent,
    BackupDeletedEvent,
    BackupEvent,
    BackupRestoredEvent,
    BackupValidatedEvent,
)
from friday.infrastructure.backup.manifest import BackupManifest
from friday.infrastructure.backup.validators import (
    build_file_manifest,
    content_hash,
)
from friday.infrastructure.backup.validators import (
    validate_backup as validate_backup_structure,
)
from friday.infrastructure.persistence import DatabaseInfrastructure
from friday.security.hardening import HardenedPathPurpose, SecureFilesystem
from friday.shared.clock import Clock
from friday.shared.errors import FridayError, InfrastructureError, PersistenceError
from friday.shared.identifiers import EntityId, IdGenerator


@dataclass(frozen=True, slots=True)
class BackupService:
    settings: ApplicationSettings
    configuration: BackupConfiguration
    database: DatabaseInfrastructure
    clock: Clock
    id_generator: IdGenerator
    logger: standard_logging.Logger
    audit_service: TechnicalAuditService
    event_bus: EventBus
    secure_filesystem: SecureFilesystem | None = None

    def create_backup(self) -> BackupManifest:
        try:
            manifest = self._create_backup()
        except FridayError as error:
            self._audit_failure("create", error)
            raise
        except OSError as error:
            wrapped = InfrastructureError(
                "Backup could not be created.",
                technical_message="Local backup creation failed.",
                cause=error,
            )
            self._audit_failure("create", wrapped)
            raise wrapped from error

        backup_path = self._backup_path(manifest)
        self.logger.info("Backup created", extra={"backup": manifest.to_dict()})
        self._audit_success("created", manifest, backup_path)
        self._publish(BackupCreatedEvent, manifest, backup_path)
        self._apply_retention()
        return manifest

    def list_backups(self) -> tuple[BackupManifest, ...]:
        self._ensure_backup_directory()
        manifests = [
            self._validate_backup_structure(path)
            for path in sorted(self.configuration.directory.iterdir())
            if path.is_dir() and path.suffix == self.configuration.extension
        ]
        return tuple(
            sorted(
                manifests,
                key=lambda manifest: (manifest.created_at, str(manifest.backup_id)),
                reverse=True,
            )
        )

    def validate_backup(
        self,
        backup_path: Path,
        *,
        publish_event: bool = True,
    ) -> BackupManifest:
        try:
            manifest = self._validate_backup_structure(backup_path)
        except FridayError as error:
            self.logger.error(
                "Backup validation failed",
                extra={"backup_error": error.to_log_dict()},
                exc_info=(type(error), error, error.__traceback__),
            )
            self._audit_failure("validate", error)
            raise

        self.logger.info("Backup validated", extra={"backup": manifest.to_dict()})
        self._audit_success("validated", manifest, backup_path)
        if publish_event:
            self._publish(BackupValidatedEvent, manifest, backup_path)
        return manifest

    def restore_backup(self, backup_path: Path) -> BackupManifest:
        manifest = self._validate_backup_structure(backup_path)
        source = backup_path / self.configuration.database_name
        destination = self.database.configuration.path
        temporary_destination = destination.with_suffix(f"{destination.suffix}.restore")

        try:
            self._ensure_directory(destination.parent)
            self.database.engine.dispose()
            shutil.copy2(source, temporary_destination)
            temporary_destination.replace(destination)
        except OSError as error:
            wrapped = InfrastructureError(
                "Backup could not be restored.",
                technical_message="Local backup restore failed.",
                cause=error,
                metadata={"backup_path": str(backup_path)},
            )
            self._audit_failure("restore", wrapped)
            raise wrapped from error
        finally:
            if temporary_destination.exists():
                temporary_destination.unlink(missing_ok=True)

        self.logger.info("Backup restored", extra={"backup": manifest.to_dict()})
        self._audit_success("restored", manifest, backup_path)
        self._publish(BackupRestoredEvent, manifest, backup_path)
        return manifest

    def remove_backup(self, backup_path: Path) -> BackupManifest:
        manifest = self._validate_backup_structure(backup_path)
        try:
            if self.secure_filesystem is None:
                shutil.rmtree(backup_path)
            else:
                self.secure_filesystem.remove_tree(
                    self.configuration.directory,
                    Path(backup_path.name),
                    purpose=HardenedPathPurpose.BACKUP,
                )
        except OSError as error:
            wrapped = InfrastructureError(
                "Backup could not be removed.",
                technical_message="Local backup removal failed.",
                cause=error,
                metadata={"backup_path": str(backup_path)},
            )
            self._audit_failure("delete", wrapped)
            raise wrapped from error

        self.logger.info("Backup removed", extra={"backup": manifest.to_dict()})
        self._audit_success("deleted", manifest, backup_path)
        self._publish(BackupDeletedEvent, manifest, backup_path)
        return manifest

    def _create_backup(self) -> BackupManifest:
        self._ensure_backup_directory()
        database_path = self.database.configuration.path
        if not database_path.is_file():
            raise InfrastructureError(
                "Backup source database is missing.",
                technical_message="SQLite database file does not exist.",
                metadata={"path": str(database_path)},
            )

        backup_id = self.id_generator.new_id(EntityId)
        created_at = self.clock.now()
        backup_path = self._backup_path_for(backup_id, created_at)

        if backup_path.exists():
            raise InfrastructureError(
                "Backup already exists.",
                technical_message="Generated backup path already exists.",
                metadata={"path": str(backup_path)},
            )

        try:
            self._ensure_directory(backup_path)
            self._ensure_directory(
                backup_path / self.configuration.metadata_directory_name
            )
            self._ensure_directory(backup_path / self.configuration.logs_directory_name)
            schema_version = self._schema_version()
            self.database.engine.dispose()
            self._copy_database(database_path, backup_path)
            files = (
                build_file_manifest(backup_path, self.configuration.database_name),
            )
            manifest = BackupManifest(
                backup_id=backup_id,
                created_at=created_at,
                application_version=self.settings.version,
                schema_version=schema_version,
                files=files,
                total_size_bytes=sum(file.size_bytes for file in files),
                content_sha256=content_hash(files),
            )
            self._write_manifest(backup_path, manifest)
        except FridayError:
            shutil.rmtree(backup_path, ignore_errors=True)
            raise
        except OSError:
            shutil.rmtree(backup_path, ignore_errors=True)
            raise

        return manifest

    def _schema_version(self) -> str:
        try:
            with self.database.engine.connect() as connection:
                table_names = inspect(connection).get_table_names()
                if "alembic_version" not in table_names:
                    return "base"

                version = connection.execute(
                    text("select version_num from alembic_version")
                ).scalar_one_or_none()
        except SQLAlchemyError as error:
            raise PersistenceError(
                "Backup schema version could not be read.",
                technical_message="Alembic schema version lookup failed.",
                cause=error,
            ) from error

        if version is None:
            return "base"
        return str(version)

    def _validate_backup_structure(self, backup_path: Path) -> BackupManifest:
        return validate_backup_structure(
            backup_path,
            self.configuration,
            application_version=self.settings.version,
        )

    def _write_manifest(self, backup_path: Path, manifest: BackupManifest) -> None:
        manifest_path = backup_path / self.configuration.manifest_name
        if self.secure_filesystem is not None:
            self.secure_filesystem.atomic_write_text(
                backup_path,
                Path(self.configuration.manifest_name),
                f"{manifest.to_json()}\n",
                purpose=HardenedPathPurpose.BACKUP,
            )
            return

        temporary_path = manifest_path.with_suffix(".json.tmp")
        temporary_path.write_text(f"{manifest.to_json()}\n", encoding="utf-8")
        temporary_path.replace(manifest_path)

    def _backup_path(self, manifest: BackupManifest) -> Path:
        return self._backup_path_for(manifest.backup_id, manifest.created_at)

    def _backup_path_for(self, backup_id: EntityId, created_at: datetime) -> Path:
        timestamp = created_at.strftime("%Y%m%d-%H%M%S")
        short_id = str(backup_id).split("-")[0]
        return (
            self.configuration.directory
            / f"backup-{timestamp}-{short_id}{self.configuration.extension}"
        )

    def _apply_retention(self) -> None:
        manifests = self.list_backups()
        for manifest in manifests[self.configuration.max_backups :]:
            backup_path = self._backup_path(manifest)
            try:
                if self.secure_filesystem is None:
                    shutil.rmtree(backup_path)
                else:
                    self.secure_filesystem.remove_tree(
                        self.configuration.directory,
                        Path(backup_path.name),
                        purpose=HardenedPathPurpose.BACKUP,
                    )
            except OSError as error:
                self.logger.error(
                    "Backup retention cleanup failed",
                    exc_info=(type(error), error, error.__traceback__),
                )

    def _audit_success(
        self,
        operation: str,
        manifest: BackupManifest,
        backup_path: Path,
    ) -> None:
        self.audit_service.try_record(
            category=AuditCategory.INFRASTRUCTURE,
            origin="backup",
            operation=operation,
            level=AuditLevel.INFO,
            message=f"Backup {operation}",
            metadata={
                "backup_id": str(manifest.backup_id),
                "backup_path": str(backup_path),
                "schema_version": manifest.schema_version,
            },
        )

    def _audit_failure(self, operation: str, error: FridayError) -> None:
        self.audit_service.try_record(
            category=AuditCategory.INFRASTRUCTURE,
            origin="backup",
            operation=operation,
            level=AuditLevel.ERROR,
            message=f"Backup {operation} failed",
            metadata={
                "error_code": error.code,
                "error_category": error.category.value,
            },
        )

    def _publish(
        self,
        event_type: type[BackupEvent],
        manifest: BackupManifest,
        backup_path: Path,
    ) -> None:
        try:
            self.event_bus.publish(
                event_type.create(
                    clock=self.clock,
                    id_generator=self.id_generator,
                    manifest=manifest,
                    backup_path=backup_path,
                )
            )
        except FridayError as error:
            self.logger.error(
                "Backup event publication failed",
                extra={"backup_error": error.to_log_dict()},
                exc_info=(type(error), error, error.__traceback__),
            )

    def _ensure_backup_directory(self) -> None:
        if self.secure_filesystem is None:
            ensure_backup_directory(self.configuration)
            return

        self.secure_filesystem.ensure_directory(
            self.configuration.directory,
            Path("."),
            purpose=HardenedPathPurpose.BACKUP,
        )

    def _ensure_directory(self, path: Path) -> None:
        if self.secure_filesystem is None:
            path.mkdir(parents=True, exist_ok=True)
            return

        self.secure_filesystem.ensure_directory(
            path,
            Path("."),
            purpose=HardenedPathPurpose.BACKUP,
        )

    def _copy_database(self, database_path: Path, backup_path: Path) -> None:
        if self.secure_filesystem is None:
            shutil.copy2(database_path, backup_path / self.configuration.database_name)
            return

        self.secure_filesystem.copy_file(
            database_path.parent,
            Path(database_path.name),
            backup_path,
            Path(self.configuration.database_name),
            purpose=HardenedPathPurpose.BACKUP,
        )
