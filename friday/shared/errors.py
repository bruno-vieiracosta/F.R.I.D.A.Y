from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from friday.bootstrap.logging import mask_sensitive_data


class ErrorCategory(StrEnum):
    DOMAIN = "DOMAIN"
    APPLICATION = "APPLICATION"
    VALIDATION = "VALIDATION"
    CONFIGURATION = "CONFIG"
    INFRASTRUCTURE = "INFRA"
    PERSISTENCE = "PERSISTENCE"
    SECURITY = "SECURITY"
    INTEGRATION = "INTEGRATION"


@dataclass(frozen=True, slots=True)
class ErrorDescriptor:
    code: str
    category: ErrorCategory
    public_message: str


class FridayError(Exception):
    descriptor = ErrorDescriptor(
        code="FRIDAY-ERROR-001",
        category=ErrorCategory.APPLICATION,
        public_message="An unexpected application error occurred.",
    )

    def __init__(
        self,
        public_message: str | None = None,
        *,
        code: str | None = None,
        technical_message: str | None = None,
        cause: BaseException | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> None:
        self.code = code or self.descriptor.code
        self.category = self.descriptor.category
        self.public_message = public_message or self.descriptor.public_message
        self.technical_message = technical_message or self.public_message
        self.cause = cause
        self.metadata = MappingProxyType(dict(metadata or {}))
        super().__init__(self.public_message)

        if cause is not None:
            self.__cause__ = cause

    def __str__(self) -> str:
        return f"{self.code}: {self.public_message}"

    def to_log_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "code": self.code,
            "category": self.category.value,
            "message": mask_sensitive_data(self.public_message),
        }
        data["technical_message"] = mask_sensitive_data(self.technical_message)
        data["metadata"] = _safe_metadata(self.metadata)

        if self.cause is not None:
            data["cause"] = {
                "type": type(self.cause).__name__,
                "message": mask_sensitive_data(str(self.cause)),
            }

        return data

    def to_public_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "category": self.category.value,
            "message": mask_sensitive_data(self.public_message),
        }


class DomainError(FridayError):
    descriptor = ErrorDescriptor(
        code="FRIDAY-DOMAIN-001",
        category=ErrorCategory.DOMAIN,
        public_message="A domain rule could not be completed.",
    )


class ApplicationError(FridayError):
    descriptor = ErrorDescriptor(
        code="FRIDAY-APP-001",
        category=ErrorCategory.APPLICATION,
        public_message="The application could not complete the operation.",
    )


class ValidationError(FridayError):
    descriptor = ErrorDescriptor(
        code="FRIDAY-VALIDATION-001",
        category=ErrorCategory.VALIDATION,
        public_message="The provided data is invalid.",
    )


class ConfigurationError(FridayError):
    descriptor = ErrorDescriptor(
        code="FRIDAY-CONFIG-001",
        category=ErrorCategory.CONFIGURATION,
        public_message="The application configuration is invalid.",
    )


class InfrastructureError(FridayError):
    descriptor = ErrorDescriptor(
        code="FRIDAY-INFRA-001",
        category=ErrorCategory.INFRASTRUCTURE,
        public_message="A technical infrastructure error occurred.",
    )


class PersistenceError(InfrastructureError):
    descriptor = ErrorDescriptor(
        code="FRIDAY-PERSISTENCE-001",
        category=ErrorCategory.PERSISTENCE,
        public_message="The persistence operation could not be completed.",
    )


class SecurityError(FridayError):
    descriptor = ErrorDescriptor(
        code="FRIDAY-SECURITY-001",
        category=ErrorCategory.SECURITY,
        public_message="The security operation could not be completed.",
    )


class IntegrationError(FridayError):
    descriptor = ErrorDescriptor(
        code="FRIDAY-INTEGRATION-001",
        category=ErrorCategory.INTEGRATION,
        public_message="The external integration could not be completed.",
    )


def _safe_metadata(metadata: Mapping[str, object]) -> dict[str, object]:
    return {key: _safe_value(value) for key, value in metadata.items()}


def _safe_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): _safe_value(nested_value) for key, nested_value in value.items()
        }

    if isinstance(value, list | tuple | set):
        return [_safe_value(item) for item in value]

    if isinstance(value, str):
        return mask_sensitive_data(value)

    return value
