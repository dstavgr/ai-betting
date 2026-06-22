"""feature snapshots

Revision ID: 202606210004
Revises: 202606210003
Create Date: 2026-06-21 23:15:00
"""
from alembic import op
import sqlalchemy as sa

revision = "202606210004"
down_revision = "202606210003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feature_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fixture_id", sa.Integer(), sa.ForeignKey("fixture.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature_version", sa.String(length=80), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("league_id", sa.Integer(), sa.ForeignKey("league.id", ondelete="SET NULL")),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("season.id", ondelete="SET NULL")),
        sa.Column("home_team_id", sa.Integer(), sa.ForeignKey("team.id", ondelete="SET NULL")),
        sa.Column("away_team_id", sa.Integer(), sa.ForeignKey("team.id", ondelete="SET NULL")),
        sa.Column("features", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("target", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("fixture_id", "feature_version", name="uq_feature_snapshot_fixture_version"),
    )
    op.create_index("ix_feature_snapshot_feature_version", "feature_snapshot", ["feature_version"])
    op.create_index("ix_feature_snapshot_league_season", "feature_snapshot", ["league_id", "season_id"])


def downgrade() -> None:
    op.drop_index("ix_feature_snapshot_league_season", table_name="feature_snapshot")
    op.drop_index("ix_feature_snapshot_feature_version", table_name="feature_snapshot")
    op.drop_table("feature_snapshot")
