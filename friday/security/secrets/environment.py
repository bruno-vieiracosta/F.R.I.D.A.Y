from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from friday.security.secrets.exceptions import SecretNotFoundError
from friday.security.secrets.models import Secret, SecretIdentifier, SecretSource
from friday.shared.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class EnvironmentSecretProvider:
    environment: Mapping[str, str] = field(repr=False)
    prefix: str = "FRIDAY_SECRET_"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "environment",
            MappingProxyType(dict(self.environment)),
        )
        self.validate()

    @classmethod
    def from_process(
        cls,
        *,
        prefix: str = "FRIDAY_SECRET_",
    ) -> EnvironmentSecretProvider:
        return cls(os.environ, prefix=prefix)

    @property
    def source(self) -> SecretSource:
        return SecretSource.ENVIRONMENT

    def get_secret(self, identifier: SecretIdentifier) -> Secret:
        value = self._secrets().get(identifier.name)
        if value is None:
            raise SecretNotFoundError(
                "The requested secret is not configured.",
                technical_message="Environment secret was not found.",
                metadata={"identifier": identifier.name, "source": self.source.value},
            )
        return Secret(identifier=identifier, source=self.source, _value=value)

    def contains(self, identifier: SecretIdentifier) -> bool:
        return identifier.name in self._secrets()

    def list_identifiers(self) -> tuple[SecretIdentifier, ...]:
        return tuple(SecretIdentifier(name) for name in sorted(self._secrets()))

    def validate(self) -> None:
        if not self.prefix.strip():
            raise ConfigurationError(
                "Secret environment prefix is invalid.",
                technical_message="Secret environment prefix must not be empty.",
            )

        if "\x00" in self.prefix:
            raise ConfigurationError(
                "Secret environment prefix is invalid.",
                technical_message=(
                    "Secret environment prefix must not contain null bytes."
                ),
            )

    def _secrets(self) -> dict[str, str]:
        secrets: dict[str, str] = {}
        for name, value in self.environment.items():
            if not name.startswith(self.prefix):
                continue

            normalized_value = value.strip()
            if not normalized_value:
                continue

            identifier = SecretIdentifier(name)
            secrets[identifier.name] = normalized_value
        return secrets
