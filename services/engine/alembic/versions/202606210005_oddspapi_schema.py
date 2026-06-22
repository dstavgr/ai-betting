"""oddspapi schema

Revision ID: 202606210005
Revises: 202606210004
Create Date: 2026-06-21 23:55:00
"""
from alembic import op
import sqlalchemy as sa

revision = "202606210005"
down_revision = "202606210004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oddspapi_bookmaker",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bookmaker_slug", sa.String(length=120), nullable=False, unique=True),
        sa.Column("bookmaker_name", sa.String(length=180)),
        sa.Column("has_live_odds", sa.Boolean()),
        sa.Column("clone_of", sa.String(length=120)),
        sa.Column("raw_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "oddspapi_market",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_id", sa.String(length=120), nullable=False, unique=True),
        sa.Column("market_name", sa.String(length=220)),
        sa.Column("market_type", sa.String(length=120)),
        sa.Column("market_length", sa.Integer()),
        sa.Column("sport_id", sa.Integer()),
        sa.Column("handicap", sa.Float()),
        sa.Column("period", sa.String(length=120)),
        sa.Column("is_player_prop", sa.Boolean()),
        sa.Column("outcomes", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("raw_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "oddspapi_tournament",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tournament_id", sa.String(length=120), nullable=False, unique=True),
        sa.Column("sport_id", sa.Integer()),
        sa.Column("tournament_slug", sa.String(length=180)),
        sa.Column("tournament_name", sa.String(length=220)),
        sa.Column("category_name", sa.String(length=180)),
        sa.Column("raw_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "oddspapi_fixture",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("oddspapi_fixture_id", sa.String(length=160), nullable=False, unique=True),
        sa.Column("tournament_id", sa.String(length=120)),
        sa.Column("sport_id", sa.Integer()),
        sa.Column("season_id", sa.String(length=120)),
        sa.Column("status_id", sa.Integer()),
        sa.Column("status_name", sa.String(length=120)),
        sa.Column("has_odds", sa.Boolean()),
        sa.Column("start_time", sa.DateTime(timezone=True)),
        sa.Column("true_start_time", sa.DateTime(timezone=True)),
        sa.Column("true_end_time", sa.DateTime(timezone=True)),
        sa.Column("participant1_id", sa.String(length=120)),
        sa.Column("participant1_name", sa.String(length=220)),
        sa.Column("participant2_id", sa.String(length=120)),
        sa.Column("participant2_name", sa.String(length=220)),
        sa.Column("raw_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "odds_fixture_map",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("provider_fixture_id", sa.String(length=160), nullable=False),
        sa.Column("provider_tournament_id", sa.String(length=120)),
        sa.Column("fixture_id", sa.Integer(), sa.ForeignKey("fixture.id", ondelete="CASCADE"), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("mapping_method", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False, server_default=sa.text("'active'")),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("provider", "provider_fixture_id", name="uq_odds_fixture_map_provider_fixture"),
    )
    op.create_table(
        "odds_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("provider_fixture_id", sa.String(length=160), nullable=False),
        sa.Column("fixture_id", sa.Integer(), sa.ForeignKey("fixture.id", ondelete="SET NULL")),
        sa.Column("provider_tournament_id", sa.String(length=120)),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("source_endpoint", sa.String(length=120), nullable=False),
        sa.Column("bookmaker_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("market_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("outcome_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("raw_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )
    op.create_table(
        "odds_price",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("odds_snapshot.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fixture_id", sa.Integer(), sa.ForeignKey("fixture.id", ondelete="SET NULL")),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("provider_fixture_id", sa.String(length=160), nullable=False),
        sa.Column("bookmaker_slug", sa.String(length=120), nullable=False),
        sa.Column("market_id", sa.String(length=120), nullable=False),
        sa.Column("market_name", sa.String(length=220)),
        sa.Column("outcome_id", sa.String(length=120), nullable=False),
        sa.Column("outcome_name", sa.String(length=220)),
        sa.Column("bookmaker_outcome_id", sa.String(length=220)),
        sa.Column("player_key", sa.String(length=120)),
        sa.Column("player_name", sa.String(length=220)),
        sa.Column("line", sa.Float()),
        sa.Column("price_decimal", sa.Float()),
        sa.Column("price_american", sa.String(length=40)),
        sa.Column("price_fractional", sa.String(length=60)),
        sa.Column("active", sa.Boolean()),
        sa.Column("is_main_line", sa.Boolean()),
        sa.Column("limit_amount", sa.Float()),
        sa.Column("bookmaker_changed_at", sa.DateTime(timezone=True)),
        sa.Column("changed_at", sa.DateTime(timezone=True)),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("raw_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )
    op.create_table(
        "oddspapi_sync_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_name", sa.String(length=120), nullable=False),
        sa.Column("sport_id", sa.Integer()),
        sa.Column("tournament_id", sa.String(length=120)),
        sa.Column("fixture_id", sa.String(length=160)),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("message", sa.Text()),
        sa.Column("counts", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_oddspapi_fixture_start_time", "oddspapi_fixture", ["start_time"])
    op.create_index("ix_oddspapi_fixture_tournament", "oddspapi_fixture", ["tournament_id"])
    op.create_index("ix_odds_fixture_map_fixture", "odds_fixture_map", ["fixture_id"])
    op.create_index("ix_odds_snapshot_fixture", "odds_snapshot", ["fixture_id"])
    op.create_index("ix_odds_snapshot_provider_fixture", "odds_snapshot", ["provider", "provider_fixture_id"])
    op.create_index("ix_odds_price_fixture_market", "odds_price", ["fixture_id", "market_id"])
    op.create_index("ix_odds_price_snapshot", "odds_price", ["snapshot_id"])


def downgrade() -> None:
    op.drop_index("ix_odds_price_snapshot", table_name="odds_price")
    op.drop_index("ix_odds_price_fixture_market", table_name="odds_price")
    op.drop_index("ix_odds_snapshot_provider_fixture", table_name="odds_snapshot")
    op.drop_index("ix_odds_snapshot_fixture", table_name="odds_snapshot")
    op.drop_index("ix_odds_fixture_map_fixture", table_name="odds_fixture_map")
    op.drop_index("ix_oddspapi_fixture_tournament", table_name="oddspapi_fixture")
    op.drop_index("ix_oddspapi_fixture_start_time", table_name="oddspapi_fixture")
    op.drop_table("oddspapi_sync_log")
    op.drop_table("odds_price")
    op.drop_table("odds_snapshot")
    op.drop_table("odds_fixture_map")
    op.drop_table("oddspapi_fixture")
    op.drop_table("oddspapi_tournament")
    op.drop_table("oddspapi_market")
    op.drop_table("oddspapi_bookmaker")
