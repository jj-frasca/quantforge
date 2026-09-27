"""add quality report source

Revision ID: 3f6a8c1d2e4b
Revises: 946ed1fcdf86
Create Date: 2026-09-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3f6a8c1d2e4b"
down_revision: str | Sequence[str] | None = "946ed1fcdf86"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist adapter identity on new quality reports; legacy rows remain unknown."""
    op.add_column("data_quality_reports", sa.Column("source", sa.String(), nullable=True))


def downgrade() -> None:
    """Remove durable adapter identity from quality reports."""
    op.drop_column("data_quality_reports", "source")
