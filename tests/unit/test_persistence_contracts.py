from dataclasses import FrozenInstanceError, dataclass
from types import TracebackType
from uuid import uuid4

import pytest

from friday.application.persistence import (
    PageRequest,
    PaginatedReader,
    Repository,
    Specification,
    Transaction,
    UnitOfWork,
)
from friday.bootstrap.container import ServiceContainer
from friday.shared.errors import PersistenceError
from friday.shared.identifiers import EntityId
from friday.shared.types import PagedResult


@dataclass(frozen=True, slots=True)
class TechnicalRecord:
    identifier: EntityId
    name: str


@dataclass(frozen=True, slots=True)
class OtherRecord:
    identifier: EntityId
    code: str


@dataclass(frozen=True, slots=True)
class NameSpecification:
    expected_name: str

    def is_satisfied_by(self, candidate: TechnicalRecord) -> bool:
        return candidate.name == self.expected_name


class InMemoryRepository:
    def __init__(self) -> None:
        self.records: dict[EntityId, TechnicalRecord] = {}

    def get_by_id(self, identifier: EntityId) -> TechnicalRecord | None:
        return self.records.get(identifier)

    def list(
        self,
        specification: Specification[TechnicalRecord] | None = None,
    ) -> tuple[TechnicalRecord, ...]:
        records = tuple(self.records.values())
        if specification is None:
            return records
        return tuple(
            record for record in records if specification.is_satisfied_by(record)
        )

    def list_paginated(
        self,
        pagination: PageRequest,
        specification: Specification[TechnicalRecord] | None = None,
    ) -> PagedResult[TechnicalRecord]:
        records = self.list(specification)
        start = (pagination.page - 1) * pagination.page_size
        end = start + pagination.page_size
        total_pages = 0
        if records:
            total_pages = (len(records) + pagination.page_size - 1) // (
                pagination.page_size
            )
        return PagedResult(
            items=records[start:end],
            page=pagination.page,
            page_size=pagination.page_size,
            total_items=len(records),
            total_pages=total_pages,
        )

    def add(self, entity: TechnicalRecord) -> None:
        self.records[entity.identifier] = entity

    def update(self, entity: TechnicalRecord) -> None:
        if entity.identifier not in self.records:
            raise PersistenceError("Record cannot be updated.")
        self.records[entity.identifier] = entity

    def remove(self, identifier: EntityId) -> None:
        self.records.pop(identifier, None)

    def exists(self, identifier: EntityId) -> bool:
        return identifier in self.records


class OtherRepository:
    def __init__(self) -> None:
        self.records: dict[EntityId, OtherRecord] = {}

    def get_by_id(self, identifier: EntityId) -> OtherRecord | None:
        return self.records.get(identifier)

    def list(
        self,
        specification: Specification[OtherRecord] | None = None,
    ) -> tuple[OtherRecord, ...]:
        records = tuple(self.records.values())
        if specification is None:
            return records
        return tuple(
            record for record in records if specification.is_satisfied_by(record)
        )

    def list_paginated(
        self,
        pagination: PageRequest,
        specification: Specification[OtherRecord] | None = None,
    ) -> PagedResult[OtherRecord]:
        records = self.list(specification)
        return PagedResult(
            items=records,
            page=pagination.page,
            page_size=pagination.page_size,
            total_items=len(records),
            total_pages=1 if records else 0,
        )

    def add(self, entity: OtherRecord) -> None:
        self.records[entity.identifier] = entity

    def update(self, entity: OtherRecord) -> None:
        self.records[entity.identifier] = entity

    def remove(self, identifier: EntityId) -> None:
        self.records.pop(identifier, None)

    def exists(self, identifier: EntityId) -> bool:
        return identifier in self.records


class FakeTransaction:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.closed = False

    @property
    def is_active(self) -> bool:
        return not self.closed

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.transaction = FakeTransaction()
        self.entered = False

    def __enter__(self) -> "FakeUnitOfWork":
        self.entered = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        self.close()
        return None

    def begin(self) -> Transaction:
        return self.transaction

    def commit(self) -> None:
        self.transaction.commit()

    def rollback(self) -> None:
        self.transaction.rollback()

    def close(self) -> None:
        self.transaction.close()


def _record(name: str) -> TechnicalRecord:
    return TechnicalRecord(identifier=EntityId.from_uuid(uuid4()), name=name)


