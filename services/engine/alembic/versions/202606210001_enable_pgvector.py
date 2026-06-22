"""enable pgvector extension

Revision ID: 202606210001
Revises:
Create Date: 2026-06-21 00:00:00.000000
"""

from alembic import op

revision = "202606210001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
