from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Self, TypeVar
from uuid import UUID, uuid4

from friday.shared.errors import ValidationError

IdT = TypeVar("IdT", bound="TypedId")


class IdGenerator(Protocol):
    def new_id(self, id_type: type[IdT]) -> IdT:
        pass


@dataclass(frozen=True, slots=True)
class TypedId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ValidationError(
                "Identifier value is invalid.",
                technical_message="TypedId requires a uuid.UUID value.",
            )

    @classmethod
    def new(cls) -> Self:
        return cls(uuid4())

    @classmethod
    def from_uuid(cls, value: UUID) -> Self:
        return cls(value)

    @classmethod
    def from_string(cls, value: str) -> Self:
        try:
            return cls(UUID(value))
        except ValueError as error:
            raise ValidationError(
                "Identifier text is invalid.",
                technical_message="Identifier text must be a valid UUID.",
                cause=error,
                metadata={"identifier_type": cls.__name__},
            ) from error

    @property
    def identifier(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash((type(self), self.value))

    def to_dict(self) -> str:
        return str(self.value)


class EntityId(TypedId):
    pass


class CorrelationId(TypedId):
    pass


class EventId(TypedId):
    pass


@dataclass(frozen=True, slots=True)
class UuidGenerator:
    def new_id(self, id_type: type[IdT]) -> IdT:
        return id_type.from_uuid(uuid4())
