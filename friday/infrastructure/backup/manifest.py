from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

from friday.shared.clock import normalize_to_utc, serialize_datetime
from friday.shared.errors import ValidationError
from friday.shared.identifiers import EntityId


@dataclass(frozen=True, slots=True)
class BackupFile:
    path: str
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        if (
            not self.path.strip()
            or self.path.startswith(("/", "\\"))
            or ".." in self.path
        ):
            raise ValidationError(
                "Backup file path is invalid.",
                technical_message="Backup manifest file paths must be relative.",
            )

        if self.size_bytes < 0:
            raise ValidationError(
                "Backup file size is invalid.",
                technical_message="Backup manifest file size must not be negative.",
            )

        _validate_sha256(self.sha256)

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> BackupFile:
        return cls(
            path=_required_text(data, "path"),
            size_bytes=_required_int(data, "size_bytes"),
            sha256=_required_text(data, "sha256"),
        )


@dataclass(frozen=True, slots=True)
class BackupManifest:
    backup_id: EntityId
    created_at: datetime
    application_version: str
    schema_version: str
    files: tuple[BackupFile, ...]
    total_size_bytes: int
    content_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.backup_id, EntityId):
            raise ValidationError(
                "Backup identifier is invalid.",
                technical_message="BackupManifest requires an EntityId.",
            )

        if not self.application_version.strip():
            raise ValidationError(
                "Backup application version is invalid.",
                technical_message="Backup application version must not be empty.",
            )

        if not self.schema_version.strip():
            raise ValidationError(
                "Backup schema version is invalid.",
                technical_message="Backup schema version must not be empty.",
            )

        object.__setattr__(self, "created_at", normalize_to_utc(self.created_at))
        object.__setattr__(self, "files", tuple(self.files))
        _validate_sha256(self.content_sha256)

        if self.total_size_bytes != sum(file.size_bytes for file in self.files):
            raise ValidationError(
                "Backup total size is invalid.",
                technical_message="Backup manifest total size does not match files.",
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "backup_id": str(self.backup_id),
            "created_at": serialize_datetime(self.created_at),
            "application_version": self.application_version,
            "schema_version": self.schema_version,
            "files": [file.to_dict() for file in self.files],
            "total_size_bytes": self.total_size_bytes,
            "content_sha256": self.content_sha256,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, value: str) -> BackupManifest:
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValidationError(
                "Backup manifest is invalid.",
                technical_message="Backup manifest is not valid JSON.",
                cause=error,
            ) from error

        if not isinstance(decoded, dict):
            raise ValidationError(
                "Backup manifest is invalid.",
                technical_message="Backup manifest JSON must be an object.",
            )

        return cls.from_dict(MappingProxyType(decoded))

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> BackupManifest:
        return cls(
            backup_id=EntityId.from_string(_required_text(data, "backup_id")),
            created_at=datetime.fromisoformat(_required_text(data, "created_at")),
            application_version=_required_text(data, "application_version"),
            schema_version=_required_text(data, "schema_version"),
            files=_required_files(data),
            total_size_bytes=_required_int(data, "total_size_bytes"),
            content_sha256=_required_text(data, "content_sha256"),
        )


def _required_files(data: Mapping[str, object]) -> tuple[BackupFile, ...]:
    value = data.get("files")
    if not isinstance(value, list):
        raise ValidationError(
            "Backup manifest is invalid.",
            technical_message="Backup manifest files must be a list.",
        )

    files: list[BackupFile] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValidationError(
                "Backup manifest is invalid.",
                technical_message="Backup manifest file entries must be objects.",
            )
        files.append(BackupFile.from_dict(MappingProxyType(item)))
    return tuple(files)


def _required_text(data: Mapping[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(
            "Backup manifest is invalid.",
            technical_message="Backup manifest field must be a non-empty string.",
            metadata={"field": key},
        )
    return value


def _required_int(data: Mapping[str, object], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise ValidationError(
            "Backup manifest is invalid.",
            technical_message="Backup manifest field must be an integer.",
            metadata={"field": key},
        )
    return value


def _validate_sha256(value: str) -> None:
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValidationError(
            "Backup hash is invalid.",
            technical_message="Backup hashes must be lowercase SHA-256 hex values.",
        )
