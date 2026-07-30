from __future__ import annotations

import logging as standard_logging
from dataclasses import dataclass, field
from typing import TypeVar, cast

from friday.application.events import ApplicationEvent, EventHandler
from friday.shared.errors import ApplicationError, ConfigurationError, FridayError

EventT = TypeVar("EventT", bound=ApplicationEvent)


@dataclass(slots=True)
class EventBus:
    logger: standard_logging.Logger
    _handlers: dict[type[ApplicationEvent], list[EventHandler[ApplicationEvent]]] = (
        field(default_factory=dict, init=False)
    )

    def subscribe(
        self,
        event_type: type[EventT],
        handler: EventHandler[EventT],
    ) -> None:
        event_key = self._validate_event_type(event_type)
        self._validate_handler(handler)
        handlers = self._handlers.setdefault(event_key, [])
        stored_handler = cast(EventHandler[ApplicationEvent], handler)

        if any(registered is stored_handler for registered in handlers):
            raise ConfigurationError(
                "Event handler is already registered.",
                technical_message="Duplicate event handler registration was rejected.",
                metadata={
                    "event": event_key.__qualname__,
                    "handler": _handler_name(stored_handler),
                },
            )

        handlers.append(stored_handler)

    def unsubscribe(
        self,
        event_type: type[EventT],
        handler: EventHandler[EventT],
    ) -> None:
        event_key = self._validate_event_type(event_type)
        stored_handler = cast(EventHandler[ApplicationEvent], handler)
        handlers = self._handlers.get(event_key)

        if handlers is None or not _remove_handler(handlers, stored_handler):
            raise ConfigurationError(
                "Event handler is not registered.",
                technical_message="Cannot remove an unknown event handler.",
                metadata={
                    "event": event_key.__qualname__,
                    "handler": _handler_name(stored_handler),
                },
            )

        if not handlers:
            self._handlers.pop(event_key)

    def handlers_for(
        self,
        event_type: type[EventT],
    ) -> tuple[EventHandler[EventT], ...]:
        event_key = self._validate_event_type(event_type)
        handlers = tuple(self._handlers.get(event_key, ()))
        return cast(tuple[EventHandler[EventT], ...], handlers)

    def publish(self, event: EventT) -> None:
        event_key = self._validate_event_type(type(event))
        failures: list[ApplicationError] = []

        for handler in tuple(self._handlers.get(event_key, ())):
            try:
                handler.handle(event)
            except Exception as error:
                handler_error = _event_handler_error(event, handler, error)
                failures.append(handler_error)
                self.logger.error(
                    "Event handler failed",
                    extra={"event_error": handler_error.to_log_dict()},
                    exc_info=(type(error), error, error.__traceback__),
                )

        if failures:
            first_failure = failures[0]
            raise ApplicationError(
                "Event publication failed.",
                code="FRIDAY-EVENTS-002",
                technical_message="One or more event handlers failed.",
                cause=first_failure,
                metadata={
                    "event": event.name,
                    "event_id": str(event.event_id),
                    "failures": len(failures),
                },
            ) from first_failure

    def _validate_event_type(self, event_type: object) -> type[ApplicationEvent]:
        if not isinstance(event_type, type) or not issubclass(
            event_type,
            ApplicationEvent,
        ):
            raise ConfigurationError(
                "Event type is invalid.",
                technical_message="EventBus requires an ApplicationEvent subclass.",
            )
        return event_type

    def _validate_handler(self, handler: object) -> None:
        handle = getattr(handler, "handle", None)
        if not callable(handle):
            raise ConfigurationError(
                "Event handler is invalid.",
                technical_message=(
                    "Event handlers must expose a callable handle method."
                ),
            )


def _remove_handler(
    handlers: list[EventHandler[ApplicationEvent]],
    handler: EventHandler[ApplicationEvent],
) -> bool:
    for index, registered in enumerate(handlers):
        if registered is handler:
            handlers.pop(index)
            return True
    return False


def _event_handler_error(
    event: ApplicationEvent,
    handler: EventHandler[ApplicationEvent],
    error: Exception,
) -> ApplicationError:
    if isinstance(error, FridayError):
        technical_message = error.technical_message
    else:
        technical_message = str(error)

    return ApplicationError(
        "Event handler failed.",
        code="FRIDAY-EVENTS-001",
        technical_message=technical_message,
        cause=error,
        metadata={
            "event": event.name,
            "event_id": str(event.event_id),
            "handler": _handler_name(handler),
        },
    )


def _handler_name(handler: object) -> str:
    return type(handler).__qualname__
