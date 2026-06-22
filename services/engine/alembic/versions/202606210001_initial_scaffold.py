"""initial scaffold

Revision ID: 202606210002
Revises: 202606210001
Create Date: 2026-06-21 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "202606210002"
down_revision = "202606210001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
