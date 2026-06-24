"""news source team reliability

Revision ID: 202606240002
Revises: 202606240001
Create Date: 2026-06-24 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "202606240002"
down_revision = "202606240001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "news_source_team",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "source_id",
            sa.String(length=120),
            sa.ForeignKey("news_source.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("team", sa.String(length=180), nullable=False),
        sa.Column("team_mentions", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "team_confirmations",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("source_id", "team", name="uq_news_source_team"),
    )


def downgrade() -> None:
    op.drop_table("news_source_team")
