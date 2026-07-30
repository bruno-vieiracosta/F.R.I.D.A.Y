from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True, slots=True)
class SqlAlchemySessionFactory:
    _sessionmaker: sessionmaker[Session]

    @classmethod
    def from_engine(cls, engine: Engine) -> SqlAlchemySessionFactory:
        return cls(
            sessionmaker(
                bind=engine,
                autoflush=False,
                expire_on_commit=False,
            )
        )

    def create(self) -> Session:
        return self._sessionmaker()
