from pathlib import Path

import pytest
from sqlalchemy.engine import Engine

from friday.application.persistence import UnitOfWork
from friday.bootstrap.config import ApplicationSettings, load_settings
from friday.bootstrap.container import build_container
from friday.infrastructure.persistence import (
    DatabaseConfiguration,
    DatabaseInfrastructure,
    SqlAlchemySessionFactory,
    SqlAlchemyUnitOfWork,
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


@pytest.mark.integration
def test_container_resolves_database_infrastructure(
    temporary_directory: Path,
) -> None:
    settings = _settings(temporary_directory)
    container = build_container(settings)

    configuration = container.resolve(DatabaseConfiguration)
    engine = container.resolve(Engine)
    session_factory = container.resolve(SqlAlchemySessionFactory)
    database = container.resolve(DatabaseInfrastructure)

    assert configuration.path == settings.database_path
    assert engine is container.resolve(Engine)
    assert session_factory is container.resolve(SqlAlchemySessionFactory)
    assert database.engine is engine
    assert database.session_factory is session_factory


@pytest.mark.integration
def test_container_resolves_transient_unit_of_work(
    temporary_directory: Path,
) -> None:
    container = build_container(_settings(temporary_directory))

    first = container.resolve(UnitOfWork)
    second = container.resolve(UnitOfWork)

    assert isinstance(first, SqlAlchemyUnitOfWork)
    assert isinstance(second, SqlAlchemyUnitOfWork)
    assert first is not second


@pytest.mark.integration
def test_resolved_unit_of_work_can_open_commit_and_close(
    temporary_directory: Path,
) -> None:
    container = build_container(_settings(temporary_directory))
    unit_of_work = container.resolve(UnitOfWork)

    with unit_of_work as active_unit_of_work:
        transaction = active_unit_of_work.begin()
        active_unit_of_work.commit()

    assert transaction.is_active is False
