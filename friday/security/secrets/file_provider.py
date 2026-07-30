from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from friday.security.secrets.exceptions import (
    SecretConfigurationError,
    SecretNotFoundError,
    SecretProviderUnavailableError,
)
from friday.security.secrets.models import Secret, SecretIdentifier, SecretSource


@dataclass(frozen=True, slots=True)
class FileSecretProvider:
    path: Path

    @property
    def source(self) -> SecretSource:
        return SecretSource.FILE

    def get_secret(self, identifier: SecretIdentifier) -> Secret:
        value = self._load().get(identifier.name)
        if value is None:
            raise SecretNotFoundError(
                "The requested secret is not configured.",
                technical_message="File secret was not found.",
                metadata={"identifier": identifier.name, "source": self.source.value},
            )
        return Secret(identifier=identifier, source=self.source, _value=value)

    def contains(self, identifier: SecretIdentifier) -> bool:
        return identifier.name in self._load()

    def list_identifiers(self) -> tuple[SecretIdentifier, ...]:
        return tuple(SecretIdentifier(name) for name in sorted(self._load()))

    def validate(self) -> None:
        self._load()

    def _load(self) -> Mapping[str, str]:
        path = self.path.expanduser()
        try:
            raw_content = path.read_text(encoding="utf-8")
        except FileNotFoundError as error:
            raise SecretProviderUnavailableError(
                "Secret file is not available.",
                technical_message="Configured secret file does not exist.",
                cause=error,
                metadata={"path": str(path)},
            ) from error
        except OSError as error:
            raise SecretProviderUnavailableError(
                "Secret file is not available.",
                technical_message="Configured secret file could not be read.",
                cause=error,
                metadata={"path": str(path)},
            ) from error

        try:
            decoded = json.loads(raw_content)
        except json.JSONDecodeError as error:
            raise SecretConfigurationError(
                "Secret file is invalid.",
                technical_message="Configured secret file is not valid JSON.",
                cause=error,
                metadata={"path": str(path)},
            ) from error

        if not isinstance(decoded, dict):
            raise SecretConfigurationError(
                "Secret file is invalid.",
                technical_message="Secret file root must be a JSON object.",
                metadata={"path": str(path)},
            )

        secrets = decoded.get("secrets")
        if not isinstance(secrets, dict):
            raise SecretConfigurationError(
                "Secret file is invalid.",
                technical_message="Secret file must contain a secrets object.",
                metadata={"path": str(path)},
            )

        return MappingProxyType(_validated_secrets(secrets, path))


def _validated_secrets(values: Mapping[object, object], path: Path) -> dict[str, str]:
    secrets: dict[str, str] = {}
    for key, value in values.items():
        if not isinstance(key, str):
            raise SecretConfigurationError(
                "Secret file is invalid.",
                technical_message="Secret identifiers in file must be strings.",
                metadata={"path": str(path)},
            )

        if not isinstance(value, str) or not value.strip():
            raise SecretConfigurationError(
                "Secret file is invalid.",
                technical_message="Secret values in file must be non-empty strings.",
                metadata={"identifier": key, "path": str(path)},
            )

        identifier = SecretIdentifier(key)
        secrets[identifier.name] = value.strip()

    return secrets
