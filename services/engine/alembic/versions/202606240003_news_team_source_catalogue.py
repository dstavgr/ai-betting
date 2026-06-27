"""news team source catalogue

Revision ID: 202606240003
Revises: 202606240002
Create Date: 2026-06-24 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "202606240003"
down_revision = "202606240002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "news_team_source",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("team", sa.String(length=180), nullable=False),
        sa.Column("source_domain", sa.String(length=220), nullable=False),
        sa.Column("feed_url", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("tier", sa.String(length=80), nullable=False),
        sa.Column(
            "verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("team", "source_domain", name="uq_news_team_source_team_domain"),
    )


def downgrade() -> None:
    op.drop_table("news_team_source")
