from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self, runtime_checkable

from friday.application.persistence.transaction import Transaction


@runtime_checkable
class UnitOfWork(Protocol):
    def __enter__(self) -> Self:
        pass  # pragma: no cover

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        pass  # pragma: no cover

    def begin(self) -> Transaction:
        pass  # pragma: no cover

    def commit(self) -> None:
        pass  # pragma: no cover

    def rollback(self) -> None:
        pass  # pragma: no cover

    def close(self) -> None:
        pass  # pragma: no cover
