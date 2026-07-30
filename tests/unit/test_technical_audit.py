import logging
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy.exc import SQLAlchemyError

from friday.bootstrap.config import ApplicationSettings, load_settings
from friday.bootstrap.container import build_container
from friday.bootstrap.logging import configure_logging, log_file_path
from friday.infrastructure.audit import (
    AuditCategory,
    AuditLevel,
    TechnicalAuditEvent,
    TechnicalAuditEventHandler,
    TechnicalAuditRecord,
    TechnicalAuditRepository,
    TechnicalAuditService,
    deserialize_metadata,
    normalize_metadata,
    serialize_metadata,
)
from friday.shared.clock import FixedClock
from friday.shared.errors import PersistenceError, ValidationError
from friday.shared.identifiers import EntityId, TypedId


class DeterministicIdGenerator:
    def __init__(self, value: UUID) -> None:
        self.value = value

    def new_id(self, id_type: type[TypedId]) -> TypedId:
        return id_type.from_uuid(self.value)


class RecordingRepository:
    def __init__(self) -> None:
        self.records: list[TechnicalAuditRecord] = []

    def add(self, record: TechnicalAuditRecord) -> None:
        self.records.append(record)


class FailingRepository:
    def add(self, _record: TechnicalAuditRecord) -> None:
        raise PersistenceError("audit failed")


class FailingSessionFactory:
    def create(self) -> object:
        raise SQLAlchemyError("session failed")


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


def _clock() -> FixedClock:
    return FixedClock(datetime(2026, 1, 1, 12, 0, tzinfo=UTC))


def _id_generator() -> DeterministicIdGenerator:
    return DeterministicIdGenerator(UUID("00000000-0000-4000-8000-000000000016"))


def _record() -> TechnicalAuditRecord:
    return TechnicalAuditRecord.create(
        clock=_clock(),
        id_generator=_id_generator(),
        category=AuditCategory.INFRASTRUCTURE,
        origin="database",
        operation="initialize",
        level=AuditLevel.INFO,
        message="Database initialized",
        metadata={"step": "bootstrap", "count": 1},
    )


@pytest.fixture(autouse=True)
def reset_friday_logger() -> None:
    logger = logging.getLogger("friday")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


@pytest.mark.unit
def test_technical_audit_record_is_immutable_and_serializable() -> None:
    record = _record()

    assert record.record_id == EntityId.from_string(
        "00000000-0000-4000-8000-000000000016"
    )
    assert record.occurred_at == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    assert record.to_dict() == {
        "id": "00000000-0000-4000-8000-000000000016",
        "occurred_at": "2026-01-01T12:00:00+00:00",
        "category": "infrastructure",
        "origin": "database",
        "operation": "initialize",
        "level": "info",
        "message": "Database initialized",
        "metadata": {"step": "bootstrap", "count": 1},
    }
    assert str(record) == "infrastructure.database.initialize[info]"

    with pytest.raises(FrozenInstanceError):
        record.message = "changed"


@pytest.mark.unit
def test_technical_audit_record_rejects_invalid_values() -> None:
    with pytest.raises(ValidationError) as error:
        TechnicalAuditRecord.create(
            clock=_clock(),
            id_generator=_id_generator(),
            category=AuditCategory.INFRASTRUCTURE,
            origin=" ",
            operation="initialize",
            level=AuditLevel.INFO,
            message="Database initialized",
        )

    assert "Audit field origin" in error.value.technical_message


@pytest.mark.unit
def test_metadata_serialization_is_deterministic_and_structured() -> None:
    instant = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    identifier = EntityId.from_string("00000000-0000-4000-8000-000000000016")

    serialized = serialize_metadata(
        {
            "z": ["value", 1, True],
            "a": {"instant": instant, "identifier": identifier},
        }
    )

    assert serialized == (
        '{"a":{"identifier":"00000000-0000-4000-8000-000000000016",'
        '"instant":"2026-01-01T12:00:00+00:00"},"z":["value",1,true]}'
    )
    assert deserialize_metadata(serialized) == {
        "a": {
            "identifier": "00000000-0000-4000-8000-000000000016",
            "instant": "2026-01-01T12:00:00+00:00",
        },
        "z": ["value", 1, True],
    }


@pytest.mark.unit
def test_metadata_serialization_rejects_unsupported_values() -> None:
    with pytest.raises(ValidationError, match="Audit metadata value is invalid"):
        normalize_metadata({"unsupported": object()})

    with pytest.raises(ValidationError, match="Audit metadata key is invalid"):
        normalize_metadata({"": "empty"})

    with pytest.raises(ValidationError, match="Audit metadata is invalid"):
        deserialize_metadata("[]")


