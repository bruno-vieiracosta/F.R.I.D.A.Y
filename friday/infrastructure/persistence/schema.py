from __future__ import annotations

from sqlalchemy import Column, DateTime, MetaData, String, Table

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

schema_metadata = MetaData(naming_convention=NAMING_CONVENTION)

application_metadata = Table(
    "application_metadata",
    schema_metadata,
    Column("key", String(length=100), primary_key=True),
    Column("value", String(length=500), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
