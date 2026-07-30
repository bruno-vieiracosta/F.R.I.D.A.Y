from __future__ import annotations

import hashlib
from pathlib import Path

from friday.infrastructure.backup.configuration import BackupConfiguration
from friday.infrastructure.backup.manifest import BackupFile, BackupManifest
from friday.shared.errors import InfrastructureError, ValidationError


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise InfrastructureError(
            "Backup file could not be read.",
            technical_message="Backup file hashing failed.",
            cause=error,
            metadata={"path": str(path)},
        ) from error
    return digest.hexdigest()


def build_file_manifest(backup_root: Path, relative_path: str) -> BackupFile:
    path = backup_root / relative_path
    try:
        size = path.stat().st_size
    except OSError as error:
        raise InfrastructureError(
            "Backup file could not be inspected.",
            technical_message="Backup file stat failed.",
            cause=error,
            metadata={"path": str(path)},
        ) from error

    return BackupFile(
        path=relative_path,
        size_bytes=size,
        sha256=file_sha256(path),
    )


def content_hash(files: tuple[BackupFile, ...]) -> str:
    digest = hashlib.sha256()
    for file in sorted(files, key=lambda item: item.path):
        digest.update(file.path.encode("utf-8"))
        digest.update(str(file.size_bytes).encode("ascii"))
        digest.update(file.sha256.encode("ascii"))
    return digest.hexdigest()


def read_manifest(
    backup_path: Path,
    configuration: BackupConfiguration,
) -> BackupManifest:
    manifest_path = backup_path / configuration.manifest_name
    try:
        return BackupManifest.from_json(manifest_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise InfrastructureError(
            "Backup manifest could not be read.",
            technical_message="Backup manifest read failed.",
            cause=error,
            metadata={"path": str(manifest_path)},
        ) from error


def validate_backup(
    backup_path: Path,
    configuration: BackupConfiguration,
    *,
    application_version: str,
) -> BackupManifest:
    resolved_path = _validate_backup_path(backup_path, configuration)
    manifest = read_manifest(resolved_path, configuration)
    _validate_manifest(manifest, resolved_path, configuration, application_version)
    return manifest


def _validate_backup_path(
    backup_path: Path,
    configuration: BackupConfiguration,
) -> Path:
    resolved_directory = configuration.directory.resolve(strict=False)
    resolved_path = backup_path.resolve(strict=False)

    try:
        resolved_path.relative_to(resolved_directory)
    except ValueError as error:
        raise ValidationError(
            "Backup path is invalid.",
            technical_message="Backup path must be inside the configured directory.",
            metadata={
                "path": str(resolved_path),
                "backup_directory": str(resolved_directory),
            },
        ) from error

    if not resolved_path.exists():
        raise ValidationError(
            "Backup path is invalid.",
            technical_message="Backup directory does not exist.",
            metadata={"path": str(resolved_path)},
        )

    if not resolved_path.is_dir():
        raise ValidationError(
            "Backup path is invalid.",
            technical_message="Backup path must point to a directory.",
            metadata={"path": str(resolved_path)},
        )

    if resolved_path.suffix != configuration.extension:
        raise ValidationError(
            "Backup path is invalid.",
            technical_message="Backup directory extension is not official.",
            metadata={"path": str(resolved_path)},
        )

    return resolved_path


def _validate_manifest(
    manifest: BackupManifest,
    backup_path: Path,
    configuration: BackupConfiguration,
    application_version: str,
) -> None:
    if manifest.application_version != application_version:
        raise ValidationError(
            "Backup version is incompatible.",
            technical_message="Backup application version does not match.",
            metadata={
                "expected": application_version,
                "actual": manifest.application_version,
            },
        )

    manifest_path = backup_path / configuration.manifest_name
    if not manifest_path.is_file():
        raise ValidationError(
            "Backup structure is incomplete.",
            technical_message="Backup manifest file is missing.",
            metadata={"path": str(manifest_path)},
        )

    expected_hash = content_hash(manifest.files)
    if manifest.content_sha256 != expected_hash:
        raise ValidationError(
            "Backup integrity is invalid.",
            technical_message="Backup manifest content hash does not match.",
        )

    for file in manifest.files:
        _validate_file(backup_path, file)


def _validate_file(backup_path: Path, file: BackupFile) -> None:
    path = backup_path / file.path
    if not path.is_file():
        raise ValidationError(
            "Backup structure is incomplete.",
            technical_message="Backup required file is missing.",
            metadata={"path": str(path)},
        )

    current = build_file_manifest(backup_path, file.path)
    if current.size_bytes != file.size_bytes or current.sha256 != file.sha256:
        raise ValidationError(
            "Backup integrity is invalid.",
            technical_message="Backup file hash or size does not match.",
            metadata={"path": file.path},
        )