@pytest.mark.unit
def test_metadata_serialization_rejects_invalid_json_and_nonfinite_float() -> None:
    with pytest.raises(ValidationError, match="Audit metadata is invalid"):
        deserialize_metadata("{")

    with pytest.raises(ValidationError, match="Audit metadata value is invalid"):
        normalize_metadata({"not_finite": float("inf")})


@pytest.mark.unit
def test_technical_audit_record_rejects_invalid_identifier() -> None:
    with pytest.raises(ValidationError, match="Audit record identifier is invalid"):
        TechnicalAuditRecord(
            record_id="not-an-entity-id",
            occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            category=AuditCategory.INFRASTRUCTURE,
            origin="database",
            operation="initialize",
            level=AuditLevel.INFO,
            message="Database initialized",
            metadata={},
        )


@pytest.mark.unit
def test_technical_audit_repository_validates_limit() -> None:
    repository = TechnicalAuditRepository(
        session_factory=FailingSessionFactory(),
        logger=logging.getLogger("friday.tests.audit"),
    )

    with pytest.raises(ValidationError, match="Audit record limit is invalid"):
        repository.list_records(limit=0)


@pytest.mark.unit
def test_technical_audit_repository_wraps_sqlalchemy_errors() -> None:
    repository = TechnicalAuditRepository(
        session_factory=FailingSessionFactory(),
        logger=logging.getLogger("friday.tests.audit"),
    )

    with pytest.raises(PersistenceError) as add_error:
        repository.add(_record())
    assert isinstance(add_error.value.cause, SQLAlchemyError)

    with pytest.raises(PersistenceError) as list_error:
        repository.list_records()
    assert isinstance(list_error.value.cause, SQLAlchemyError)


@pytest.mark.unit
def test_technical_audit_service_records_with_logger(
    temporary_directory: Path,
) -> None:
    settings = _settings(temporary_directory)
    logger_factory = configure_logging(settings)
    repository = RecordingRepository()
    service = TechnicalAuditService(
        repository=repository,
        clock=_clock(),
        id_generator=_id_generator(),
        logger=logger_factory.get_logger("audit"),
    )

    record = service.record(
        category=AuditCategory.PERSISTENCE,
        origin="unit_of_work",
        operation="commit",
        level=AuditLevel.INFO,
        message="Unit of Work committed",
    )

    assert repository.records == [record]
    assert "Technical audit record stored" in log_file_path(settings).read_text(
        encoding="utf-8"
    )


@pytest.mark.unit
def test_technical_audit_service_try_record_logs_failure(
    temporary_directory: Path,
) -> None:
    settings = _settings(temporary_directory)
    logger_factory = configure_logging(settings)
    service = TechnicalAuditService(
        repository=FailingRepository(),
        clock=_clock(),
        id_generator=_id_generator(),
        logger=logger_factory.get_logger("audit"),
    )

    recorded = service.try_record(
        category=AuditCategory.PERSISTENCE,
        origin="repository",
        operation="insert",
        level=AuditLevel.ERROR,
        message="Audit insert failed",
    )

    assert recorded is False
    assert "Technical audit record failed" in log_file_path(settings).read_text(
        encoding="utf-8"
    )


@pytest.mark.unit
def test_technical_audit_event_is_serializable() -> None:
    event = TechnicalAuditEvent.create(
        clock=_clock(),
        id_generator=_id_generator(),
        category=AuditCategory.EVENT_BUS,
        origin="events",
        operation="publish",
        level=AuditLevel.INFO,
        message="Event published",
        metadata={"handlers": 1},
    )

    assert event.name == "infrastructure.audit.technical_event"
    assert event.to_dict()["metadata"] == {"handlers": 1}


@pytest.mark.unit
def test_technical_audit_event_handler_uses_safe_recording() -> None:
    service = TechnicalAuditService(
        repository=FailingRepository(),
        clock=_clock(),
        id_generator=_id_generator(),
        logger=logging.getLogger("friday.tests.audit"),
    )
    handler = TechnicalAuditEventHandler(service)
    event = TechnicalAuditEvent.create(
        clock=_clock(),
        id_generator=_id_generator(),
        category=AuditCategory.EVENT_BUS,
        origin="events",
        operation="publish",
        level=AuditLevel.INFO,
        message="Event published",
    )

    handler.handle(event)


@pytest.mark.unit
def test_audit_services_are_registered_in_container(
    temporary_directory: Path,
) -> None:
    container = build_container(_settings(temporary_directory))

    assert isinstance(
        container.resolve(TechnicalAuditRepository), TechnicalAuditRepository
    )
    assert isinstance(container.resolve(TechnicalAuditService), TechnicalAuditService)
    assert isinstance(
        container.resolve(TechnicalAuditEventHandler), TechnicalAuditEventHandler
    )
