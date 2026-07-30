from __future__ import annotations

from sqlalchemy import Column, DateTime, Index, MetaData, String, Table, Text

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

technical_audit_records = Table(
    "technical_audit_records",
    schema_metadata,
    Column("id", String(length=36), primary_key=True),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("category", String(length=50), nullable=False),
    Column("origin", String(length=120), nullable=False),
    Column("operation", String(length=120), nullable=False),
    Column("level", String(length=20), nullable=False),
    Column("message", String(length=500), nullable=False),
    Column("metadata_json", Text(), nullable=False),
    Index("ix_technical_audit_records_occurred_at", "occurred_at"),
    Index("ix_technical_audit_records_category", "category"),
    Index("ix_technical_audit_records_origin_operation", "origin", "operation"),
)
