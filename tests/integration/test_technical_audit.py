import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import inspect

from friday.application.event_bus import EventBus
from friday.application.persistence.unit_of_work import UnitOfWork
from friday.bootstrap.config import ApplicationSettings, load_settings
from friday.bootstrap.container import ServiceContainer, build_container
from friday.bootstrap.logging import configure_logging
from friday.infrastructure.audit import (
    AuditCategory,
    AuditLevel,
    TechnicalAuditEvent,
    TechnicalAuditRepository,
    TechnicalAuditService,
)
from friday.infrastructure.persistence import (
    DatabaseInfrastructure,
    downgrade_database,
    upgrade_database,
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
            [
                UUID("00000000-0000-4000-8000-000000000101"),
                UUID("00000000-0000-4000-8000-000000000102"),
            ]
        ),
        replace=True,
    )
    return settings, container


def _dispose_container_database(container: ServiceContainer) -> None:
    container.resolve(DatabaseInfrastructure).engine.dispose()


def _table_names(database: DatabaseInfrastructure) -> list[str]:
    try:
        with database.engine.connect() as connection:
            return list(inspect(connection).get_table_names())
    finally:
        database.engine.dispose()


@pytest.fixture(autouse=True)
def reset_friday_logger() -> None:
    logger = logging.getLogger("friday")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


@pytest.mark.integration
def test_technical_audit_flow_persists_and_loads_record(
    temporary_directory: Path,
) -> None:
    settings, container = _container(temporary_directory)
    logger = configure_logging(settings).get_logger("migrations")
    upgrade_database(settings, logger)

    try:
        service = container.resolve(TechnicalAuditService)
        repository = container.resolve(TechnicalAuditRepository)
        record = service.record(
            category=AuditCategory.INFRASTRUCTURE,
            origin="database",
            operation="initialize",
            level=AuditLevel.INFO,
            message="Database initialized",
            metadata={"component": "persistence"},
        )

        records = repository.list_records()

        assert records == (record,)
        assert records[0].metadata == {"component": "persistence"}
    finally:
        _dispose_container_database(container)


@pytest.mark.integration
def test_technical_audit_event_bus_integration_records_event(
    temporary_directory: Path,
) -> None:
    settings, container = _container(temporary_directory)
    logger = configure_logging(settings).get_logger("migrations")
    upgrade_database(settings, logger)
    try:
        event_bus = container.resolve(EventBus)
        event = TechnicalAuditEvent.create(
            clock=container.resolve(Clock),
            id_generator=container.resolve(IdGenerator),
            category=AuditCategory.EVENT_BUS,
            origin="events",
            operation="publish",
            level=AuditLevel.INFO,
            message="Event published",
            metadata={"handlers": 1},
        )

        event_bus.publish(event)

        records = container.resolve(TechnicalAuditRepository).list_records()
        assert len(records) == 1
        assert records[0].origin == "events"
        assert records[0].operation == "publish"
        assert records[0].metadata == {"handlers": 1}
    finally:
        _dispose_container_database(container)


@pytest.mark.integration
def test_technical_audit_uses_database_infrastructure_and_unit_of_work(
    temporary_directory: Path,
) -> None:
    settings, container = _container(temporary_directory)
    logger = configure_logging(settings).get_logger("migrations")
    upgrade_database(settings, logger)
    try:
        database = container.resolve(DatabaseInfrastructure)

        with container.resolve(UnitOfWork) as unit_of_work:
            unit_of_work.begin()
            unit_of_work.commit()

        container.resolve(TechnicalAuditService).record(
            category=AuditCategory.PERSISTENCE,
            origin="unit_of_work",
            operation="commit",
            level=AuditLevel.INFO,
            message="Unit of Work committed",
        )

        assert "technical_audit_records" in _table_names(database)
    finally:
        _dispose_container_database(container)


@pytest.mark.integration
def test_technical_audit_migration_upgrade_and_downgrade(
    temporary_directory: Path,
) -> None:
    settings, container = _container(temporary_directory)
    logger = configure_logging(settings).get_logger("migrations")
    database = container.resolve(DatabaseInfrastructure)

    upgrade_database(settings, logger)

    upgraded_tables = _table_names(database)
    assert "technical_audit_records" in upgraded_tables
    assert "application_metadata" in upgraded_tables

    downgrade_database(settings, logger)

    assert _table_names(database) == []
