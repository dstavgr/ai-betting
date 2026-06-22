"""api football schema

Revision ID: 202606210003
Revises: 202606210002
Create Date: 2026-06-21 21:05:00
"""
from alembic import op
import sqlalchemy as sa

revision = "202606210003"
down_revision = "202606210002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "league",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("api_football_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("type", sa.String(length=80)),
        sa.Column("country_name", sa.String(length=120)),
        sa.Column("country_code", sa.String(length=12)),
        sa.Column("country_flag", sa.Text()),
        sa.Column("logo", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "venue",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("api_football_id", sa.Integer(), unique=True),
        sa.Column("name", sa.String(length=180)),
        sa.Column("address", sa.Text()),
        sa.Column("city", sa.String(length=120)),
        sa.Column("capacity", sa.Integer()),
        sa.Column("surface", sa.String(length=80)),
        sa.Column("image", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "season",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("league_id", sa.Integer(), sa.ForeignKey("league.id", ondelete="CASCADE"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("current", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("coverage", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("league_id", "year", name="uq_season_league_year"),
    )
    op.create_table(
        "team",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("api_football_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("code", sa.String(length=24)),
        sa.Column("country", sa.String(length=120)),
        sa.Column("founded", sa.Integer()),
        sa.Column("national", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("logo", sa.Text()),
        sa.Column("venue_id", sa.Integer(), sa.ForeignKey("venue.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "fixture",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("api_football_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("league_id", sa.Integer(), sa.ForeignKey("league.id", ondelete="SET NULL")),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("season.id", ondelete="SET NULL")),
        sa.Column("venue_id", sa.Integer(), sa.ForeignKey("venue.id", ondelete="SET NULL")),
        sa.Column("home_team_id", sa.Integer(), sa.ForeignKey("team.id", ondelete="SET NULL")),
        sa.Column("away_team_id", sa.Integer(), sa.ForeignKey("team.id", ondelete="SET NULL")),
        sa.Column("referee_name", sa.String(length=180)),
        sa.Column("timezone", sa.String(length=80)),
        sa.Column("kickoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timestamp", sa.BigInteger()),
        sa.Column("round", sa.String(length=180)),
        sa.Column("status_long", sa.String(length=120)),
        sa.Column("status_short", sa.String(length=40)),
        sa.Column("elapsed", sa.Integer()),
        sa.Column("goals_home", sa.Integer()),
        sa.Column("goals_away", sa.Integer()),
        sa.Column("score", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("raw_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "fixture_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fixture_id", sa.Integer(), sa.ForeignKey("fixture.id", ondelete="CASCADE"), nullable=False),
        sa.Column("elapsed", sa.Integer()),
        sa.Column("extra", sa.Integer()),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("team.id", ondelete="SET NULL")),
        sa.Column("player_api_football_id", sa.Integer()),
        sa.Column("player_name", sa.String(length=180)),
        sa.Column("assist_api_football_id", sa.Integer()),
        sa.Column("assist_name", sa.String(length=180)),
        sa.Column("type", sa.String(length=80)),
        sa.Column("detail", sa.String(length=160)),
        sa.Column("comments", sa.Text()),
        sa.Column("raw_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "team_match_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fixture_id", sa.Integer(), sa.ForeignKey("fixture.id", ondelete="CASCADE"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("team.id", ondelete="CASCADE"), nullable=False),
        sa.Column("statistics", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("raw_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("fixture_id", "team_id", name="uq_team_match_stats_fixture_team"),
    )
    op.create_table(
        "source_entity_map",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("source_name", sa.String(length=220)),
        sa.Column("canonical_table", sa.String(length=80), nullable=False),
        sa.Column("canonical_id", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("source", "entity_type", "source_id", name="uq_source_entity_map_source_entity_id"),
    )
    op.create_table(
        "api_football_sync_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_name", sa.String(length=120), nullable=False),
        sa.Column("league_api_football_id", sa.Integer()),
        sa.Column("season_year", sa.Integer()),
        sa.Column("fixture_api_football_id", sa.Integer()),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("message", sa.Text()),
        sa.Column("counts", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_fixture_kickoff_at", "fixture", ["kickoff_at"])
    op.create_index("ix_fixture_league_season", "fixture", ["league_id", "season_id"])
    op.create_index("ix_source_entity_map_canonical", "source_entity_map", ["canonical_table", "canonical_id"])


def downgrade() -> None:
    op.drop_index("ix_source_entity_map_canonical", table_name="source_entity_map")
    op.drop_index("ix_fixture_league_season", table_name="fixture")
    op.drop_index("ix_fixture_kickoff_at", table_name="fixture")
    op.drop_table("api_football_sync_log")
    op.drop_table("source_entity_map")
    op.drop_table("team_match_stats")
    op.drop_table("fixture_event")
    op.drop_table("fixture")
    op.drop_table("team")
    op.drop_table("season")
    op.drop_table("venue")
    op.drop_table("league")
