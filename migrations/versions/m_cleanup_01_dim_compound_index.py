"""m-cleanup 01 — dimension_records (updated_by, updated_at) 联合索引

Revision ID: mcleanup01
Revises: m20team01
Create Date: 2026-05-09

cross-sprint punt #13 立修（M04 R1-A A2 约定 M15/M19 已过 / M-CLEANUP sprint 关闭）：
dimension_records 是 M13/M14 写大量行的源表，缺 (updated_by, updated_at) 联合索引会让
activity_stream 按 user 视角时间线查询慢。本迁移 add covering index 闭合 punt。
"""

from collections.abc import Sequence

from alembic import op

revision: str = "mcleanup01"
down_revision: str | Sequence[str] | None = "m20team01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_dim_updated_by_updated_at",
        "dimension_records",
        ["updated_by", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_dim_updated_by_updated_at", table_name="dimension_records")
