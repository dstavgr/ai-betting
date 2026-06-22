"""oddspapi historical odds cache

Revision ID: 202606210006
Revises: 202606210005
Create Date: 2026-06-21 23:59:00
"""
from alembic import op
import sqlalchemy as sa

revision = "202606210006"
down_revision = "202606210005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oddspapi_historical_cache",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("provider_fixture_id", sa.String(length=160), nullable=False),
        sa.Column("bookmakers", sa.String(length=360), nullable=False),
        sa.Column("etag", sa.String(length=360)),
        sa.Column("last_status_code", sa.Integer()),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("provider", "provider_fixture_id", "bookmakers", name="uq_oddspapi_historical_cache_scope"),
    )
    op.create_index("ix_oddspapi_historical_cache_fixture", "oddspapi_historical_cache", ["provider_fixture_id"])


def downgrade() -> None:
    op.drop_index("ix_oddspapi_historical_cache_fixture", table_name="oddspapi_historical_cache")
    op.drop_table("oddspapi_historical_cache")
