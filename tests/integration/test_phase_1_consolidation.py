import logging
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine

from friday.application.event_bus import EventBus
from friday.application.persistence import UnitOfWork
from friday.bootstrap.config import ApplicationSettings, load_settings
from friday.bootstrap.container import build_container
from friday.bootstrap.logging import LoggerFactory
from friday.infrastructure.audit import (
    TechnicalAuditEventHandler,
    TechnicalAuditRepository,
    TechnicalAuditService,
)
from friday.infrastructure.backup import BackupConfiguration, BackupService
from friday.infrastructure.persistence import (
    DatabaseConfiguration,
    DatabaseInfrastructure,
    SqlAlchemyEngineFactory,
    SqlAlchemySessionFactory,
    SqlAlchemyUnitOfWork,
)
from friday.security.hardening import SecureFilesystem, SecurityPolicy
from friday.security.secrets import (
    EnvironmentSecretProvider,
    FileSecretProvider,
    SecretProvider,
    SecretProviderResolver,
)
from friday.shared.clock import Clock, SystemClock
from friday.shared.identifiers import IdGenerator


def _settings(temporary_directory: Path) -> ApplicationSettings:
    return load_settings(
        {
            "FRIDAY_ENVIRONMENT": "testing",
            "FRIDAY_DATABASE_PATH": str(temporary_directory / "data" / "friday.db"),
            "FRIDAY_BACKUPS_DIR": str(temporary_directory / "backups"),
            "FRIDAY_SECRETS_FILE": str(temporary_directory / "config" / "secrets.json"),
            "FRIDAY_LOGS_DIR": str(temporary_directory / "logs"),
            "FRIDAY_LOG_MAX_BYTES": "4096",
            "FRIDAY_LOG_BACKUP_COUNT": "1",
        }
    )


@pytest.fixture(autouse=True)
def reset_friday_logger() -> None:
    logger = logging.getLogger("friday")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


@pytest.mark.integration
def test_phase_1_services_are_registered_and_resolvable(
    temporary_directory: Path,
) -> None:
    settings = _settings(temporary_directory)
    container = build_container(settings)

    singleton_services: tuple[type[object], ...] = (
        ApplicationSettings,
        LoggerFactory,
        logging.Logger,
        Clock,
        IdGenerator,
        DatabaseConfiguration,
        BackupConfiguration,
        SecurityPolicy,
        SecureFilesystem,
        EnvironmentSecretProvider,
        FileSecretProvider,
        SqlAlchemyEngineFactory,
        Engine,
        SqlAlchemySessionFactory,
        DatabaseInfrastructure,
        TechnicalAuditRepository,
        TechnicalAuditService,
        TechnicalAuditEventHandler,
        EventBus,
        SecretProviderResolver,
        SecretProvider,
        BackupService,
    )

    try:
        for service_type in singleton_services:
            assert container.contains(service_type) is True
            assert container.resolve(service_type) is container.resolve(service_type)

        first_unit_of_work = container.resolve(UnitOfWork)
        second_unit_of_work = container.resolve(UnitOfWork)

        assert isinstance(container.resolve(Clock), SystemClock)
        assert isinstance(first_unit_of_work, SqlAlchemyUnitOfWork)
        assert isinstance(second_unit_of_work, SqlAlchemyUnitOfWork)
        assert first_unit_of_work is not second_unit_of_work
        assert container.resolve(BackupService).secure_filesystem is container.resolve(
            SecureFilesystem
        )
        assert container.resolve(FileSecretProvider).secure_filesystem is (
            container.resolve(SecureFilesystem)
        )
    finally:
        container.resolve(DatabaseInfrastructure).engine.dispose()


@pytest.mark.integration
def test_readme_references_existing_phase_1_documentation() -> None:
    root = Path(__file__).resolve().parents[2]
    readme = root / "README.md"
    documentation_paths = {
        "docs/architecture/package_structure.md",
        "docs/development/backup_infrastructure.md",
        "docs/development/code_quality.md",
        "docs/development/configuration.md",
        "docs/development/continuous_integration.md",
        "docs/development/database_infrastructure.md",
        "docs/development/database_migrations.md",
        "docs/development/dependency_injection.md",
        "docs/development/errors.md",
        "docs/development/event_bus.md",
        "docs/development/financial_types.md",
        "docs/development/identifiers_and_time.md",
        "docs/development/logging.md",
        "docs/development/persistence_contracts.md",
        "docs/development/phase_1_consolidation.md",
        "docs/development/secret_management.md",
        "docs/development/security_hardening.md",
        "docs/development/shared_types.md",
        "docs/development/technical_audit.md",
        "docs/development/testing.md",
    }

    content = readme.read_text(encoding="utf-8")

    for documentation_path in documentation_paths:
        assert documentation_path in content
        assert (root / documentation_path).is_file()
