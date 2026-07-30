from __future__ import annotations

import logging as standard_logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar, cast, overload

from friday.bootstrap.config import ApplicationSettings, load_settings
from friday.bootstrap.logging import LoggerFactory, configure_logging
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

    container = ServiceContainer()
    container.register_instance(ApplicationSettings, resolved_settings)
    container.register_instance(LoggerFactory, logger_factory)
    container.register_instance(
        standard_logging.Logger,
        logger_factory.get_logger(),
    )
    container.register_instance(Clock, SystemClock())
    container.register_instance(IdGenerator, UuidGenerator())
    return container
