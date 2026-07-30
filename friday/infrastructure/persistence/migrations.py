from __future__ import annotations

import logging as standard_logging
from pathlib import Path

from alembic.config import Config
from alembic.util import CommandError

from alembic import command
from friday.bootstrap.config import ApplicationSettings
from friday.infrastructure.persistence.configuration import (
    resolve_database_configuration,
)
from friday.shared.errors import PersistenceError

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_INI_PATH = PROJECT_ROOT / "alembic.ini"
ALEMBIC_SCRIPT_LOCATION = PROJECT_ROOT / "alembic"


def create_alembic_config(settings: ApplicationSettings) -> Config:
    configuration = resolve_database_configuration(settings)
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(ALEMBIC_SCRIPT_LOCATION))
    config.set_main_option("sqlalchemy.url", configuration.url)
    config.attributes["application_settings"] = settings
    return config


def upgrade_database(
    settings: ApplicationSettings,
    logger: standard_logging.Logger,
    revision: str = "head",
) -> None:
    logger.info("Database migration upgrade started")
    try:
        command.upgrade(create_alembic_config(settings), revision)
    except CommandError as error:
        logger.exception("Database migration upgrade failed")
        raise PersistenceError(
            "Database migration upgrade failed.",
            technical_message="Alembic upgrade command failed.",
            cause=error,
            metadata={"revision": revision},
        ) from error
    logger.info("Database migration upgrade completed")


def downgrade_database(
    settings: ApplicationSettings,
    logger: standard_logging.Logger,
    revision: str = "base",
) -> None:
    logger.info("Database migration downgrade started")
    try:
        command.downgrade(create_alembic_config(settings), revision)
    except CommandError as error:
        logger.exception("Database migration downgrade failed")
        raise PersistenceError(
            "Database migration downgrade failed.",
            technical_message="Alembic downgrade command failed.",
            cause=error,
            metadata={"revision": revision},
        ) from error
    logger.info("Database migration downgrade completed")
