from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from friday import __version__

APPLICATION_NAME = "F.R.I.D.A.Y."


class ConfigurationError(ValueError):
    pass


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class LoggingSettings:
    level: LogLevel
    file_name: str
    max_bytes: int
    backup_count: int


@dataclass(frozen=True, slots=True)
class FeatureFlags:
    desktop: bool = False
    ai: bool = False
    integrations: bool = False
    backups: bool = False


@dataclass(frozen=True, slots=True)
class DirectorySettings:
    data: Path
    logs: Path
    backups: Path
    temporary: Path


@dataclass(frozen=True, slots=True)
class SecretSettings:
    file_path: Path
    environment_prefix: str


@dataclass(frozen=True, slots=True)
class ApplicationSettings:
    name: str
    version: str
    environment: Environment
    debug: bool
    directories: DirectorySettings
    logging: LoggingSettings
    database_path: Path
    secrets: SecretSettings
    feature_flags: FeatureFlags

    @property
    def log_level(self) -> LogLevel:
        return self.logging.level


def load_settings(environ: Mapping[str, str] | None = None) -> ApplicationSettings:
    values = dict(os.environ if environ is None else environ)
    environment = _environment_from(values)
    debug = _bool_from(values, "FRIDAY_DEBUG", default=False)
    base_dir = _base_dir_from(values)
    directories = _directories_from(values, base_dir)
    settings = ApplicationSettings(
        name=APPLICATION_NAME,
        version=__version__,
        environment=environment,
        debug=debug,
        directories=directories,
        logging=_logging_settings_from(values),
        database_path=_path_from(
            values,
            "FRIDAY_DATABASE_PATH",
            directories.data / "friday.sqlite3",
        ),
        secrets=_secret_settings_from(values, base_dir),
        feature_flags=_feature_flags_from(values),
    )
    _validate_settings(settings)
    return settings


def _environment_from(values: Mapping[str, str]) -> Environment:
    raw_environment = values.get("FRIDAY_ENVIRONMENT", Environment.DEVELOPMENT.value)
    environment = raw_environment.strip().lower()
    if not environment:
        raise ConfigurationError("FRIDAY_ENVIRONMENT must not be empty.")

    try:
        return Environment(environment)
    except ValueError as error:
        allowed = ", ".join(item.value for item in Environment)
        raise ConfigurationError(
            f"FRIDAY_ENVIRONMENT must be one of: {allowed}."
        ) from error


def _log_level_from(values: Mapping[str, str]) -> LogLevel:
    raw_level = values.get("FRIDAY_LOG_LEVEL", LogLevel.INFO.value)
    level = raw_level.strip().upper()
    if not level:
        raise ConfigurationError("FRIDAY_LOG_LEVEL must not be empty.")

    try:
        return LogLevel(level)
    except ValueError as error:
        allowed = ", ".join(item.value for item in LogLevel)
        raise ConfigurationError(
            f"FRIDAY_LOG_LEVEL must be one of: {allowed}."
        ) from error


def _feature_flags_from(values: Mapping[str, str]) -> FeatureFlags:
    return FeatureFlags(
        desktop=_bool_from(values, "FRIDAY_FEATURE_DESKTOP", default=False),
        ai=_bool_from(values, "FRIDAY_FEATURE_AI", default=False),
        integrations=_bool_from(
            values,
            "FRIDAY_FEATURE_INTEGRATIONS",
            default=False,
        ),
        backups=_bool_from(values, "FRIDAY_FEATURE_BACKUPS", default=False),
    )


def _logging_settings_from(values: Mapping[str, str]) -> LoggingSettings:
    return LoggingSettings(
        level=_log_level_from(values),
        file_name=_log_file_name_from(values),
        max_bytes=_int_from(values, "FRIDAY_LOG_MAX_BYTES", default=1_048_576),
        backup_count=_int_from(values, "FRIDAY_LOG_BACKUP_COUNT", default=5),
    )


def _log_file_name_from(values: Mapping[str, str]) -> str:
    file_name = values.get("FRIDAY_LOG_FILE_NAME", "friday.log").strip()
    if not file_name:
        raise ConfigurationError("FRIDAY_LOG_FILE_NAME must not be empty.")

    path = Path(file_name)
    if path.name != file_name:
        raise ConfigurationError("FRIDAY_LOG_FILE_NAME must be a file name only.")

    return file_name


def _base_dir_from(values: Mapping[str, str]) -> Path:
    return _path_from(values, "FRIDAY_BASE_DIR", Path.home() / ".friday")


