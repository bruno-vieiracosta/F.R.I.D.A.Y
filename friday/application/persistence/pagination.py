from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar, runtime_checkable

from friday.application.persistence.specifications import Specification
from friday.shared.errors import PersistenceError
from friday.shared.types import PagedResult

EntityT = TypeVar("EntityT")


@dataclass(frozen=True, slots=True)
class PageRequest:
    page: int
    page_size: int

    def __post_init__(self) -> None:
        if self.page < 1:
            raise PersistenceError(
                "Pagination request is invalid.",
                technical_message="Page must be greater than or equal to 1.",
            )
        if self.page_size < 1:
            raise PersistenceError(
                "Pagination request is invalid.",
                technical_message="Page size must be greater than or equal to 1.",
            )


@runtime_checkable
class PaginatedReader(Protocol, Generic[EntityT]):
    def list_paginated(
        self,
        pagination: PageRequest,
        specification: Specification[EntityT] | None = None,
    ) -> PagedResult[EntityT]:
        pass  # pragma: no cover
