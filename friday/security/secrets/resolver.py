from __future__ import annotations

import logging as standard_logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from friday.security.secrets.exceptions import (
    SecretNotFoundError,
    SecretProviderUnavailableError,
)
from friday.security.secrets.models import Secret, SecretIdentifier, SecretSource
from friday.security.secrets.provider import SecretProvider
from friday.shared.errors import ConfigurationError

SecretAuditCallback = Callable[
    [str, str, str, Mapping[str, object] | None],
    None,
]


@dataclass(frozen=True, slots=True)
class SecretProviderResolver:
    providers: tuple[SecretProvider, ...]
    logger: standard_logging.Logger
    audit_callback: SecretAuditCallback | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.providers:
            raise ConfigurationError(
                "Secret providers are invalid.",
                technical_message="At least one secret provider must be configured.",
            )

    @property
    def source(self) -> SecretSource:
        return SecretSource.RESOLVER

    def get_secret(self, identifier: SecretIdentifier) -> Secret:
        for provider in self.providers:
            try:
                if provider.contains(identifier):
                    secret = provider.get_secret(identifier)
                    self.logger.info(
                        "Secret resolved",
                        extra={
                            "secret": {
                                "identifier": identifier.name,
                                "source": provider.source.value,
                            }
                        },
                    )
                    self._audit(
                        "resolved",
                        "info",
                        "Secret resolved",
                        {
                            "identifier": identifier.name,
                            "source": provider.source.value,
                        },
                    )
                    return secret
            except SecretProviderUnavailableError as error:
                self.logger.warning(
                    "Secret provider unavailable",
                    extra={"secret_error": error.to_log_dict()},
                )
                self._audit(
                    "provider_unavailable",
                    "warning",
                    "Secret provider unavailable",
                    {"source": provider.source.value},
                )
                continue

        self.logger.warning(
            "Secret not found",
            extra={"secret": {"identifier": identifier.name}},
        )
        self._audit(
            "missing",
            "warning",
            "Secret not found",
            {"identifier": identifier.name},
        )
        raise SecretNotFoundError(
            "The requested secret is not configured.",
            technical_message=(
                "No configured secret provider contains the requested key."
            ),
            metadata={"identifier": identifier.name},
        )

    def contains(self, identifier: SecretIdentifier) -> bool:
        for provider in self.providers:
            try:
                if provider.contains(identifier):
                    return True
            except SecretProviderUnavailableError:
                continue
        return False

    def list_identifiers(self) -> tuple[SecretIdentifier, ...]:
        names: set[str] = set()
        for provider in self.providers:
            try:
                names.update(
                    identifier.name for identifier in provider.list_identifiers()
                )
            except SecretProviderUnavailableError:
                continue
        return tuple(SecretIdentifier(name) for name in sorted(names))

    def validate(self) -> None:
        for provider in self.providers:
            try:
                provider.validate()
            except SecretProviderUnavailableError:
                continue

    def active_source_for(self, identifier: SecretIdentifier) -> SecretSource:
        for provider in self.providers:
            try:
                if provider.contains(identifier):
                    return provider.source
            except SecretProviderUnavailableError:
                continue
        raise SecretNotFoundError(
            "The requested secret is not configured.",
            technical_message="No active secret provider contains the requested key.",
            metadata={"identifier": identifier.name},
        )

    def _audit(
        self,
        operation: str,
        level: str,
        message: str,
        metadata: Mapping[str, object] | None,
    ) -> None:
        if self.audit_callback is None:
            return

        self.audit_callback(operation, level, message, metadata)


def build_secret_provider_resolver(
    *,
    environment_provider: SecretProvider,
    file_provider: SecretProvider,
    logger: standard_logging.Logger,
    audit_callback: SecretAuditCallback | None = None,
) -> SecretProviderResolver:
    return SecretProviderResolver(
        providers=(environment_provider, file_provider),
        logger=logger,
        audit_callback=audit_callback,
    )
