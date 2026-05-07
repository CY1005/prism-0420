"""m03 module tree schema (1 table: nodes) + path text_pattern_ops index

Revision ID: m03nodetree01
Revises: m02project01
Create Date: 2026-05-07

实施期处理段（design §3 sprint 末 R1 punt 回写差异）：
- A1 范式校准：type 列用 String(20) + DB CHECK（M02 R1 已立同款，与 M01 user.py 一致）
- A2 reconcile：加 description 列（design §6 M18 baseline-patch 拼接 name+description；
                                  design §3 字面缺 description = sprint 末回写）

G5 决策：path Text 无长度限制；ix_nodes_path 用 text_pattern_ops 支持 LIKE 前缀子树查询。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m03nodetree01"
down_revision: str | Sequence[str] | None = "m02project01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_NODE_TYPES = ("folder", "file")


# M04 sprint R1-B C2 闭环：_ck_clause 三处重复 → migrations/helpers.py
from migrations.helpers import ck_clause as _ck_clause  # noqa: E402


def upgrade() -> None:
    op.create_table(
        "nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        # A2 reconcile：M18 get_for_embedding 拼接 name + "\n" + description
        sa.Column("description", sa.String(2000), nullable=True),
        # A1 范式：String(20) + DB CHECK + StrEnum.value default
        sa.Column("type", sa.String(20), nullable=False, server_default="folder"),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        # G5：path Text 无长度限制
        sa.Column("path", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
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
            ["project_id"], ["projects.id"], ondelete="CASCADE", name="fk_nodes_project"
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["nodes.id"], ondelete="CASCADE", name="fk_nodes_parent"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_nodes_created_by"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], name="fk_nodes_updated_by"),
        sa.CheckConstraint("name <> ''", name="ck_node_name_not_empty"),
        sa.CheckConstraint("depth >= 0", name="ck_node_depth_non_negative"),
        sa.CheckConstraint("sort_order >= 0", name="ck_node_sort_order_non_negative"),
        sa.CheckConstraint(_ck_clause("type", _NODE_TYPES), name="ck_node_type"),
    )
    op.create_index("ix_nodes_project_id", "nodes", ["project_id"])
    op.create_index("ix_nodes_parent_id", "nodes", ["parent_id"])
    op.create_index("ix_nodes_project_parent", "nodes", ["project_id", "parent_id"])
    op.create_index("ix_nodes_project_sort", "nodes", ["project_id", "sort_order"])
    # G5：path 子树查询用 LIKE 前缀，需 text_pattern_ops opclass
    op.create_index(
        "ix_nodes_path",
        "nodes",
        ["path"],
        postgresql_ops={"path": "text_pattern_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_nodes_path", table_name="nodes")
    op.drop_index("ix_nodes_project_sort", table_name="nodes")
    op.drop_index("ix_nodes_project_parent", table_name="nodes")
    op.drop_index("ix_nodes_parent_id", table_name="nodes")
    op.drop_index("ix_nodes_project_id", table_name="nodes")
    op.drop_table("nodes")
