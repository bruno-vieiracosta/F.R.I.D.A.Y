from __future__ import annotations

import logging as standard_logging
from dataclasses import dataclass, field

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from friday.infrastructure.persistence.configuration import (
    DatabaseConfiguration,
    ensure_database_directory,
)
from friday.shared.errors import InfrastructureError


@dataclass(slots=True)
class SqlAlchemyEngineFactory:
    configuration: DatabaseConfiguration
    logger: standard_logging.Logger
    _engine: Engine | None = field(default=None, init=False)

    def create(self) -> Engine:
        if self._engine is not None:
            return self._engine

        try:
            ensure_database_directory(self.configuration)
            self._engine = create_engine(
                self.configuration.url,
                future=True,
            )
        except SQLAlchemyError as error:
            self.logger.exception("SQLAlchemy engine creation failed")
            raise InfrastructureError(
                "Database engine could not be created.",
                technical_message="SQLAlchemy create_engine failed.",
                cause=error,
                metadata={"database": str(self.configuration.path)},
            ) from error

        self.logger.info("Database engine created")
        return self._engine
