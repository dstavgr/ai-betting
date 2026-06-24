"""news intelligence schema

Revision ID: 202606240001
Revises: 202606220001
Create Date: 2026-06-24 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "202606240001"
down_revision = "202606220001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "news_source",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("name", sa.String(length=220)),
        sa.Column("domain", sa.String(length=220), nullable=False, unique=True),
        sa.Column("tier", sa.String(length=80), nullable=False),
        sa.Column("reliability_score", sa.Float(), nullable=False),
        sa.Column("mentions", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("confirmations", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "news_assessment",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("fixture_id", sa.Integer(), nullable=False),
        sa.Column("team", sa.String(length=180), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("fixture_id", "team", name="uq_news_assessment_fixture_team"),
    )


def downgrade() -> None:
    op.drop_table("news_assessment")
    op.drop_table("news_source")
