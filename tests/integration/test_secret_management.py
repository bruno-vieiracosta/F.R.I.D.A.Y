import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from friday.bootstrap.config import ApplicationSettings, load_settings
from friday.bootstrap.container import ServiceContainer, build_container
from friday.bootstrap.logging import configure_logging
from friday.infrastructure.audit import TechnicalAuditRepository
from friday.infrastructure.persistence import DatabaseInfrastructure, upgrade_database
from friday.security.secrets import (
    SecretIdentifier,
    SecretNotFoundError,
    SecretProvider,
    SecretSource,
)
from friday.shared.clock import Clock, FixedClock
from friday.shared.identifiers import IdGenerator, TypedId


class DeterministicIdGenerator:
    def __init__(self, values: list[UUID]) -> None:
        self.values = values

    def new_id(self, id_type: type[TypedId]) -> TypedId:
        return id_type.from_uuid(self.values.pop(0))


def _settings(temporary_directory: Path) -> ApplicationSettings:
    return load_settings(
        {
            "FRIDAY_ENVIRONMENT": "testing",
            "FRIDAY_DATABASE_PATH": str(temporary_directory / "data" / "friday.db"),
            "FRIDAY_SECRETS_FILE": str(temporary_directory / "config" / "secrets.json"),
            "FRIDAY_LOGS_DIR": str(temporary_directory / "logs"),
            "FRIDAY_LOG_MAX_BYTES": "4096",
            "FRIDAY_LOG_BACKUP_COUNT": "1",
        }
    )


def _container(
    temporary_directory: Path,
) -> tuple[ApplicationSettings, ServiceContainer]:
    settings = _settings(temporary_directory)
    container = build_container(settings)
    container.register_instance(
        Clock,
        FixedClock(datetime(2026, 1, 1, 12, 0, tzinfo=UTC)),
        replace=True,
    )
    container.register_instance(
        IdGenerator,
        DeterministicIdGenerator(
            [UUID(f"00000000-0000-4000-8000-{index:012d}") for index in range(301, 320)]
        ),
        replace=True,
    )
    return settings, container


@pytest.fixture(autouse=True)
def reset_friday_logger() -> None:
    logger = logging.getLogger("friday")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


@pytest.mark.integration
def test_secret_provider_uses_container_configuration_logging_and_audit(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_value = "runtime-secret-that-must-not-leak"
    file_secret_value = "file-secret-that-must-not-leak"
    settings, container = _container(temporary_directory)
    settings.secrets.file_path.parent.mkdir(parents=True)
    settings.secrets.file_path.write_text(
        json.dumps(
            {
                "version": 1,
                "secrets": {"FRIDAY_SECRET_FILE_ONLY": file_secret_value},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("FRIDAY_SECRET_API_KEY", secret_value)
    upgrade_database(settings, configure_logging(settings).get_logger("migrations"))

    try:
        provider = container.resolve(SecretProvider)

        with caplog.at_level(logging.INFO):
            secret = provider.get_secret(SecretIdentifier("FRIDAY_SECRET_API_KEY"))
            file_secret = provider.get_secret(
                SecretIdentifier("FRIDAY_SECRET_FILE_ONLY")
            )
            with pytest.raises(SecretNotFoundError):
                provider.get_secret(SecretIdentifier("FRIDAY_SECRET_MISSING"))

        assert secret.source is SecretSource.ENVIRONMENT
        assert secret.reveal() == secret_value
        assert file_secret.source is SecretSource.FILE
        assert file_secret.reveal() == file_secret_value
        assert secret_value not in caplog.text
        assert file_secret_value not in caplog.text

        records = container.resolve(TechnicalAuditRepository).list_records()
        operations = [record.operation for record in records]
        assert "resolved" in operations
        assert "missing" in operations
        assert secret_value not in str([record.to_dict() for record in records])
        assert file_secret_value not in str([record.to_dict() for record in records])
    finally:
        container.resolve(DatabaseInfrastructure).engine.dispose()
