"""m04 dimension records (1 table: dimension_records)

Revision ID: m04dimrecord01
Revises: m03nodetree01
Create Date: 2026-05-07

design §3 SQLAlchemy block + §3 ER + §9 主查询模式：
- 唯一约束：UNIQUE(node_id, dimension_type_id)
- tenant 一致性：CHECK ck_dim_project_id_not_null（NOT NULL + service 层等值约束）
- 索引：(node_id, dimension_type_id) 主查询；(project_id, updated_at) tenant + 排序
- 乐观锁：version 默认 1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m04dimrecord01"
down_revision: str | Sequence[str] | None = "m03nodetree01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dimension_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dimension_type_id", sa.Integer(), nullable=False),
        sa.Column(
            "content",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], ondelete="CASCADE", name="fk_dim_node"),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_dim_project",
        ),
        sa.ForeignKeyConstraint(
            ["dimension_type_id"],
            ["dimension_types.id"],
            name="fk_dim_type",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_dim_created_by"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], name="fk_dim_updated_by"),
        sa.UniqueConstraint("node_id", "dimension_type_id", name="uq_dim_node_type"),
        sa.CheckConstraint("project_id IS NOT NULL", name="ck_dim_project_id_not_null"),
    )
    op.create_index("ix_dim_node_id", "dimension_records", ["node_id"])
    op.create_index("ix_dim_project_id", "dimension_records", ["project_id"])
    op.create_index("ix_dim_node_type", "dimension_records", ["node_id", "dimension_type_id"])
    op.create_index(
        "ix_dim_project_updated",
        "dimension_records",
        ["project_id", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_dim_project_updated", table_name="dimension_records")
    op.drop_index("ix_dim_node_type", table_name="dimension_records")
    op.drop_index("ix_dim_project_id", table_name="dimension_records")
    op.drop_index("ix_dim_node_id", table_name="dimension_records")
    op.drop_table("dimension_records")
