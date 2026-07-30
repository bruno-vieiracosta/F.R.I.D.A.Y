from __future__ import annotations

from dataclasses import dataclass, field
from types import TracebackType

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from friday.application.persistence.transaction import Transaction
from friday.infrastructure.persistence.session import SqlAlchemySessionFactory
from friday.shared.errors import PersistenceError


@dataclass(slots=True)
class SqlAlchemyTransaction:
    session: Session
    _is_active: bool = field(default=True, init=False)

    @property
    def is_active(self) -> bool:
        return self._is_active

    def commit(self) -> None:
        try:
            self.session.commit()
        except SQLAlchemyError as error:
            raise PersistenceError(
                "Database transaction could not be committed.",
                technical_message="SQLAlchemy session commit failed.",
                cause=error,
            ) from error
        self._is_active = False

    def rollback(self) -> None:
        try:
            self.session.rollback()
        except SQLAlchemyError as error:
            raise PersistenceError(
                "Database transaction could not be rolled back.",
                technical_message="SQLAlchemy session rollback failed.",
                cause=error,
            ) from error
        self._is_active = False

    def close(self) -> None:
        try:
            self.session.close()
        except SQLAlchemyError as error:
            raise PersistenceError(
                "Database transaction could not be closed.",
                technical_message="SQLAlchemy session close failed.",
                cause=error,
            ) from error
        self._is_active = False


@dataclass(slots=True)
class SqlAlchemyUnitOfWork:
    session_factory: SqlAlchemySessionFactory
    _session: Session | None = field(default=None, init=False)
    _transaction: SqlAlchemyTransaction | None = field(default=None, init=False)

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        self.begin()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        if exc_type is not None:
            self.rollback()
        self.close()
        return None

    def begin(self) -> Transaction:
        if self._transaction is not None and self._transaction.is_active:
            return self._transaction

        self._session = self.session_factory.create()
        self._transaction = SqlAlchemyTransaction(self._session)
        return self._transaction

    def commit(self) -> None:
        self._active_transaction().commit()

    def rollback(self) -> None:
        self._active_transaction().rollback()

    def close(self) -> None:
        if self._transaction is not None:
            self._transaction.close()
        self._transaction = None
        self._session = None

    def _active_transaction(self) -> SqlAlchemyTransaction:
        if self._transaction is None:
            raise PersistenceError(
                "Database transaction is not active.",
                technical_message="UnitOfWork operation requires begin first.",
            )
        return self._transaction
