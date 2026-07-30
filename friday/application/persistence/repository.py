from __future__ import annotations

from typing import Generic, Protocol, TypeVar, runtime_checkable

from friday.application.persistence.pagination import PageRequest
from friday.application.persistence.specifications import Specification
from friday.shared.identifiers import TypedId
from friday.shared.types import PagedResult

EntityT = TypeVar("EntityT")
IdentifierT_contra = TypeVar(
    "IdentifierT_contra",
    bound=TypedId,
    contravariant=True,
)


@runtime_checkable
class Repository(Protocol, Generic[EntityT, IdentifierT_contra]):
    def get_by_id(self, identifier: IdentifierT_contra) -> EntityT | None:
        pass  # pragma: no cover

    def list(
        self,
        specification: Specification[EntityT] | None = None,
    ) -> tuple[EntityT, ...]:
        pass  # pragma: no cover

    def list_paginated(
        self,
        pagination: PageRequest,
        specification: Specification[EntityT] | None = None,
    ) -> PagedResult[EntityT]:
        pass  # pragma: no cover

    def add(self, entity: EntityT) -> None:
        pass  # pragma: no cover

    def update(self, entity: EntityT) -> None:
        pass  # pragma: no cover

    def remove(self, identifier: IdentifierT_contra) -> None:
        pass  # pragma: no cover

    def exists(self, identifier: IdentifierT_contra) -> bool:
        pass  # pragma: no cover
