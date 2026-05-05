"""b9 fixture smoke notes table

Revision ID: 333181a89bc8
Revises: b1c62870faa5
Create Date: 2026-05-05 21:23:56.777517

B9 fixture self-test only; remove together with tests/_dummy_model.py when M01 lands.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "333181a89bc8"
down_revision: str | Sequence[str] | None = "b1c62870faa5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("content", sa.String(length=200), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("notes")
