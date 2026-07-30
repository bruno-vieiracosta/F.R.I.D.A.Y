from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import URL

from friday.bootstrap.config import ApplicationSettings
from friday.shared.errors import InfrastructureError


@dataclass(frozen=True, slots=True)
class DatabaseConfiguration:
    path: Path
    url: str


def resolve_database_configuration(
    settings: ApplicationSettings,
) -> DatabaseConfiguration:
    database_path = settings.database_path.expanduser()
    return DatabaseConfiguration(
        path=database_path,
        url=str(URL.create("sqlite+pysqlite", database=str(database_path))),
    )


def ensure_database_directory(configuration: DatabaseConfiguration) -> None:
    try:
        configuration.path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise InfrastructureError(
            "Database directory could not be created.",
            technical_message="SQLite database parent directory creation failed.",
            cause=error,
            metadata={"path": str(configuration.path.parent)},
        ) from error
