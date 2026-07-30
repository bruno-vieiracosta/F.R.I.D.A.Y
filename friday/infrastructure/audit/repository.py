from __future__ import annotations

import logging as standard_logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import insert, select
from sqlalchemy.engine.row import RowMapping
from sqlalchemy.exc import SQLAlchemyError

from friday.infrastructure.audit.models import (
    AuditCategory,
    AuditLevel,
    TechnicalAuditRecord,
)
from friday.infrastructure.audit.serializers import (
    deserialize_metadata,
    serialize_metadata,
)
from friday.infrastructure.persistence.schema import technical_audit_records
from friday.infrastructure.persistence.session import SqlAlchemySessionFactory
from friday.shared.clock import normalize_to_utc
from friday.shared.errors import PersistenceError, ValidationError
from friday.shared.identifiers import EntityId


@dataclass(frozen=True, slots=True)
class TechnicalAuditRepository:
    session_factory: SqlAlchemySessionFactory
    logger: standard_logging.Logger

    def add(self, record: TechnicalAuditRecord) -> None:
        values = {
            "id": str(record.record_id),
            "occurred_at": record.occurred_at,
            "category": record.category.value,
            "origin": record.origin,
            "operation": record.operation,
            "level": record.level.value,
            "message": record.message,
            "metadata_json": serialize_metadata(record.metadata),
        }

        try:
            with self.session_factory.create() as session:
                session.execute(insert(technical_audit_records).values(**values))
                session.commit()
        except SQLAlchemyError as error:
            self.logger.exception("Technical audit record could not be stored")
            raise PersistenceError(
                "Technical audit record could not be stored.",
                technical_message="SQLAlchemy failed while storing audit record.",
                cause=error,
                metadata={
                    "audit_record_id": str(record.record_id),
                    "operation": record.operation,
                },
            ) from error

    def list_records(
        self,
        *,
        limit: int | None = None,
    ) -> tuple[TechnicalAuditRecord, ...]:
        if limit is not None and limit < 1:
            raise ValidationError(
                "Audit record limit is invalid.",
                technical_message="Audit record limit must be greater than zero.",
            )

        statement = select(technical_audit_records).order_by(
            technical_audit_records.c.occurred_at.asc(),
            technical_audit_records.c.id.asc(),
        )
        if limit is not None:
            statement = statement.limit(limit)

        try:
            with self.session_factory.create() as session:
                rows = session.execute(statement).mappings().all()
                return tuple(_record_from_mapping(row) for row in rows)
        except SQLAlchemyError as error:
            self.logger.exception("Technical audit records could not be loaded")
            raise PersistenceError(
                "Technical audit records could not be loaded.",
                technical_message="SQLAlchemy failed while loading audit records.",
                cause=error,
            ) from error


def _record_from_mapping(row: RowMapping) -> TechnicalAuditRecord:
    return TechnicalAuditRecord(
        record_id=EntityId.from_string(_text(row, "id")),
        occurred_at=_datetime(row, "occurred_at"),
        category=AuditCategory(_text(row, "category")),
        origin=_text(row, "origin"),
        operation=_text(row, "operation"),
        level=AuditLevel(_text(row, "level")),
        message=_text(row, "message"),
        metadata=deserialize_metadata(_text(row, "metadata_json")),
    )


def _text(row: RowMapping, key: str) -> str:
    value = row[key]
    if not isinstance(value, str):
        raise PersistenceError(
            "Technical audit record is invalid.",
            technical_message="Audit database row contains a non-text value.",
            metadata={"field": key},
        )
    return value


def _datetime(row: RowMapping, key: str) -> datetime:
    value = row[key]
    if not isinstance(value, datetime):
        raise PersistenceError(
            "Technical audit record is invalid.",
            technical_message="Audit database row contains a non-datetime value.",
            metadata={"field": key},
        )

    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)

    return normalize_to_utc(value)
