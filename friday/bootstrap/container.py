from __future__ import annotations

import logging as standard_logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar, cast, overload

from sqlalchemy.engine import Engine

from friday.application.event_bus import EventBus
from friday.application.persistence.unit_of_work import UnitOfWork
from friday.bootstrap.config import ApplicationSettings, load_settings
from friday.bootstrap.logging import LoggerFactory, configure_logging
from friday.infrastructure.audit import (
    TechnicalAuditEvent,
    TechnicalAuditEventHandler,
    TechnicalAuditRepository,
    TechnicalAuditService,
)
from friday.infrastructure.backup import (
    BackupConfiguration,
    BackupService,
    resolve_backup_configuration,
)
from friday.infrastructure.persistence import (
    DatabaseConfiguration,
    DatabaseInfrastructure,
    SqlAlchemyEngineFactory,
    SqlAlchemySessionFactory,
    SqlAlchemyUnitOfWork,
    resolve_database_configuration,
)
from friday.shared.clock import Clock, SystemClock
from friday.shared.errors import ConfigurationError
from friday.shared.identifiers import IdGenerator, UuidGenerator

ServiceT = TypeVar("ServiceT")


class ServiceLifetime(StrEnum):
    SINGLETON = "singleton"
    TRANSIENT = "transient"


@dataclass(frozen=True, slots=True)
class ServiceRegistration(Generic[ServiceT]):
    service_type: type[object]
    factory: Callable[[ServiceContainer], ServiceT]
    lifetime: ServiceLifetime


class ServiceContainer:
    def __init__(self) -> None:
        self._registrations: dict[type[object], ServiceRegistration[object]] = {}
        self._singletons: dict[type[object], object] = {}

    def register_instance(
        self,
        service_type: object,
        instance: ServiceT,
        *,
        replace: bool = False,
    ) -> None:
        def factory(_container: ServiceContainer) -> ServiceT:
            return instance

        self.register_factory(
            service_type,
            factory,
            lifetime=ServiceLifetime.SINGLETON,
            replace=replace,
        )
        self._singletons[self._validate_service_type(service_type)] = instance

    def register_factory(
        self,
        service_type: object,
        factory: Callable[[ServiceContainer], ServiceT],
        *,
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
        replace: bool = False,
    ) -> None:
        service_key = self._validate_service_type(service_type)

        if service_key in self._registrations and not replace:
            raise ConfigurationError(
                "Service is already registered.",
                technical_message="Duplicate service registration was rejected.",
                metadata={"service": service_key.__qualname__},
            )

        registration = ServiceRegistration(
            service_type=service_key,
            factory=factory,
            lifetime=lifetime,
        )
        self._registrations[service_key] = cast(
            ServiceRegistration[object],
            registration,
        )
        if replace:
            self._singletons.pop(service_key, None)

    @overload
    def resolve(self, service_type: type[ServiceT]) -> ServiceT:
        pass

    @overload
    def resolve(self, service_type: object) -> object:
        pass

    def resolve(self, service_type: object) -> object:
        service_key = self._validate_service_type(service_type)
        registration = self._registrations.get(service_key)

        if registration is None:
            raise ConfigurationError(
                "Service is not registered.",
                technical_message=(
                    "Dependency resolution failed for an unknown service."
                ),
                metadata={"service": service_key.__qualname__},
            )

        if registration.lifetime is ServiceLifetime.SINGLETON:
            if service_key not in self._singletons:
                self._singletons[service_key] = registration.factory(self)
            return self._singletons[service_key]

        return registration.factory(self)

    def remove(self, service_type: object) -> None:
        service_key = self._validate_service_type(service_type)

        if service_key not in self._registrations:
            raise ConfigurationError(
                "Service is not registered.",
                technical_message="Cannot remove an unknown service registration.",
                metadata={"service": service_key.__qualname__},
            )

        self._registrations.pop(service_key)
        self._singletons.pop(service_key, None)

    def contains(self, service_type: object) -> bool:
        service_key = self._validate_service_type(service_type)
        return service_key in self._registrations

    def _validate_service_type(self, service_type: object) -> type[object]:
        if not isinstance(service_type, type):
            raise ConfigurationError(
                "Service type is invalid.",
                technical_message="Service registrations require a class or protocol.",
            )
        return service_type


