from dataclasses import FrozenInstanceError
from uuid import UUID, uuid4

import pytest

from friday.shared.errors import ValidationError
from friday.shared.identifiers import (
    CorrelationId,
    EntityId,
    EventId,
    IdGenerator,
    TypedId,
    UuidGenerator,
)
from friday.shared.types import Result


class DeterministicIdGenerator:
    def __init__(self, value: UUID) -> None:
        self.value = value

    def new_id(self, id_type: type[TypedId]) -> TypedId:
        return id_type.from_uuid(self.value)


def _generate_id(generator: IdGenerator, id_type: type[EntityId]) -> EntityId:
    return generator.new_id(id_type)


@pytest.mark.unit
def test_typed_id_can_be_created_from_uuid() -> None:
    value = uuid4()

    identifier = EntityId.from_uuid(value)

    assert identifier.value == value
    assert str(identifier) == str(value)
    assert identifier.identifier == str(value)
    assert identifier.to_dict() == str(value)


@pytest.mark.unit
def test_typed_id_can_be_created_from_string() -> None:
    value = uuid4()

    identifier = EntityId.from_string(str(value))

    assert identifier == EntityId.from_uuid(value)


@pytest.mark.unit
def test_new_typed_id_uses_uuid_v4() -> None:
    identifier = EntityId.new()

    assert identifier.value.version == 4


@pytest.mark.unit
def test_invalid_uuid_text_raises_official_error() -> None:
    with pytest.raises(ValidationError, match="Identifier text is invalid"):
        EntityId.from_string("not-a-uuid")


@pytest.mark.unit
def test_typed_id_rejects_non_uuid_value() -> None:
    with pytest.raises(ValidationError, match="Identifier value is invalid"):
        EntityId("not-a-uuid")


@pytest.mark.unit
def test_ids_of_different_types_are_not_equal() -> None:
    value = uuid4()

    assert EntityId.from_uuid(value) != EventId.from_uuid(value)
    assert EntityId.from_uuid(value) != CorrelationId.from_uuid(value)


@pytest.mark.unit
def test_typed_ids_are_hashable_and_type_safe() -> None:
    value = uuid4()
    entity_id = EntityId.from_uuid(value)
    event_id = EventId.from_uuid(value)
    ids = {entity_id, event_id}
    lookup = {entity_id: "entity", event_id: "event"}

    assert len(ids) == 2
    assert lookup[entity_id] == "entity"
    assert lookup[event_id] == "event"


@pytest.mark.unit
def test_typed_id_is_immutable() -> None:
    identifier = EntityId.new()

    with pytest.raises(FrozenInstanceError):
        identifier.value = uuid4()


@pytest.mark.unit
def test_uuid_generator_returns_requested_type_and_unique_ids() -> None:
    generator = UuidGenerator()

    first = generator.new_id(EntityId)
    second = generator.new_id(EntityId)
    event = generator.new_id(EventId)

    assert isinstance(first, EntityId)
    assert isinstance(event, EventId)
    assert first != second
    assert first.value.version == 4
    assert second.value.version == 4


@pytest.mark.unit
def test_deterministic_generator_can_replace_real_generator() -> None:
    value = uuid4()
    generator = DeterministicIdGenerator(value)

    identifier = _generate_id(generator, EntityId)

    assert identifier == EntityId.from_uuid(value)


@pytest.mark.unit
def test_typed_id_integrates_with_result() -> None:
    identifier = EntityId.new()
    result: Result[EntityId, ValidationError] = Result.success(identifier)

    assert result.to_dict() == {
        "success": True,
        "value": str(identifier),
    }
