"""m05 version timeline (1 table: version_records)

Revision ID: m05versiontl01
Revises: m04dimrecord01
Create Date: 2026-05-08

design §3 SQLAlchemy block + §3 ER + §9 主查询模式：
- 唯一约束：UNIQUE(node_id, version_label) — 同节点不重名版本
- CHECK 约束：change_type IN (...) / release_mode IN (...)
- A6 索引升级（闸门 2.5 B1 候选 C 实证 / M05 sprint）：
  ix_version_node_proj_created (node_id, project_id, created_at DESC)
  → covering 主查询 list_by_node + 时间线排序 + tenant 过滤一索引服务
- 部分唯一索引：UNIQUE(node_id) WHERE is_current = true → DB 层兜底"同 node 最多 1 当前版本"
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from migrations.helpers import ck_clause as _ck_clause

revision: str = "m05versiontl01"
down_revision: str | Sequence[str] | None = "m04dimrecord01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "version_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_label", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "change_type",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'added'"),
        ),
        sa.Column(
            "is_current",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("snapshot_data", postgresql.JSONB(), nullable=True),
        sa.Column(
            "release_mode",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'release'"),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
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
            ["node_id"], ["nodes.id"], ondelete="CASCADE", name="fk_version_node"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_version_project",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_version_created_by"),
        sa.UniqueConstraint("node_id", "version_label", name="uq_version_node_label"),
        sa.CheckConstraint(
            _ck_clause(
                "change_type",
                ("added", "modified", "deprecated", "split", "merged", "migrated"),
            ),
            name="ck_version_change_type",
        ),
        sa.CheckConstraint(
            _ck_clause("release_mode", ("release", "continuous")),
            name="ck_version_release_mode",
        ),
    )
    # A6 covering 主索引（M05 sprint 闸门 2.5 B1 候选 C 实证）
    op.create_index(
        "ix_version_node_proj_created",
        "version_records",
        ["node_id", "project_id", sa.text("created_at DESC")],
    )
    op.create_index("ix_version_project", "version_records", ["project_id"])
    # 部分唯一索引：DB 层兜底"同 node 最多 1 当前版本"
    op.create_index(
        "uq_version_node_is_current",
        "version_records",
        ["node_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_version_node_is_current", table_name="version_records")
    op.drop_index("ix_version_project", table_name="version_records")
    op.drop_index("ix_version_node_proj_created", table_name="version_records")
    op.drop_table("version_records")
