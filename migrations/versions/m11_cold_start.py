"""m11 cold_start (1 table: cold_start_tasks)

Revision ID: m11coldstart01
Revises: m08modulerel01
Create Date: 2026-05-08

design §3 SQLAlchemy block + §3 ER：
- cold_start_tasks 表：CSV 导入批次记录 / orchestrator 模式 / 同步 HTTP 路径
- CHECK 约束：status IN (5 状态)（G6 移除 partial_failed）
- 索引：(project_id, status) / (user_id, created_at)
- project_id 冗余 tenant 兜底（design §3 G6）
- G2/G6 决策：无 UNIQUE(user_id, project_id, source_hash)（无 idempotency）
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from migrations.helpers import ck_clause as _ck_clause

revision: str = "m11coldstart01"
# down_revision 链：M10 是纯读模块（无 model/migration / ADR-003 规则 2 豁免），
# 故 M11 直接接续 M08 module_relations。
down_revision: str | Sequence[str] | None = "m08modulerel01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cold_start_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_hash", sa.Text(), nullable=False),
        sa.Column("source_filename", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("success_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("failed_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_report", postgresql.JSONB(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            ["project_id"], ["projects.id"], ondelete="CASCADE", name="fk_cold_start_project"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_cold_start_user"),
        sa.CheckConstraint(
            _ck_clause(
                "status",
                ("pending", "validating", "importing", "completed", "failed"),
            ),
            name="ck_cold_start_status",
        ),
    )
    op.create_index(
        "ix_cold_start_project_status",
        "cold_start_tasks",
        ["project_id", "status"],
    )
    op.create_index(
        "ix_cold_start_user_created",
        "cold_start_tasks",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_cold_start_user_created", table_name="cold_start_tasks")
    op.drop_index("ix_cold_start_project_status", table_name="cold_start_tasks")
    op.drop_table("cold_start_tasks")
