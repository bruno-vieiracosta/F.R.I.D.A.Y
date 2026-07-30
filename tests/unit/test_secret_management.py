import json
import logging
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from friday.bootstrap.config import load_settings
from friday.bootstrap.container import build_container
from friday.security.secrets import (
    EnvironmentSecretProvider,
    FileSecretProvider,
    Secret,
    SecretConfigurationError,
    SecretIdentifier,
    SecretNotFoundError,
    SecretProvider,
    SecretProviderResolver,
    SecretProviderUnavailableError,
    SecretSource,
    build_secret_provider_resolver,
)
from friday.shared.errors import ConfigurationError, ValidationError


class RecordingAuditCallback:
    def __init__(self) -> None:
        self.operations: list[str] = []
        self.metadata: list[dict[str, object]] = []

    def __call__(
        self,
        operation: str,
        level: str,
        message: str,
        metadata: dict[str, object] | None,
    ) -> None:
        self.operations.append(f"{level}:{operation}:{message}")
        self.metadata.append(dict(metadata or {}))


def _secret_file(path: Path, secrets: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"version": 1, "secrets": secrets}),
        encoding="utf-8",
    )


@pytest.mark.unit
def test_secret_identifier_is_typed_immutable_and_serializable() -> None:
    identifier = SecretIdentifier.from_text(" FRIDAY_SECRET_API_KEY ")

    assert identifier.name == "FRIDAY_SECRET_API_KEY"
    assert str(identifier) == "FRIDAY_SECRET_API_KEY"
    assert identifier.to_dict() == {"name": "FRIDAY_SECRET_API_KEY"}
    with pytest.raises(FrozenInstanceError):
        identifier.name = "FRIDAY_SECRET_OTHER"


@pytest.mark.unit
def test_secret_identifier_rejects_invalid_names() -> None:
    for value in ["", " friday_secret_api_key ", "1SECRET", "SECRET-KEY", "A\x00B"]:
        with pytest.raises(ValidationError, match="Secret identifier is invalid"):
            SecretIdentifier.from_text(value)


@pytest.mark.unit
def test_secret_value_is_redacted_outside_explicit_reveal() -> None:
    secret = Secret(
        identifier=SecretIdentifier("FRIDAY_SECRET_TOKEN"),
        source=SecretSource.ENVIRONMENT,
        _value="super-secret-token",
    )

    assert secret.reveal() == "super-secret-token"
    assert str(secret) == "<redacted>"
    assert secret.to_dict() == {
        "identifier": "FRIDAY_SECRET_TOKEN",
        "source": "environment",
        "value": "<redacted>",
    }
    assert "super-secret-token" not in repr(secret)


@pytest.mark.unit
def test_secret_rejects_empty_value() -> None:
    with pytest.raises(ValidationError, match="Secret value is invalid"):
        Secret(
            identifier=SecretIdentifier("FRIDAY_SECRET_TOKEN"),
            source=SecretSource.FILE,
            _value="",
        )


@pytest.mark.unit
def test_environment_provider_reads_only_prefixed_secrets() -> None:
    provider = EnvironmentSecretProvider(
        {
            "FRIDAY_ENVIRONMENT": "testing",
            "FRIDAY_SECRET_API_KEY": " environment-secret ",
            "FRIDAY_SECRET_EMPTY": " ",
            "OTHER_SECRET": "ignored",
        }
    )
    identifier = SecretIdentifier("FRIDAY_SECRET_API_KEY")

    assert isinstance(provider, SecretProvider)
    assert provider.source is SecretSource.ENVIRONMENT
    assert provider.contains(identifier) is True
    assert provider.list_identifiers() == (identifier,)
    assert provider.get_secret(identifier).reveal() == "environment-secret"


@pytest.mark.unit
def test_environment_provider_handles_missing_and_invalid_configuration() -> None:
    provider = EnvironmentSecretProvider({})

    with pytest.raises(SecretNotFoundError, match="requested secret"):
        provider.get_secret(SecretIdentifier("FRIDAY_SECRET_API_KEY"))

    with pytest.raises(ConfigurationError, match="prefix"):
        EnvironmentSecretProvider({}, prefix="")

    with pytest.raises(ConfigurationError, match="prefix"):
        EnvironmentSecretProvider({}, prefix="BAD\x00")


@pytest.mark.unit
def test_file_provider_reads_secure_json_file(temporary_directory: Path) -> None:
    path = temporary_directory / "config" / "secrets.json"
    _secret_file(path, {"FRIDAY_SECRET_API_KEY": "file-secret"})
    provider = FileSecretProvider(path)
    identifier = SecretIdentifier("FRIDAY_SECRET_API_KEY")

    assert provider.source is SecretSource.FILE
    assert provider.contains(identifier) is True
    assert provider.list_identifiers() == (identifier,)
    assert provider.get_secret(identifier).reveal() == "file-secret"


@pytest.mark.unit
def test_file_provider_rejects_missing_secret_and_unavailable_file(
    temporary_directory: Path,
) -> None:
    path = temporary_directory / "config" / "secrets.json"
    _secret_file(path, {"FRIDAY_SECRET_PRESENT": "value"})
    provider = FileSecretProvider(path)

    with pytest.raises(SecretNotFoundError, match="requested secret"):
        provider.get_secret(SecretIdentifier("FRIDAY_SECRET_MISSING"))

    missing_provider = FileSecretProvider(temporary_directory / "missing.json")
    with pytest.raises(SecretProviderUnavailableError, match="Secret file"):
        missing_provider.validate()


