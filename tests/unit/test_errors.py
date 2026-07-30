import logging
from dataclasses import FrozenInstanceError

import pytest

from friday.bootstrap.config import load_settings
from friday.bootstrap.logging import configure_logging, log_file_path
from friday.shared.errors import (
    ApplicationError,
    ConfigurationError,
    DomainError,
    ErrorCategory,
    ErrorDescriptor,
    FridayError,
    InfrastructureError,
    IntegrationError,
    PersistenceError,
    SecurityError,
    ValidationError,
)

ERROR_TYPES = (
    DomainError,
    ApplicationError,
    ValidationError,
    ConfigurationError,
    InfrastructureError,
    PersistenceError,
    SecurityError,
    IntegrationError,
)


@pytest.mark.unit
def test_error_hierarchy() -> None:
    for error_type in ERROR_TYPES:
        assert issubclass(error_type, FridayError)

    assert issubclass(PersistenceError, InfrastructureError)


@pytest.mark.unit
def test_error_descriptors_are_immutable() -> None:
    descriptor = ErrorDescriptor(
        code="FRIDAY-TEST-001",
        category=ErrorCategory.APPLICATION,
        public_message="Safe message.",
    )

    with pytest.raises(FrozenInstanceError):
        descriptor.code = "FRIDAY-TEST-002"


@pytest.mark.unit
def test_error_codes_are_stable_and_consistent() -> None:
    codes = [error_type().code for error_type in ERROR_TYPES]

    assert len(codes) == len(set(codes))
    assert all(code.startswith("FRIDAY-") for code in codes)
    assert all(code.endswith("-001") for code in codes)


@pytest.mark.unit
def test_public_and_technical_messages_are_separated() -> None:
    error = InfrastructureError(
        "Service temporarily unavailable.",
        technical_message="Connection failed for token=secret-token",
    )

    assert error.public_message == "Service temporarily unavailable."
    assert error.technical_message == "Connection failed for token=secret-token"
    assert "secret-token" not in error.to_public_dict()["message"]
    assert "secret-token" not in error.to_log_dict()["technical_message"]


@pytest.mark.unit
def test_cause_is_preserved() -> None:
    cause = RuntimeError("password=hidden")

    error = PersistenceError(cause=cause)

    assert error.cause is cause
    assert error.__cause__ is cause
    assert error.to_log_dict()["cause"] == {
        "type": "RuntimeError",
        "message": "password=***",
    }


@pytest.mark.unit
def test_metadata_is_immutable_and_serialized_safely() -> None:
    error = SecurityError(
        metadata={
            "user": "local",
            "token": "token=abc",
            "nested": {"api_key": "api_key=xyz"},
            "items": ["secret=value"],
        }
    )

    with pytest.raises(TypeError):
        error.metadata["new"] = "value"

    serialized = error.to_log_dict()
    assert serialized["metadata"] == {
        "user": "local",
        "token": "token=***",
        "nested": {"api_key": "api_key=***"},
        "items": ["secret=***"],
    }


@pytest.mark.unit
def test_public_serialization_does_not_expose_technical_details() -> None:
    error = ConfigurationError(
        "Configuration is invalid.",
        technical_message="Invalid path C:/secret/password=file",
        metadata={"password": "password=abc"},
    )

    assert error.to_public_dict() == {
        "code": "FRIDAY-CONFIG-001",
        "category": "CONFIG",
        "message": "Configuration is invalid.",
    }


@pytest.mark.unit
def test_log_serialization_contains_safe_diagnostic_data() -> None:
    error = IntegrationError(
        technical_message="Bearer abc.def",
        metadata={"endpoint": "local", "credential": "credential=raw"},
    )

    serialized = error.to_log_dict()

    assert serialized["code"] == "FRIDAY-INTEGRATION-001"
    assert serialized["category"] == "INTEGRATION"
    assert serialized["technical_message"] == "Bearer ***"
    assert serialized["metadata"] == {
        "endpoint": "local",
        "credential": "credential=***",
    }


@pytest.mark.unit
def test_string_representation_uses_code_and_public_message() -> None:
    error = ValidationError("Invalid field.")

    assert str(error) == "FRIDAY-VALIDATION-001: Invalid field."


@pytest.mark.unit
def test_code_can_be_overridden_for_specific_future_cases() -> None:
    error = ApplicationError(code="FRIDAY-APP-999")

    assert error.code == "FRIDAY-APP-999"


@pytest.mark.unit
def test_error_is_compatible_with_logging(temporary_directory) -> None:
    settings = load_settings({"FRIDAY_LOGS_DIR": str(temporary_directory / "logs")})
    factory = configure_logging(settings)
    logger = factory.get_logger("errors")
    error = SecurityError(
        technical_message="token=raw-token",
        metadata={"secret": "secret=value"},
    )

    logger.error("Application error: %s", error.to_log_dict())

    for handler in logging.getLogger("friday").handlers:
        handler.flush()

    contents = log_file_path(settings).read_text(encoding="utf-8")
    assert "FRIDAY-SECURITY-001" in contents
    assert "raw-token" not in contents
    assert "secret=value" not in contents
    assert "token=***" in contents
