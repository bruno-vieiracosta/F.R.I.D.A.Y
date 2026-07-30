import logging
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from friday.bootstrap.config import ApplicationSettings, load_settings
from friday.bootstrap.logging import configure_logging, log_file_path
from friday.infrastructure.persistence import (
    DatabaseConfiguration,
    SqlAlchemyEngineFactory,
    SqlAlchemySessionFactory,
    SqlAlchemyTransaction,
    SqlAlchemyUnitOfWork,
    ensure_database_directory,
    initialize_database,
    resolve_database_configuration,
)
from friday.shared.errors import InfrastructureError, PersistenceError


class FailingCommitSession:
    def commit(self) -> None:
        raise SQLAlchemyError("commit failed")

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass


class FailingRollbackSession:
    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        raise SQLAlchemyError("rollback failed")

    def close(self) -> None:
        pass


class FailingCloseSession:
    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        raise SQLAlchemyError("close failed")


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


@pytest.fixture(autouse=True)
def reset_friday_logger() -> None:
    logger = logging.getLogger("friday")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


@pytest.mark.unit
def test_database_configuration_comes_from_application_settings(
    temporary_directory: Path,
) -> None:
    settings = _settings(temporary_directory)

    configuration = resolve_database_configuration(settings)

    assert configuration.path == temporary_directory / "data" / "friday.db"
    assert configuration.url.startswith("sqlite+pysqlite:///")
    assert str(configuration.path) in configuration.url


@pytest.mark.unit
def test_database_directory_is_created(temporary_directory: Path) -> None:
    configuration = DatabaseConfiguration(
        path=temporary_directory / "missing" / "friday.db",
        url="sqlite+pysqlite:///unused",
    )

    ensure_database_directory(configuration)

    assert configuration.path.parent.is_dir()


@pytest.mark.unit
def test_database_directory_creation_failure_is_wrapped(
    temporary_directory: Path,
) -> None:
    parent_file = temporary_directory / "not-a-directory"
    parent_file.write_text("blocked", encoding="utf-8")
    configuration = DatabaseConfiguration(
        path=parent_file / "friday.db",
        url="sqlite+pysqlite:///unused",
    )

    with pytest.raises(InfrastructureError) as error:
        ensure_database_directory(configuration)

    assert isinstance(error.value.cause, OSError)


@pytest.mark.unit
def test_engine_factory_creates_reusable_sqlite_engine(
    temporary_directory: Path,
) -> None:
    settings = _settings(temporary_directory)
    configuration = resolve_database_configuration(settings)
    factory = SqlAlchemyEngineFactory(
        configuration=configuration,
        logger=logging.getLogger("friday.tests.database"),
    )

    first = factory.create()
    second = factory.create()

    assert isinstance(first, Engine)
    assert first is second
    assert first.url.drivername == "sqlite+pysqlite"
    assert configuration.path.parent.is_dir()


@pytest.mark.unit
def test_engine_creation_failure_is_wrapped(
    temporary_directory: Path,
) -> None:
    configuration = DatabaseConfiguration(
        path=temporary_directory / "friday.db",
        url="not-a-valid-sqlalchemy-url",
    )
    factory = SqlAlchemyEngineFactory(
        configuration=configuration,
        logger=logging.getLogger("friday.tests.database"),
    )

    with pytest.raises(InfrastructureError) as error:
        factory.create()

    assert isinstance(error.value.cause, SQLAlchemyError)


@pytest.mark.unit
def test_session_factory_creates_sessions(temporary_directory: Path) -> None:
    engine = SqlAlchemyEngineFactory(
        configuration=resolve_database_configuration(_settings(temporary_directory)),
        logger=logging.getLogger("friday.tests.database"),
    ).create()
    session_factory = SqlAlchemySessionFactory.from_engine(engine)

    first = session_factory.create()
    second = session_factory.create()

    try:
        assert isinstance(first, Session)
        assert isinstance(second, Session)
        assert first is not second
        assert first.bind is engine
        assert second.bind is engine
    finally:
        first.close()
        second.close()


@pytest.mark.unit
def test_unit_of_work_controls_session_lifecycle(temporary_directory: Path) -> None:
    engine = SqlAlchemyEngineFactory(
        configuration=resolve_database_configuration(_settings(temporary_directory)),
        logger=logging.getLogger("friday.tests.database"),
    ).create()
    session_factory = SqlAlchemySessionFactory.from_engine(engine)
    unit_of_work = SqlAlchemyUnitOfWork(session_factory)

    with unit_of_work as active_unit_of_work:
        transaction = active_unit_of_work.begin()
        active_unit_of_work.commit()

    assert transaction.is_active is False
    assert unit_of_work._session is None


@pytest.mark.unit
def test_unit_of_work_rolls_back_on_context_error(
    temporary_directory: Path,
) -> None:
    engine = SqlAlchemyEngineFactory(
        configuration=resolve_database_configuration(_settings(temporary_directory)),
        logger=logging.getLogger("friday.tests.database"),
    ).create()
    session_factory = SqlAlchemySessionFactory.from_engine(engine)
    unit_of_work = SqlAlchemyUnitOfWork(session_factory)

    with pytest.raises(ValueError, match="boom"), unit_of_work:
        raise ValueError("boom")

    assert unit_of_work._session is None


@pytest.mark.unit
def test_unit_of_work_requires_active_transaction_for_commit(
    temporary_directory: Path,
) -> None:
    engine = SqlAlchemyEngineFactory(
        configuration=resolve_database_configuration(_settings(temporary_directory)),
        logger=logging.getLogger("friday.tests.database"),
    ).create()
    session_factory = SqlAlchemySessionFactory.from_engine(engine)
    unit_of_work = SqlAlchemyUnitOfWork(session_factory)

    with pytest.raises(PersistenceError, match="Database transaction is not active"):
        unit_of_work.commit()


@pytest.mark.unit
def test_transaction_errors_are_wrapped() -> None:
    with pytest.raises(PersistenceError) as commit_error:
        SqlAlchemyTransaction(FailingCommitSession()).commit()
    assert isinstance(commit_error.value.cause, SQLAlchemyError)

    with pytest.raises(PersistenceError) as rollback_error:
        SqlAlchemyTransaction(FailingRollbackSession()).rollback()
    assert isinstance(rollback_error.value.cause, SQLAlchemyError)

    with pytest.raises(PersistenceError) as close_error:
        SqlAlchemyTransaction(FailingCloseSession()).close()
    assert isinstance(close_error.value.cause, SQLAlchemyError)


@pytest.mark.unit
def test_database_initialization_uses_logger(
    temporary_directory: Path,
) -> None:
    settings = _settings(temporary_directory)
    logger_factory = configure_logging(settings)

    database = initialize_database(settings, logger_factory.get_logger("database"))
    session = database.session_factory.create()

    try:
        assert database.configuration.path == settings.database_path
        assert session.bind is database.engine
        assert "Database infrastructure initialized" in log_file_path(
            settings
        ).read_text(encoding="utf-8")
    finally:
        session.close()
