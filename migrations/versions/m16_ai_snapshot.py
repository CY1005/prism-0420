"""m16 AI 快照 — ai_snapshot_tasks 表 + ActionType +3 + TargetType +1

Revision ID: m16aisnapshot01
Revises: m16r14enumext01
Create Date: 2026-05-09

design §3 SQLAlchemy block + §12B 字段①（M16 sprint 子片 1）：
- ai_snapshot_tasks 表（FastAPI BackgroundTasks fire-and-forget 子模板）
- 5 索引（node_status / user_created / expires / status_created zombie cron /
  user_project_node_version_count_created find_idempotent）
- 1 CHECK constraint（5 状态枚举）
- 不建 DB UniqueConstraint（audit B1 修复 / 幂等走 advisory_xact_lock）
- ActionType +3：ai_snapshot_started / ai_snapshot_completed / ai_snapshot_failed
- TargetType +1：ai_snapshot_task
- ALTER ck_activity_log_action_type + ck_activity_log_target_type 重建（含 M16 新值）
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from api.models.activity_log import _ACTION_TYPES, _TARGET_TYPES

revision: str = "m16aisnapshot01"
down_revision: str | Sequence[str] | None = "m16r14enumext01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _quoted_in_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    # 闸门 2.6 mini-sprint scaffold：插入 SYSTEM_USER_UUID 种子行（ADR-002 §1.1）。
    # cron / Queue 系统任务写 activity_log 必须落此 user_id；不与真 user.id 撞。
    op.execute(
        """
        INSERT INTO users (id, email, name, password_hash, status, role)
        VALUES (
            '00000000-0000-0000-0000-00000000fe00',
            'system@internal.prism0420.local',
            '系统',
            '__system_no_login__',
            'active',
            'platform_admin'
        )
        ON CONFLICT (id) DO NOTHING
        """
    )

    op.create_table(
        "ai_snapshot_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("version_count", sa.Integer(), nullable=False),
        sa.Column("ai_provider", sa.Text(), nullable=False),
        sa.Column("ai_model", sa.Text(), nullable=False),
        sa.Column("review_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
            name="fk_ai_snapshot_project_id",
        ),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["nodes.id"],
            ondelete="CASCADE",
            name="fk_ai_snapshot_node_id",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_ai_snapshot_user_id",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_ai_snapshot_status",
        ),
    )
    op.create_index("ix_ai_snapshot_node_status", "ai_snapshot_tasks", ["node_id", "status"])
    op.create_index("ix_ai_snapshot_user_created", "ai_snapshot_tasks", ["user_id", "created_at"])
    op.create_index("ix_ai_snapshot_expires", "ai_snapshot_tasks", ["expires_at"])
    op.create_index("ix_ai_snapshot_status_created", "ai_snapshot_tasks", ["status", "created_at"])
    op.create_index(
        "ix_ai_snapshot_idem_lookup",
        "ai_snapshot_tasks",
        ["user_id", "project_id", "node_id", "version_count", "created_at"],
    )

    # 重建 activity_logs CHECK constraint：覆盖 M16 新增 3 ActionType + 1 TargetType
    op.drop_constraint("ck_activity_log_action_type", "activity_logs", type_="check")
    op.create_check_constraint(
        "ck_activity_log_action_type",
        "activity_logs",
        f"action_type IN ({_quoted_in_list(_ACTION_TYPES)})",
    )
    op.drop_constraint("ck_activity_log_target_type", "activity_logs", type_="check")
    op.create_check_constraint(
        "ck_activity_log_target_type",
        "activity_logs",
        f"target_type IN ({_quoted_in_list(_TARGET_TYPES)})",
    )


def downgrade() -> None:
    # 回退 activity_logs CHECK：去掉 M16 新值
    _OLD_ACTION_TYPES = tuple(
        v
        for v in _ACTION_TYPES
        if v not in {"ai_snapshot_started", "ai_snapshot_completed", "ai_snapshot_failed"}
    )
    _OLD_TARGET_TYPES = tuple(v for v in _TARGET_TYPES if v != "ai_snapshot_task")
    op.drop_constraint("ck_activity_log_action_type", "activity_logs", type_="check")
    op.create_check_constraint(
        "ck_activity_log_action_type",
        "activity_logs",
        f"action_type IN ({_quoted_in_list(_OLD_ACTION_TYPES)})",
    )
    op.drop_constraint("ck_activity_log_target_type", "activity_logs", type_="check")
    op.create_check_constraint(
        "ck_activity_log_target_type",
        "activity_logs",
        f"target_type IN ({_quoted_in_list(_OLD_TARGET_TYPES)})",
    )

    op.drop_index("ix_ai_snapshot_idem_lookup", table_name="ai_snapshot_tasks")
    op.drop_index("ix_ai_snapshot_status_created", table_name="ai_snapshot_tasks")
    op.drop_index("ix_ai_snapshot_expires", table_name="ai_snapshot_tasks")
    op.drop_index("ix_ai_snapshot_user_created", table_name="ai_snapshot_tasks")
    op.drop_index("ix_ai_snapshot_node_status", table_name="ai_snapshot_tasks")
    op.drop_table("ai_snapshot_tasks")

    op.execute("DELETE FROM users WHERE id = '00000000-0000-0000-0000-00000000fe00'")
