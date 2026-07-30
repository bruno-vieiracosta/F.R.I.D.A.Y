import logging
import sys
from pathlib import Path
from types import TracebackType

import pytest

from friday.bootstrap.config import ApplicationSettings, LogLevel, load_settings
from friday.bootstrap.logging import (
    LoggerFactory,
    SensitiveDataFilter,
    configure_logging,
    install_exception_hook,
    log_file_path,
    mask_sensitive_data,
)


def _settings(temporary_directory: Path, **overrides: str) -> ApplicationSettings:
    values = {
        "FRIDAY_LOGS_DIR": str(temporary_directory / "logs"),
        "FRIDAY_LOG_MAX_BYTES": "1024",
        "FRIDAY_LOG_BACKUP_COUNT": "2",
        **overrides,
    }
    return load_settings(values)


@pytest.fixture(autouse=True)
def reset_friday_logger() -> None:
    logger = logging.getLogger("friday")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


@pytest.mark.unit
def test_configure_logging_returns_factory(
    temporary_directory: Path,
) -> None:
    factory = configure_logging(_settings(temporary_directory))

    assert isinstance(factory, LoggerFactory)


@pytest.mark.unit
def test_logger_factory_reuses_logger_instances(
    temporary_directory: Path,
) -> None:
    factory = configure_logging(_settings(temporary_directory))

    assert factory.get_logger("unit") is factory.get_logger("unit")


@pytest.mark.unit
def test_configure_logging_does_not_duplicate_handlers(
    temporary_directory: Path,
) -> None:
    settings = _settings(temporary_directory)
    configure_logging(settings)
    configure_logging(settings)

    logger = logging.getLogger("friday")

    assert len(logger.handlers) == 2


@pytest.mark.unit
def test_log_level_comes_from_settings(temporary_directory: Path) -> None:
    settings = _settings(temporary_directory, FRIDAY_LOG_LEVEL="ERROR")

    configure_logging(settings)

    assert logging.getLogger("friday").level == logging.ERROR
    assert settings.log_level is LogLevel.ERROR


@pytest.mark.unit
def test_console_handler_writes_structured_log(
    capsys: pytest.CaptureFixture[str],
    temporary_directory: Path,
) -> None:
    factory = configure_logging(_settings(temporary_directory))

    factory.get_logger("console").warning("console message")

    output = capsys.readouterr().err
    assert "WARNING" in output
    assert "test_logging" in output
    assert "friday.console" in output
    assert "console message" in output


@pytest.mark.unit
def test_file_handler_writes_log_file(temporary_directory: Path) -> None:
    settings = _settings(temporary_directory)
    factory = configure_logging(settings)

    factory.get_logger("file").info("file message")

    contents = log_file_path(settings).read_text(encoding="utf-8")
    assert "INFO" in contents
    assert "file message" in contents


@pytest.mark.unit
def test_log_directory_is_created(temporary_directory: Path) -> None:
    settings = _settings(temporary_directory)

    configure_logging(settings)

    assert settings.directories.logs.is_dir()


@pytest.mark.unit
def test_rotation_uses_configured_backups(temporary_directory: Path) -> None:
    settings = _settings(
        temporary_directory,
        FRIDAY_LOG_MAX_BYTES="80",
        FRIDAY_LOG_BACKUP_COUNT="1",
    )
    factory = configure_logging(settings)
    logger = factory.get_logger("rotation")

    for index in range(20):
        logger.info("rotation message %s token=secret-%s", index, index)

    assert log_file_path(settings).is_file()
    assert log_file_path(settings).with_name("friday.log.1").is_file()


@pytest.mark.unit
def test_sensitive_data_is_masked() -> None:
    masked = mask_sensitive_data(
        "password=abc token: def api_key=ghi secret=jkl credential=mno"
    )

    assert "abc" not in masked
    assert "def" not in masked
    assert "ghi" not in masked
    assert "jkl" not in masked
    assert "mno" not in masked
    assert masked.count("***") == 5


@pytest.mark.unit
def test_sensitive_data_filter_masks_record_message() -> None:
    record = logging.LogRecord(
        name="friday.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="token=%s",
        args=("abc",),
        exc_info=None,
    )

    assert SensitiveDataFilter().filter(record) is True
    assert record.getMessage() == "token=***"


@pytest.mark.unit
def test_exception_hook_logs_unhandled_exception(
    temporary_directory: Path,
) -> None:
    settings = _settings(temporary_directory)
    factory = configure_logging(settings)
    previous_hook = sys.excepthook

    try:
        install_exception_hook(factory)
        try:
            raise RuntimeError("secret=hidden")
        except RuntimeError as error:
            exc_type = type(error)
            traceback: TracebackType | None = error.__traceback__
            sys.excepthook(exc_type, error, traceback)
    finally:
        sys.excepthook = previous_hook

    contents = log_file_path(settings).read_text(encoding="utf-8")
    assert "Unhandled exception" in contents
    assert "RuntimeError" in contents
    assert "hidden" not in contents
    assert "secret=***" in contents


@pytest.mark.unit
def test_file_logging_failure_does_not_interrupt_execution(
    monkeypatch: pytest.MonkeyPatch,
    temporary_directory: Path,
) -> None:
    def raise_os_error(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk unavailable")

    monkeypatch.setattr(
        "friday.bootstrap.logging.RotatingFileHandler",
        raise_os_error,
    )
    settings = _settings(temporary_directory)

    factory = configure_logging(settings)

    assert factory.get_logger("fallback").name == "friday.fallback"
    assert len(logging.getLogger("friday").handlers) == 1
