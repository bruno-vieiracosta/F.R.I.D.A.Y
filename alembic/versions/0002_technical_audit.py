from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_technical_audit"
down_revision: str | None = "0001_initial_revision"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "technical_audit_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("origin", sa.String(length=120), nullable=False),
        sa.Column("operation", sa.String(length=120), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_technical_audit_records")),
    )
    op.create_index(
        "ix_technical_audit_records_category",
        "technical_audit_records",
        ["category"],
        unique=False,
    )
    op.create_index(
        "ix_technical_audit_records_occurred_at",
        "technical_audit_records",
        ["occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_technical_audit_records_origin_operation",
        "technical_audit_records",
        ["origin", "operation"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_technical_audit_records_origin_operation",
        table_name="technical_audit_records",
    )
    op.drop_index(
        "ix_technical_audit_records_occurred_at",
        table_name="technical_audit_records",
    )
    op.drop_index(
        "ix_technical_audit_records_category",
        table_name="technical_audit_records",
    )
    op.drop_table("technical_audit_records")
