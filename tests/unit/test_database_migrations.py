import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData

from friday.bootstrap.config import ApplicationSettings, load_settings
from friday.infrastructure.persistence import (
    application_metadata,
    create_alembic_config,
    schema_metadata,
)

REVISION_PATH = Path("alembic/versions/0001_initial_revision.py")


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


def _load_revision_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "initial_revision",
        REVISION_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.unit
def test_alembic_config_uses_application_settings(
    temporary_directory: Path,
) -> None:
    settings = _settings(temporary_directory)

    config = create_alembic_config(settings)

    assert isinstance(config, Config)
    assert config.get_main_option("script_location").endswith("alembic")
    assert config.get_main_option("sqlalchemy.url").startswith("sqlite+pysqlite:///")
    assert str(settings.database_path) in config.get_main_option("sqlalchemy.url")


@pytest.mark.unit
def test_official_metadata_contains_only_technical_table() -> None:
    assert isinstance(schema_metadata, MetaData)
    assert schema_metadata is application_metadata.metadata
    assert set(schema_metadata.tables) == {"application_metadata"}


@pytest.mark.unit
def test_initial_revision_exists_and_is_registered() -> None:
    script_directory = ScriptDirectory.from_config(
        create_alembic_config(load_settings({}))
    )

    revision = script_directory.get_revision("head")

    assert revision is not None
    assert revision.revision == "0001_initial_revision"
    assert revision.down_revision is None


@pytest.mark.unit
def test_initial_revision_exposes_upgrade_and_downgrade() -> None:
    module = _load_revision_module()

    assert module.revision == "0001_initial_revision"
    assert module.down_revision is None
    assert callable(module.upgrade)
    assert callable(module.downgrade)