def build_container(settings: ApplicationSettings | None = None) -> ServiceContainer:
    resolved_settings = load_settings() if settings is None else settings
    logger_factory = configure_logging(resolved_settings)

    def event_bus_factory(current_container: ServiceContainer) -> EventBus:
        factory = current_container.resolve(LoggerFactory)
        event_bus = EventBus(logger=factory.get_logger("events"))
        event_bus.subscribe(
            TechnicalAuditEvent,
            current_container.resolve(TechnicalAuditEventHandler),
        )
        return event_bus

    def engine_factory(current_container: ServiceContainer) -> Engine:
        factory = current_container.resolve(SqlAlchemyEngineFactory)
        return factory.create()

    def session_factory(
        current_container: ServiceContainer,
    ) -> SqlAlchemySessionFactory:
        engine = current_container.resolve(Engine)
        return SqlAlchemySessionFactory.from_engine(engine)

    def unit_of_work_factory(current_container: ServiceContainer) -> UnitOfWork:
        factory = current_container.resolve(SqlAlchemySessionFactory)
        return SqlAlchemyUnitOfWork(factory)

    def database_factory(
        current_container: ServiceContainer,
    ) -> DatabaseInfrastructure:
        configuration = current_container.resolve(DatabaseConfiguration)
        engine = current_container.resolve(Engine)
        factory = current_container.resolve(SqlAlchemySessionFactory)
        logger = current_container.resolve(LoggerFactory).get_logger("database")
        logger.info("Database infrastructure initialized")
        return DatabaseInfrastructure(
            configuration=configuration,
            engine=engine,
            session_factory=factory,
        )

    def audit_repository_factory(
        current_container: ServiceContainer,
    ) -> TechnicalAuditRepository:
        return TechnicalAuditRepository(
            session_factory=current_container.resolve(SqlAlchemySessionFactory),
            logger=current_container.resolve(LoggerFactory).get_logger("audit"),
        )

    def audit_service_factory(
        current_container: ServiceContainer,
    ) -> TechnicalAuditService:
        return TechnicalAuditService(
            repository=current_container.resolve(TechnicalAuditRepository),
            clock=cast(Clock, current_container.resolve(Clock)),
            id_generator=cast(IdGenerator, current_container.resolve(IdGenerator)),
            logger=current_container.resolve(LoggerFactory).get_logger("audit"),
        )

    def backup_service_factory(current_container: ServiceContainer) -> BackupService:
        return BackupService(
            settings=current_container.resolve(ApplicationSettings),
            configuration=current_container.resolve(BackupConfiguration),
            database=current_container.resolve(DatabaseInfrastructure),
            clock=cast(Clock, current_container.resolve(Clock)),
            id_generator=cast(IdGenerator, current_container.resolve(IdGenerator)),
            logger=current_container.resolve(LoggerFactory).get_logger("backup"),
            audit_service=current_container.resolve(TechnicalAuditService),
            event_bus=current_container.resolve(EventBus),
        )

    container = ServiceContainer()
    container.register_instance(ApplicationSettings, resolved_settings)
    container.register_instance(LoggerFactory, logger_factory)
    container.register_instance(
        standard_logging.Logger,
        logger_factory.get_logger(),
    )
    container.register_instance(Clock, SystemClock())
    container.register_instance(IdGenerator, UuidGenerator())
    container.register_instance(
        DatabaseConfiguration,
        resolve_database_configuration(resolved_settings),
    )
    container.register_instance(
        BackupConfiguration,
        resolve_backup_configuration(resolved_settings),
    )
    container.register_factory(
        SqlAlchemyEngineFactory,
        lambda current_container: SqlAlchemyEngineFactory(
            configuration=current_container.resolve(DatabaseConfiguration),
            logger=current_container.resolve(LoggerFactory).get_logger("database"),
        ),
        lifetime=ServiceLifetime.SINGLETON,
    )
    container.register_factory(
        Engine,
        engine_factory,
        lifetime=ServiceLifetime.SINGLETON,
    )
    container.register_factory(
        SqlAlchemySessionFactory,
        session_factory,
        lifetime=ServiceLifetime.SINGLETON,
    )
    container.register_factory(
        UnitOfWork,
        unit_of_work_factory,
        lifetime=ServiceLifetime.TRANSIENT,
    )
    container.register_factory(
        DatabaseInfrastructure,
        database_factory,
        lifetime=ServiceLifetime.SINGLETON,
    )
    container.register_factory(
        TechnicalAuditRepository,
        audit_repository_factory,
        lifetime=ServiceLifetime.SINGLETON,
    )
    container.register_factory(
        TechnicalAuditService,
        audit_service_factory,
        lifetime=ServiceLifetime.SINGLETON,
    )
    container.register_factory(
        TechnicalAuditEventHandler,
        lambda current_container: TechnicalAuditEventHandler(
            current_container.resolve(TechnicalAuditService),
        ),
        lifetime=ServiceLifetime.SINGLETON,
    )
    container.register_factory(
        EventBus,
        event_bus_factory,
        lifetime=ServiceLifetime.SINGLETON,
    )
    container.register_factory(
        BackupService,
        backup_service_factory,
        lifetime=ServiceLifetime.SINGLETON,
    )
    return container
