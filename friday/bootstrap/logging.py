from __future__ import annotations

import logging as standard_logging
import re
import sys
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType

from friday.bootstrap.config import ApplicationSettings

LOGGER_NAME = "friday"
LOG_FORMAT = "%(asctime)s %(levelname)s %(module)s %(name)s %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
MASK = "***"
SENSITIVE_PATTERN = re.compile(
    r"(?i)\b(password|passwd|pwd|token|api[_-]?key|secret|credential|credentials)"
    r"\b(\s*[:=]\s*)([^\s,;]+)"
)
BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]+")


def mask_sensitive_data(value: object) -> str:
    text = str(value)
    text = SENSITIVE_PATTERN.sub(_mask_key_value, text)
    return BEARER_PATTERN.sub(f"Bearer {MASK}", text)


def _mask_key_value(match: re.Match[str]) -> str:
    return f"{match.group(1)}{match.group(2)}{MASK}"


class SensitiveDataFilter(standard_logging.Filter):
    def filter(self, record: standard_logging.LogRecord) -> bool:
        record.msg = mask_sensitive_data(record.getMessage())
        record.args = ()
        return True


class StructuredFormatter(standard_logging.Formatter):
    def format(self, record: standard_logging.LogRecord) -> str:
        return mask_sensitive_data(super().format(record))


@dataclass(frozen=True, slots=True)
class LoggerFactory:
    settings: ApplicationSettings

    def get_logger(self, name: str | None = None) -> standard_logging.Logger:
        if name is None:
            return standard_logging.getLogger(LOGGER_NAME)
        if name == LOGGER_NAME or name.startswith(f"{LOGGER_NAME}."):
            return standard_logging.getLogger(name)
        return standard_logging.getLogger(f"{LOGGER_NAME}.{name}")


def configure_logging(settings: ApplicationSettings) -> LoggerFactory:
    logger = standard_logging.getLogger(LOGGER_NAME)
    logger.setLevel(settings.logging.level.value)
    logger.propagate = False
    _replace_handlers(logger, _build_handlers(settings))
    return LoggerFactory(settings=settings)


def install_exception_hook(factory: LoggerFactory) -> None:
    logger = factory.get_logger("exceptions")

    def handle_exception(
        exception_type: type[BaseException],
        exception: BaseException,
        traceback: TracebackType | None,
    ) -> None:
        logger.critical(
            "Unhandled exception",
            exc_info=(exception_type, exception, traceback),
        )

    sys.excepthook = handle_exception


def _build_handlers(settings: ApplicationSettings) -> list[standard_logging.Handler]:
    handlers: list[standard_logging.Handler] = []
    formatter = StructuredFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    sensitive_filter = SensitiveDataFilter()

    console_handler = standard_logging.StreamHandler()
    console_handler.set_name("friday.console")
    console_handler.setLevel(settings.logging.level.value)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(sensitive_filter)
    handlers.append(console_handler)

    file_handler = _file_handler(settings)
    if file_handler is not None:
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sensitive_filter)
        handlers.append(file_handler)

    return handlers


def _file_handler(settings: ApplicationSettings) -> RotatingFileHandler | None:
    try:
        settings.directories.logs.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            settings.directories.logs / settings.logging.file_name,
            maxBytes=settings.logging.max_bytes,
            backupCount=settings.logging.backup_count,
            encoding="utf-8",
        )
    except OSError:
        return None

    handler.set_name("friday.file")
    handler.setLevel(settings.logging.level.value)
    return handler


def _replace_handlers(
    logger: standard_logging.Logger,
    handlers: list[standard_logging.Handler],
) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    for handler in handlers:
        logger.addHandler(handler)


def log_file_path(settings: ApplicationSettings) -> Path:
    return settings.directories.logs / settings.logging.file_name