@pytest.mark.unit
def test_file_provider_rejects_invalid_json_and_structure(
    temporary_directory: Path,
) -> None:
    path = temporary_directory / "config" / "secrets.json"
    path.parent.mkdir(parents=True)

    path.write_text("{", encoding="utf-8")
    with pytest.raises(SecretConfigurationError, match="Secret file is invalid"):
        FileSecretProvider(path).validate()

    path.write_text("[]", encoding="utf-8")
    with pytest.raises(SecretConfigurationError, match="Secret file is invalid"):
        FileSecretProvider(path).validate()

    path.write_text(json.dumps({"version": 1}), encoding="utf-8")
    with pytest.raises(SecretConfigurationError, match="Secret file is invalid"):
        FileSecretProvider(path).validate()

    path.write_text(
        json.dumps({"version": 1, "secrets": {"FRIDAY_SECRET_EMPTY": ""}}),
        encoding="utf-8",
    )
    with pytest.raises(SecretConfigurationError, match="Secret file is invalid"):
        FileSecretProvider(path).validate()


@pytest.mark.unit
def test_resolver_prefers_environment_and_falls_back_to_file(
    temporary_directory: Path,
) -> None:
    path = temporary_directory / "config" / "secrets.json"
    _secret_file(
        path,
        {
            "FRIDAY_SECRET_API_KEY": "file-secret",
            "FRIDAY_SECRET_FILE_ONLY": "file-only",
        },
    )
    resolver = build_secret_provider_resolver(
        environment_provider=EnvironmentSecretProvider(
            {"FRIDAY_SECRET_API_KEY": "environment-secret"}
        ),
        file_provider=FileSecretProvider(path),
        logger=logging.getLogger("friday.tests.secrets"),
    )

    assert resolver.get_secret(SecretIdentifier("FRIDAY_SECRET_API_KEY")).reveal() == (
        "environment-secret"
    )
    file_secret = resolver.get_secret(SecretIdentifier("FRIDAY_SECRET_FILE_ONLY"))
    assert file_secret.reveal() == "file-only"
    assert (
        resolver.active_source_for(SecretIdentifier("FRIDAY_SECRET_API_KEY"))
        is SecretSource.ENVIRONMENT
    )


@pytest.mark.unit
def test_resolver_ignores_unavailable_fallback_and_reports_missing(
    temporary_directory: Path,
) -> None:
    resolver = build_secret_provider_resolver(
        environment_provider=EnvironmentSecretProvider({}),
        file_provider=FileSecretProvider(temporary_directory / "missing.json"),
        logger=logging.getLogger("friday.tests.secrets"),
    )

    assert resolver.contains(SecretIdentifier("FRIDAY_SECRET_MISSING")) is False
    assert resolver.list_identifiers() == ()
    resolver.validate()
    with pytest.raises(SecretNotFoundError, match="requested secret"):
        resolver.get_secret(SecretIdentifier("FRIDAY_SECRET_MISSING"))


@pytest.mark.unit
def test_resolver_logs_and_audits_without_secret_values(
    temporary_directory: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    path = temporary_directory / "config" / "secrets.json"
    _secret_file(path, {"FRIDAY_SECRET_API_KEY": "file-secret-that-must-not-leak"})
    audit = RecordingAuditCallback()
    resolver = build_secret_provider_resolver(
        environment_provider=EnvironmentSecretProvider({}),
        file_provider=FileSecretProvider(path),
        logger=logging.getLogger("friday.tests.secrets"),
        audit_callback=audit,
    )

    with caplog.at_level(logging.INFO):
        secret = resolver.get_secret(SecretIdentifier("FRIDAY_SECRET_API_KEY"))

    assert secret.reveal() == "file-secret-that-must-not-leak"
    assert "resolved" in audit.operations[0]
    assert "file-secret-that-must-not-leak" not in caplog.text
    assert "file-secret-that-must-not-leak" not in str(audit.metadata)


@pytest.mark.unit
def test_resolver_requires_at_least_one_provider() -> None:
    with pytest.raises(ConfigurationError, match="Secret providers are invalid"):
        SecretProviderResolver(
            providers=(),
            logger=logging.getLogger("friday.tests.secrets"),
        )


@pytest.mark.unit
def test_secret_settings_are_loaded_from_application_configuration(
    temporary_directory: Path,
) -> None:
    settings = load_settings(
        {
            "FRIDAY_BASE_DIR": str(temporary_directory / "base"),
            "FRIDAY_SECRETS_FILE": str(temporary_directory / "secrets.json"),
            "FRIDAY_SECRET_ENV_PREFIX": "APP_SECRET_",
        }
    )

    assert settings.secrets.file_path == temporary_directory / "secrets.json"
    assert settings.secrets.environment_prefix == "APP_SECRET_"


@pytest.mark.unit
def test_secret_provider_is_registered_in_container(
    temporary_directory: Path,
) -> None:
    settings = load_settings(
        {
            "FRIDAY_ENVIRONMENT": "testing",
            "FRIDAY_SECRETS_FILE": str(temporary_directory / "config" / "secrets.json"),
            "FRIDAY_LOGS_DIR": str(temporary_directory / "logs"),
            "FRIDAY_LOG_MAX_BYTES": "1024",
            "FRIDAY_LOG_BACKUP_COUNT": "1",
        }
    )

    container = build_container(settings)

    assert isinstance(
        container.resolve(EnvironmentSecretProvider),
        EnvironmentSecretProvider,
    )
    assert isinstance(container.resolve(FileSecretProvider), FileSecretProvider)
    assert isinstance(container.resolve(SecretProviderResolver), SecretProviderResolver)
    assert container.resolve(SecretProvider) is container.resolve(
        SecretProviderResolver
    )