def _directories_from(values: Mapping[str, str], base_dir: Path) -> DirectorySettings:
    return DirectorySettings(
        data=_path_from(values, "FRIDAY_DATA_DIR", base_dir / "data"),
        logs=_path_from(values, "FRIDAY_LOGS_DIR", base_dir / "logs"),
        backups=_path_from(values, "FRIDAY_BACKUPS_DIR", base_dir / "backups"),
        temporary=_path_from(values, "FRIDAY_TEMP_DIR", base_dir / "temp"),
    )


def _secret_settings_from(values: Mapping[str, str], base_dir: Path) -> SecretSettings:
    prefix = values.get("FRIDAY_SECRET_ENV_PREFIX", "FRIDAY_SECRET_").strip()
    if not prefix:
        raise ConfigurationError("FRIDAY_SECRET_ENV_PREFIX must not be empty.")

    if any(character.isspace() for character in prefix):
        raise ConfigurationError("FRIDAY_SECRET_ENV_PREFIX must not contain spaces.")

    if "\x00" in prefix:
        raise ConfigurationError(
            "FRIDAY_SECRET_ENV_PREFIX must not contain null bytes."
        )

    return SecretSettings(
        file_path=_path_from(
            values,
            "FRIDAY_SECRETS_FILE",
            base_dir / "config" / "secrets.json",
        ),
        environment_prefix=prefix,
    )


def _path_from(values: Mapping[str, str], name: str, default: Path) -> Path:
    raw_path = values.get(name)
    if raw_path is None:
        return default.expanduser()

    path = raw_path.strip()
    if not path:
        raise ConfigurationError(f"{name} must not be empty.")

    if "\x00" in path:
        raise ConfigurationError(f"{name} must not contain null bytes.")

    return Path(path).expanduser()


def _bool_from(values: Mapping[str, str], name: str, *, default: bool) -> bool:
    raw_value = values.get(name)
    if raw_value is None:
        return default

    value = raw_value.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False

    raise ConfigurationError(
        f"{name} must be a boolean value: true, false, 1, 0, yes, no, on or off."
    )


def _int_from(values: Mapping[str, str], name: str, *, default: int) -> int:
    raw_value = values.get(name)
    if raw_value is None:
        return default

    value = raw_value.strip()
    if not value:
        raise ConfigurationError(f"{name} must not be empty.")

    try:
        return int(value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be an integer.") from error


def _validate_settings(settings: ApplicationSettings) -> None:
    if not settings.name.strip():
        raise ConfigurationError("Application name must not be empty.")

    if not settings.version.strip():
        raise ConfigurationError("Application version must not be empty.")

    if settings.environment is Environment.PRODUCTION and settings.debug:
        raise ConfigurationError("FRIDAY_DEBUG must be false in production.")

    for name, path in {
        "FRIDAY_DATA_DIR": settings.directories.data,
        "FRIDAY_LOGS_DIR": settings.directories.logs,
        "FRIDAY_BACKUPS_DIR": settings.directories.backups,
        "FRIDAY_TEMP_DIR": settings.directories.temporary,
    }.items():
        _validate_directory_path(name, path)

    _validate_database_path(settings.database_path)
    _validate_logging_settings(settings.logging)
    _validate_secret_settings(settings.secrets)


def _validate_directory_path(name: str, path: Path) -> None:
    if path.exists() and not path.is_dir():
        raise ConfigurationError(f"{name} must point to a directory.")


def _validate_database_path(path: Path) -> None:
    if path.exists() and path.is_dir():
        raise ConfigurationError("FRIDAY_DATABASE_PATH must point to a file.")

    parent = path.parent
    if parent.exists() and not parent.is_dir():
        raise ConfigurationError(
            "FRIDAY_DATABASE_PATH parent must point to a directory."
        )


def _validate_logging_settings(settings: LoggingSettings) -> None:
    if settings.max_bytes <= 0:
        raise ConfigurationError("FRIDAY_LOG_MAX_BYTES must be greater than zero.")

    if settings.backup_count < 0:
        raise ConfigurationError("FRIDAY_LOG_BACKUP_COUNT must be zero or greater.")


def _validate_secret_settings(settings: SecretSettings) -> None:
    if settings.file_path.exists() and settings.file_path.is_dir():
        raise ConfigurationError("FRIDAY_SECRETS_FILE must point to a file.")

    parent = settings.file_path.parent
    if parent.exists() and not parent.is_dir():
        raise ConfigurationError(
            "FRIDAY_SECRETS_FILE parent must point to a directory."
        )
