"""initial baseline

Revision ID: b1c62870faa5
Revises:
Create Date: 2026-05-05 20:52:41.851769

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "b1c62870faa5"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
