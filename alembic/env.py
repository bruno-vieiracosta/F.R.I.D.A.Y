from __future__ import annotations

from alembic import context
from sqlalchemy import MetaData, Table, func, inspect, select
from sqlalchemy.engine import Connection

from friday.bootstrap.config import load_settings
from friday.bootstrap.logging import configure_logging
from friday.infrastructure.persistence.configuration import (
    resolve_database_configuration,
)
from friday.infrastructure.persistence.engine import SqlAlchemyEngineFactory
from friday.infrastructure.persistence.schema import schema_metadata

config = context.config

configured_settings = config.attributes.get("application_settings")
if configured_settings is None:
    settings = load_settings()
else:
    settings = configured_settings
logger_factory = configure_logging(settings)
logger = logger_factory.get_logger("migrations")
database_configuration = resolve_database_configuration(settings)
target_metadata = schema_metadata


def drop_empty_version_table(connection: Connection) -> None:
    inspector = inspect(connection)
    if "alembic_version" not in inspector.get_table_names():
        return

    version_table = Table(
        "alembic_version",
        MetaData(),
        autoload_with=connection,
    )
    version_count = connection.execute(
        select(func.count()).select_from(version_table),
    ).scalar_one()
    if version_count == 0:
        version_table.drop(connection)


def run_migrations_offline() -> None:
    logger.info("Offline database migration started")
    context.configure(
        url=database_configuration.url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()
    logger.info("Offline database migration completed")


def run_migrations_online() -> None:
    logger.info("Online database migration started")
    engine = SqlAlchemyEngineFactory(
        configuration=database_configuration,
        logger=logger,
    ).create()

    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
            )

            with context.begin_transaction():
                context.run_migrations()
                drop_empty_version_table(connection)
    finally:
        engine.dispose()
    logger.info("Online database migration completed")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
