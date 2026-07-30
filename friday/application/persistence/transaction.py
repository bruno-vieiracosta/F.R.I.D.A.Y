from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Transaction(Protocol):
    @property
    def is_active(self) -> bool:
        pass  # pragma: no cover

    def commit(self) -> None:
        pass  # pragma: no cover

    def rollback(self) -> None:
        pass  # pragma: no cover

    def close(self) -> None:
        pass  # pragma: no cover
