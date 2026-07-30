from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from friday import __version__
from friday.bootstrap.config import (
    APPLICATION_NAME,
    ApplicationSettings,
    ConfigurationError,
    Environment,
    FeatureFlags,
    LogLevel,
    load_settings,
)


@pytest.mark.unit
def test_default_settings_are_loaded() -> None:
    settings = load_settings({})

    assert settings.name == APPLICATION_NAME
    assert settings.version == __version__
    assert settings.environment is Environment.DEVELOPMENT
    assert settings.debug is False
    assert settings.log_level is LogLevel.INFO
    assert settings.feature_flags == FeatureFlags()


@pytest.mark.unit
def test_settings_are_immutable() -> None:
    settings = load_settings({})

    with pytest.raises(FrozenInstanceError):
        settings.debug = True


@pytest.mark.unit
def test_valid_environments_are_supported() -> None:
    assert load_settings({"FRIDAY_ENVIRONMENT": "development"}).environment is (
        Environment.DEVELOPMENT
    )
    assert load_settings({"FRIDAY_ENVIRONMENT": "testing"}).environment is (
        Environment.TESTING
    )
    assert load_settings({"FRIDAY_ENVIRONMENT": "production"}).environment is (
        Environment.PRODUCTION
    )


@pytest.mark.unit
def test_invalid_environment_raises_clear_error() -> None:
    with pytest.raises(
        ConfigurationError,
        match="FRIDAY_ENVIRONMENT must be one of",
    ):
        load_settings({"FRIDAY_ENVIRONMENT": "local"})


@pytest.mark.unit
def test_environment_values_are_normalized() -> None:
    settings = load_settings({"FRIDAY_ENVIRONMENT": " TESTING "})

    assert settings.environment is Environment.TESTING


@pytest.mark.unit
def test_environment_variables_override_defaults(temporary_directory: Path) -> None:
    settings = load_settings(
        {
            "FRIDAY_ENVIRONMENT": "testing",
            "FRIDAY_DEBUG": "true",
            "FRIDAY_BASE_DIR": str(temporary_directory / "base"),
            "FRIDAY_LOG_LEVEL": "debug",
        }
    )

    assert settings.environment is Environment.TESTING
    assert settings.debug is True
    assert settings.directories.data == temporary_directory / "base" / "data"
    assert settings.log_level is LogLevel.DEBUG


@pytest.mark.unit
def test_settings_can_be_loaded_from_process_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FRIDAY_ENVIRONMENT", "testing")
    monkeypatch.setenv("FRIDAY_LOG_LEVEL", "warning")

    settings = load_settings()

    assert settings.environment is Environment.TESTING
    assert settings.log_level is LogLevel.WARNING


@pytest.mark.unit
def test_debug_mode_is_rejected_in_production() -> None:
    with pytest.raises(
        ConfigurationError,
        match="FRIDAY_DEBUG must be false in production",
    ):
        load_settings({"FRIDAY_ENVIRONMENT": "production", "FRIDAY_DEBUG": "true"})


@pytest.mark.unit
def test_directories_can_be_configured(temporary_directory: Path) -> None:
    settings = load_settings(
        {
            "FRIDAY_DATA_DIR": str(temporary_directory / "data"),
            "FRIDAY_LOGS_DIR": str(temporary_directory / "logs"),
            "FRIDAY_BACKUPS_DIR": str(temporary_directory / "backups"),
            "FRIDAY_TEMP_DIR": str(temporary_directory / "temp"),
        }
    )

    assert settings.directories.data == temporary_directory / "data"
    assert settings.directories.logs == temporary_directory / "logs"
    assert settings.directories.backups == temporary_directory / "backups"
    assert settings.directories.temporary == temporary_directory / "temp"


@pytest.mark.unit
def test_directory_path_cannot_point_to_existing_file(
    temporary_directory: Path,
) -> None:
    file_path = temporary_directory / "data-file"
    file_path.write_text("not a directory", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="FRIDAY_DATA_DIR"):
        load_settings({"FRIDAY_DATA_DIR": str(file_path)})


@pytest.mark.unit
def test_database_path_can_be_configured(temporary_directory: Path) -> None:
    database_path = temporary_directory / "database.sqlite3"

    settings = load_settings({"FRIDAY_DATABASE_PATH": str(database_path)})

    assert settings.database_path == database_path


@pytest.mark.unit
def test_database_path_cannot_point_to_directory(temporary_directory: Path) -> None:
    with pytest.raises(ConfigurationError, match="FRIDAY_DATABASE_PATH"):
        load_settings({"FRIDAY_DATABASE_PATH": str(temporary_directory)})


@pytest.mark.unit
def test_log_level_must_be_valid() -> None:
    with pytest.raises(ConfigurationError, match="FRIDAY_LOG_LEVEL must be one of"):
        load_settings({"FRIDAY_LOG_LEVEL": "verbose"})


@pytest.mark.unit
def test_logging_rotation_settings_are_loaded() -> None:
    settings = load_settings(
        {
            "FRIDAY_LOG_FILE_NAME": "technical.log",
            "FRIDAY_LOG_MAX_BYTES": "2048",
            "FRIDAY_LOG_BACKUP_COUNT": "7",
        }
    )

    assert settings.logging.file_name == "technical.log"
    assert settings.logging.max_bytes == 2048
    assert settings.logging.backup_count == 7


@pytest.mark.unit
def test_logging_rotation_values_must_be_valid() -> None:
    with pytest.raises(ConfigurationError, match="FRIDAY_LOG_MAX_BYTES"):
        load_settings({"FRIDAY_LOG_MAX_BYTES": "0"})

    with pytest.raises(ConfigurationError, match="FRIDAY_LOG_BACKUP_COUNT"):
        load_settings({"FRIDAY_LOG_BACKUP_COUNT": "-1"})


@pytest.mark.unit
def test_feature_flags_are_typed_and_loaded_from_environment() -> None:
    settings = load_settings(
        {
            "FRIDAY_FEATURE_DESKTOP": "true",
            "FRIDAY_FEATURE_AI": "1",
            "FRIDAY_FEATURE_INTEGRATIONS": "yes",
            "FRIDAY_FEATURE_BACKUPS": "on",
        }
    )

    assert settings.feature_flags == FeatureFlags(
        desktop=True,
        ai=True,
        integrations=True,
        backups=True,
    )


@pytest.mark.unit
def test_invalid_boolean_value_raises_clear_error() -> None:
    with pytest.raises(ConfigurationError, match="FRIDAY_FEATURE_AI must be"):
        load_settings({"FRIDAY_FEATURE_AI": "maybe"})


@pytest.mark.unit
def test_loaded_settings_have_expected_type() -> None:
    assert isinstance(load_settings({}), ApplicationSettings)
