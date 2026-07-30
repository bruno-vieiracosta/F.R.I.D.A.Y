from __future__ import annotations

import logging as standard_logging
from collections.abc import Mapping
from dataclasses import dataclass

from friday.infrastructure.audit.models import (
    AuditCategory,
    AuditLevel,
    TechnicalAuditRecord,
)
from friday.infrastructure.audit.repository import TechnicalAuditRepository
from friday.shared.clock import Clock
from friday.shared.errors import FridayError
from friday.shared.identifiers import IdGenerator


@dataclass(frozen=True, slots=True)
class TechnicalAuditService:
    repository: TechnicalAuditRepository
    clock: Clock
    id_generator: IdGenerator
    logger: standard_logging.Logger

    def record(
        self,
        *,
        category: AuditCategory,
        origin: str,
        operation: str,
        level: AuditLevel,
        message: str,
        metadata: Mapping[str, object] | None = None,
    ) -> TechnicalAuditRecord:
        record = TechnicalAuditRecord.create(
            clock=self.clock,
            id_generator=self.id_generator,
            category=category,
            origin=origin,
            operation=operation,
            level=level,
            message=message,
            metadata=metadata,
        )
        self.repository.add(record)
        self.logger.info(
            "Technical audit record stored",
            extra={"technical_audit": record.to_dict()},
        )
        return record

    def try_record(
        self,
        *,
        category: AuditCategory,
        origin: str,
        operation: str,
        level: AuditLevel,
        message: str,
        metadata: Mapping[str, object] | None = None,
    ) -> bool:
        try:
            self.record(
                category=category,
                origin=origin,
                operation=operation,
                level=level,
                message=message,
                metadata=metadata,
            )
        except FridayError as error:
            self.logger.error(
                "Technical audit record failed",
                extra={"technical_audit_error": error.to_log_dict()},
                exc_info=(type(error), error, error.__traceback__),
            )
            return False
        return True