@pytest.mark.unit
def test_repository_contract_supports_typed_crud_operations() -> None:
    repository: Repository[TechnicalRecord, EntityId] = InMemoryRepository()
    record = _record("alpha")

    repository.add(record)

    assert repository.get_by_id(record.identifier) == record
    assert repository.exists(record.identifier) is True
    assert repository.list() == (record,)

    updated = TechnicalRecord(identifier=record.identifier, name="beta")
    repository.update(updated)
    assert repository.get_by_id(record.identifier) == updated

    repository.remove(record.identifier)
    assert repository.get_by_id(record.identifier) is None
    assert repository.exists(record.identifier) is False


@pytest.mark.unit
def test_repository_contract_is_generic_for_multiple_entity_types() -> None:
    repository: Repository[OtherRecord, EntityId] = OtherRepository()
    record = OtherRecord(identifier=EntityId.from_uuid(uuid4()), code="other")

    repository.add(record)

    assert repository.get_by_id(record.identifier) == record


@pytest.mark.unit
def test_specification_contract_filters_without_sql() -> None:
    repository: Repository[TechnicalRecord, EntityId] = InMemoryRepository()
    first = _record("match")
    second = _record("skip")
    repository.add(first)
    repository.add(second)

    records = repository.list(NameSpecification("match"))

    assert records == (first,)
    assert isinstance(NameSpecification("match"), Specification)


@pytest.mark.unit
def test_page_request_is_immutable_and_validated() -> None:
    pagination = PageRequest(page=1, page_size=10)

    assert pagination.page == 1
    assert pagination.page_size == 10

    with pytest.raises(FrozenInstanceError):
        pagination.page = 2

    with pytest.raises(PersistenceError, match="Pagination request is invalid"):
        PageRequest(page=0, page_size=10)

    with pytest.raises(PersistenceError, match="Pagination request is invalid"):
        PageRequest(page=1, page_size=0)


@pytest.mark.unit
def test_repository_contract_uses_paged_result() -> None:
    repository: Repository[TechnicalRecord, EntityId] = InMemoryRepository()
    first = _record("one")
    second = _record("two")
    repository.add(first)
    repository.add(second)

    result = repository.list_paginated(PageRequest(page=1, page_size=1))

    assert isinstance(result, PagedResult)
    assert result.items == (first,)
    assert result.total_items == 2
    assert result.total_pages == 2


@pytest.mark.unit
def test_paginated_reader_contract_can_be_used_independently() -> None:
    reader: PaginatedReader[TechnicalRecord] = InMemoryRepository()

    result = reader.list_paginated(PageRequest(page=1, page_size=10))

    assert result == PagedResult(
        items=(),
        page=1,
        page_size=10,
        total_items=0,
        total_pages=0,
    )
    assert isinstance(reader, PaginatedReader)


@pytest.mark.unit
def test_transaction_contract_exposes_minimum_operations() -> None:
    transaction: Transaction = FakeTransaction()

    assert transaction.is_active is True
    transaction.commit()
    transaction.rollback()
    transaction.close()

    assert transaction.is_active is False


@pytest.mark.unit
def test_unit_of_work_contract_supports_context_management() -> None:
    unit_of_work: UnitOfWork = FakeUnitOfWork()

    with unit_of_work as active_unit_of_work:
        transaction = active_unit_of_work.begin()
        active_unit_of_work.commit()

    assert isinstance(transaction, Transaction)
    assert transaction.committed is True
    assert transaction.closed is True


@pytest.mark.unit
def test_unit_of_work_can_rollback() -> None:
    unit_of_work: UnitOfWork = FakeUnitOfWork()

    unit_of_work.rollback()

    assert unit_of_work.transaction.rolled_back is True


@pytest.mark.unit
def test_persistence_errors_use_official_hierarchy() -> None:
    repository: Repository[TechnicalRecord, EntityId] = InMemoryRepository()

    with pytest.raises(PersistenceError):
        repository.update(_record("missing"))


@pytest.mark.unit
def test_contracts_are_compatible_with_container_without_direct_dependency() -> None:
    container = ServiceContainer()
    repository = InMemoryRepository()
    container.register_instance(Repository, repository)

    resolved = container.resolve(Repository)

    assert resolved is repository
