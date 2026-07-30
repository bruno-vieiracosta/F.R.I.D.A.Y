from __future__ import annotations

import logging as standard_logging
from dataclasses import dataclass

from sqlalchemy.engine import Engine

from friday.bootstrap.config import ApplicationSettings
from friday.infrastructure.persistence.configuration import (
    DatabaseConfiguration,
    resolve_database_configuration,
)
from friday.infrastructure.persistence.engine import SqlAlchemyEngineFactory
from friday.infrastructure.persistence.session import SqlAlchemySessionFactory
from friday.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


@dataclass(frozen=True, slots=True)
class DatabaseInfrastructure:
    configuration: DatabaseConfiguration
    engine: Engine
    session_factory: SqlAlchemySessionFactory

    def create_unit_of_work(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self.session_factory)


def initialize_database(
    settings: ApplicationSettings,
    logger: standard_logging.Logger,
) -> DatabaseInfrastructure:
    configuration = resolve_database_configuration(settings)
    engine_factory = SqlAlchemyEngineFactory(
        configuration=configuration,
        logger=logger,
    )
    engine = engine_factory.create()
    session_factory = SqlAlchemySessionFactory.from_engine(engine)

    logger.info("Database infrastructure initialized")
    return DatabaseInfrastructure(
        configuration=configuration,
        engine=engine,
        session_factory=session_factory,
    )
