"""m12 comparison (2 tables: comparison_snapshots + comparison_snapshot_items)

Revision ID: m12comparison01
Revises: m11coldstart01
Create Date: 2026-05-08

design §3 SQLAlchemy block + §3 ER：
- comparison_snapshots：快照主表 / 含 nodes_ref + dimensions_ref 元数据 + version 乐观锁
- comparison_snapshot_items：G4=B 值快照明细 / node_id ON DELETE SET NULL（不降级）
- 索引：(project_id) / (user_id, project_id) / (snapshot_id) / (node_id)
- G2/G4：无 status 字段（快照无状态最小集）
- name 无唯一约束（允许同名快照）
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m12comparison01"
down_revision: str | Sequence[str] | None = "m11coldstart01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "comparison_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "nodes_ref",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "dimensions_ref",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_comparison_snapshot_project",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_comparison_snapshot_user",
        ),
    )
    op.create_index(
        "ix_comparison_snapshot_project",
        "comparison_snapshots",
        ["project_id"],
    )
    op.create_index(
        "ix_comparison_snapshot_user_project",
        "comparison_snapshots",
        ["user_id", "project_id"],
    )

    op.create_table(
        "comparison_snapshot_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dimension_type_id", sa.Integer(), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=True),
        sa.Column(
            "snapshot_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["comparison_snapshots.id"],
            ondelete="CASCADE",
            name="fk_comparison_snapshot_items_snapshot",
        ),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["nodes.id"],
            ondelete="SET NULL",
            name="fk_comparison_snapshot_items_node",
        ),
        sa.ForeignKeyConstraint(
            ["dimension_type_id"],
            ["dimension_types.id"],
            name="fk_comparison_snapshot_items_dim_type",
        ),
    )
    op.create_index(
        "ix_snapshot_items_snapshot",
        "comparison_snapshot_items",
        ["snapshot_id"],
    )
    op.create_index(
        "ix_snapshot_items_node",
        "comparison_snapshot_items",
        ["node_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_snapshot_items_node", table_name="comparison_snapshot_items")
    op.drop_index("ix_snapshot_items_snapshot", table_name="comparison_snapshot_items")
    op.drop_table("comparison_snapshot_items")
    op.drop_index("ix_comparison_snapshot_user_project", table_name="comparison_snapshots")
    op.drop_index("ix_comparison_snapshot_project", table_name="comparison_snapshots")
    op.drop_table("comparison_snapshots")
