"""m07 issue (1 table: issues)

Revision ID: m07issue01
Revises: m06competitor01
Create Date: 2026-05-08

design §3 SQLAlchemy block + §3 ER + §9 主查询模式：
- issues 表：node_id 可 NULL（游离 issue）+ ON DELETE SET NULL（**orphan 语义**）
- CHECK 约束：status IN (4 状态) / category IN (4 类)
- 索引：(project_id, status) / (node_id, project_id) / (project_id, category) / (created_by)
- project_id 冗余 tenant 兜底（design §3 CY ack）
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from migrations.helpers import ck_clause as _ck_clause

revision: str = "m07issue01"
down_revision: str | Sequence[str] | None = "m06competitor01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "tags",
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
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
            ["project_id"], ["projects.id"], ondelete="CASCADE", name="fk_issue_project"
        ),
        # orphan 语义：node 删除时 issue 不级联删除，node_id 设 NULL（design §3）
        sa.ForeignKeyConstraint(
            ["node_id"], ["nodes.id"], ondelete="SET NULL", name="fk_issue_node"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_issue_created_by"),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], name="fk_issue_assigned_to"),
        sa.CheckConstraint(
            _ck_clause("status", ("open", "in_progress", "resolved", "closed")),
            name="ck_issue_status",
        ),
        sa.CheckConstraint(
            _ck_clause("category", ("bug", "tech_debt", "design_flaw", "performance")),
            name="ck_issue_category",
        ),
    )
    op.create_index("ix_issue_project_status", "issues", ["project_id", "status"])
    op.create_index("ix_issue_node_project", "issues", ["node_id", "project_id"])
    op.create_index("ix_issue_project_category", "issues", ["project_id", "category"])
    op.create_index("ix_issue_created_by", "issues", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_issue_created_by", table_name="issues")
    op.drop_index("ix_issue_project_category", table_name="issues")
    op.drop_index("ix_issue_node_project", table_name="issues")
    op.drop_index("ix_issue_project_status", table_name="issues")
    op.drop_table("issues")
