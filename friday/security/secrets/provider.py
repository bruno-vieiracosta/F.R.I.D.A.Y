from __future__ import annotations

from typing import Protocol, runtime_checkable

from friday.security.secrets.models import Secret, SecretIdentifier, SecretSource


@runtime_checkable
class SecretProvider(Protocol):
    @property
    def source(self) -> SecretSource:
        pass

    def get_secret(self, identifier: SecretIdentifier) -> Secret:
        pass

    def contains(self, identifier: SecretIdentifier) -> bool:
        pass

    def list_identifiers(self) -> tuple[SecretIdentifier, ...]:
        pass

    def validate(self) -> None:
        pass
