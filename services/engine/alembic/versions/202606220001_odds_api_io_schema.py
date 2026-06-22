"""odds-api.io schema

Revision ID: 202606220001
Revises: 202606210006
Create Date: 2026-06-22 06:55:00
"""
from alembic import op
import sqlalchemy as sa

revision = "202606220001"
down_revision = "202606210006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oddsapiio_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(length=160), nullable=False, unique=True),
        sa.Column("sport_slug", sa.String(length=120)),
        sa.Column("league_slug", sa.String(length=180)),
        sa.Column("status", sa.String(length=80)),
        sa.Column("starts_at", sa.DateTime(timezone=True)),
        sa.Column("home_name", sa.String(length=220)),
        sa.Column("away_name", sa.String(length=220)),
        sa.Column("scores", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("raw_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_oddsapiio_event_league_start", "oddsapiio_event", ["league_slug", "starts_at"])
    op.create_index("ix_oddsapiio_event_start", "oddsapiio_event", ["starts_at"])

    op.create_table(
        "provider_quota_window",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requests_used", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("request_limit", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("provider", "window_start", name="uq_provider_quota_window"),
    )
    op.create_index("ix_provider_quota_window_provider", "provider_quota_window", ["provider", "window_start"])


def downgrade() -> None:
    op.drop_index("ix_provider_quota_window_provider", table_name="provider_quota_window")
    op.drop_table("provider_quota_window")
    op.drop_index("ix_oddsapiio_event_start", table_name="oddsapiio_event")
    op.drop_index("ix_oddsapiio_event_league_start", table_name="oddsapiio_event")
    op.drop_table("oddsapiio_event")
