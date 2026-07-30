from __future__ import annotations

from typing import Generic, Protocol, TypeVar, runtime_checkable

EntityT_contra = TypeVar("EntityT_contra", contravariant=True)


@runtime_checkable
class Specification(Protocol, Generic[EntityT_contra]):
    def is_satisfied_by(self, candidate: EntityT_contra) -> bool:
        pass  # pragma: no cover
