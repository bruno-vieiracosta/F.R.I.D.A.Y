import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from friday.bootstrap.config import ApplicationSettings, load_settings
from friday.bootstrap.container import (
    ServiceContainer,
    ServiceLifetime,
    build_container,
)
from friday.bootstrap.logging import LoggerFactory
from friday.shared.clock import Clock, FixedClock, SystemClock
from friday.shared.errors import ConfigurationError
from friday.shared.identifiers import EntityId, IdGenerator, TypedId


class ExampleService:
    pass


class DeterministicIdGenerator:
    def __init__(self, value: UUID) -> None:
        self.value = value

    def new_id(self, id_type: type[TypedId]) -> TypedId:
        return id_type.from_uuid(self.value)


def _settings(temporary_directory: Path) -> ApplicationSettings:
    return load_settings(
        {
            "FRIDAY_ENVIRONMENT": "testing",
            "FRIDAY_LOGS_DIR": str(temporary_directory / "logs"),
            "FRIDAY_LOG_MAX_BYTES": "1024",
            "FRIDAY_LOG_BACKUP_COUNT": "1",
        }
    )


@pytest.fixture(autouse=True)
def reset_friday_logger() -> None:
    logger = logging.getLogger("friday")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


@pytest.mark.unit
def test_register_instance_resolves_same_value() -> None:
    container = ServiceContainer()
    service = ExampleService()

    container.register_instance(ExampleService, service)

    assert container.resolve(ExampleService) is service
    assert container.contains(ExampleService) is True


@pytest.mark.unit
def test_singleton_factory_is_created_once() -> None:
    container = ServiceContainer()
    calls = 0

    def factory(_container: ServiceContainer) -> ExampleService:
        nonlocal calls
        calls += 1
        return ExampleService()

    container.register_factory(
        ExampleService,
        factory,
        lifetime=ServiceLifetime.SINGLETON,
    )

    first = container.resolve(ExampleService)
    second = container.resolve(ExampleService)

    assert first is second
    assert calls == 1


@pytest.mark.unit
def test_transient_factory_creates_new_instances() -> None:
    container = ServiceContainer()
    container.register_factory(ExampleService, lambda _container: ExampleService())

    first = container.resolve(ExampleService)
    second = container.resolve(ExampleService)

    assert first is not second


@pytest.mark.unit
def test_duplicate_registration_is_rejected() -> None:
    container = ServiceContainer()
    container.register_instance(ExampleService, ExampleService())

    with pytest.raises(ConfigurationError, match="Service is already registered"):
        container.register_instance(ExampleService, ExampleService())


@pytest.mark.unit
def test_missing_service_raises_official_error() -> None:
    container = ServiceContainer()

    with pytest.raises(ConfigurationError, match="Service is not registered"):
        container.resolve(ExampleService)


@pytest.mark.unit
def test_registration_can_be_replaced_for_tests() -> None:
    container = ServiceContainer()
    original = ExampleService()
    replacement = ExampleService()
    container.register_instance(ExampleService, original)

    container.register_instance(ExampleService, replacement, replace=True)

    assert container.resolve(ExampleService) is replacement


@pytest.mark.unit
def test_registration_can_be_removed() -> None:
    container = ServiceContainer()
    container.register_instance(ExampleService, ExampleService())

    container.remove(ExampleService)

    assert container.contains(ExampleService) is False
    with pytest.raises(ConfigurationError, match="Service is not registered"):
        container.resolve(ExampleService)


@pytest.mark.unit
def test_containers_are_independent() -> None:
    first_container = ServiceContainer()
    second_container = ServiceContainer()
    first_service = ExampleService()
    second_service = ExampleService()

    first_container.register_instance(ExampleService, first_service)
    second_container.register_instance(ExampleService, second_service)

    assert first_container.resolve(ExampleService) is first_service
    assert second_container.resolve(ExampleService) is second_service


@pytest.mark.unit
def test_factory_can_resolve_other_services() -> None:
    container = ServiceContainer()
    service = ExampleService()
    container.register_instance(ExampleService, service)
    container.register_factory(
        str,
        lambda current_container: (
            type(current_container.resolve(ExampleService)).__name__
        ),
    )

    assert container.resolve(str) == "ExampleService"


@pytest.mark.unit
def test_build_container_registers_core_services(temporary_directory: Path) -> None:
    settings = _settings(temporary_directory)

    container = build_container(settings)

    assert container.resolve(ApplicationSettings) is settings
    assert isinstance(container.resolve(LoggerFactory), LoggerFactory)
    assert isinstance(container.resolve(logging.Logger), logging.Logger)
    assert isinstance(container.resolve(Clock), SystemClock)
    assert container.resolve(IdGenerator).new_id(EntityId).value.version == 4


@pytest.mark.unit
def test_bootstrapped_clock_returns_utc(temporary_directory: Path) -> None:
    container = build_container(_settings(temporary_directory))

    instant = container.resolve(Clock).now()

    assert instant.tzinfo is UTC


@pytest.mark.unit
def test_bootstrapped_id_generator_returns_typed_id(
    temporary_directory: Path,
) -> None:
    container = build_container(_settings(temporary_directory))

    identifier = container.resolve(IdGenerator).new_id(EntityId)

    assert isinstance(identifier, EntityId)
    assert identifier.value.version == 4


@pytest.mark.unit
def test_core_services_can_be_substituted_for_tests(
    temporary_directory: Path,
) -> None:
    container = build_container(_settings(temporary_directory))
    instant = datetime(2026, 1, 1, tzinfo=UTC)
    fixed_clock = FixedClock(instant)
    generator = DeterministicIdGenerator(UUID("00000000-0000-4000-8000-000000000001"))

    container.register_instance(Clock, fixed_clock, replace=True)
    container.register_instance(IdGenerator, generator, replace=True)

    assert container.resolve(Clock).now() == instant
    assert str(container.resolve(IdGenerator).new_id(EntityId)) == (
        "00000000-0000-4000-8000-000000000001"
    )
