from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from friday.bootstrap.config import ApplicationSettings, load_settings
from friday.bootstrap.logging import configure_logging
from friday.infrastructure.persistence import (
    DatabaseInfrastructure,
    SqlAlchemyEngineFactory,
    SqlAlchemySessionFactory,
    downgrade_database,
    resolve_database_configuration,
    upgrade_database,
)


def _settings(temporary_directory: Path) -> ApplicationSettings:
    return load_settings(
        {
            "FRIDAY_ENVIRONMENT": "testing",
            "FRIDAY_DATABASE_PATH": str(temporary_directory / "data" / "friday.db"),
            "FRIDAY_LOGS_DIR": str(temporary_directory / "logs"),
            "FRIDAY_LOG_MAX_BYTES": "4096",
            "FRIDAY_LOG_BACKUP_COUNT": "1",
        }
    )


def _engine(settings: ApplicationSettings) -> Engine:
    return SqlAlchemyEngineFactory(
        configuration=resolve_database_configuration(settings),
        logger=configure_logging(settings).get_logger("database"),
    ).create()


def _table_names(engine: Engine) -> list[str]:
    try:
        with engine.connect() as connection:
            return list(inspect(connection).get_table_names())
    finally:
        engine.dispose()


@pytest.mark.integration
def test_alembic_upgrade_creates_initial_technical_table(
    temporary_directory: Path,
) -> None:
    settings = _settings(temporary_directory)
    logger = configure_logging(settings).get_logger("migrations")

    upgrade_database(settings, logger)

    table_names = _table_names(_engine(settings))
    assert "application_metadata" in table_names
    assert "technical_audit_records" in table_names
    assert "alembic_version" in table_names


@pytest.mark.integration
def test_alembic_downgrade_removes_initial_technical_table(
    temporary_directory: Path,
) -> None:
    settings = _settings(temporary_directory)
    logger = configure_logging(settings).get_logger("migrations")
    upgrade_database(settings, logger)

    downgrade_database(settings, logger)

    table_names = _table_names(_engine(settings))
    assert table_names == []


@pytest.mark.integration
def test_migrations_are_compatible_with_database_infrastructure(
    temporary_directory: Path,
) -> None:
    settings = _settings(temporary_directory)
    logger_factory = configure_logging(settings)
    logger = logger_factory.get_logger("migrations")
    engine = _engine(settings)
    database = DatabaseInfrastructure(
        configuration=resolve_database_configuration(settings),
        engine=engine,
        session_factory=SqlAlchemySessionFactory.from_engine(engine),
    )

    upgrade_database(settings, logger)

    assert database.engine is engine
    assert "application_metadata" in _table_names(database.engine)
