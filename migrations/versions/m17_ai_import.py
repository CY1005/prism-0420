"""m17 AI 导入 — import_tasks + import_task_items 表 + ActionType +8 + TargetType +1

Revision ID: m17aiimport01
Revises: m16aisnapshot01
Create Date: 2026-05-09

design §3 SQLAlchemy block + §12 Queue payload（M17 sprint 子片 1）：
- import_tasks 表（11 状态主表 / arq Queue 异步 pilot）
- import_task_items 表（5 状态明细表 / 细粒度重试 + 部分失败追踪）
- 4 索引主表（project_status / user_created / expires / status_created）+ 1 索引明细表
- 1 UNIQUE constraint(user_id, project_id, source_hash)：idempotency 7 天复用 key（B1 修复）
- 2 CHECK constraints（status / source_type）+ 1 CHECK 明细表（item status）
- ActionType +8：import_created / import_status_changed / import_ai_step_completed /
  import_review_confirmed / import_batch_inserted / import_canceled / import_failed /
  import_partial_failed
- TargetType +1：import_task
- ALTER ck_activity_log_action_type + ck_activity_log_target_type 重建（含 M17 新值 / 与
  m16 范式一致）
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from api.models.activity_log import _ACTION_TYPES, _TARGET_TYPES
from api.models.import_task import (
    _IMPORT_SOURCE_TYPES,
    _IMPORT_TASK_ITEM_STATUSES,
    _IMPORT_TASK_STATUSES,
)

revision: str = "m17aiimport01"
down_revision: str | Sequence[str] | None = "m16aisnapshot01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _quoted_in_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    # ---- import_tasks 主表 ----
    op.create_table(
        "import_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_hash", sa.Text(), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ai_provider", sa.Text(), nullable=False),
        sa.Column("ai_model", sa.Text(), nullable=False),
        sa.Column("review_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
            name="fk_import_task_project_id",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_import_task_user_id",
        ),
        sa.UniqueConstraint(
            "user_id",
            "project_id",
            "source_hash",
            name="uq_import_user_project_hash",
        ),
        sa.CheckConstraint(
            f"status IN ({_quoted_in_list(_IMPORT_TASK_STATUSES)})",
            name="ck_import_task_status",
        ),
        sa.CheckConstraint(
            f"source_type IN ({_quoted_in_list(_IMPORT_SOURCE_TYPES)})",
            name="ck_import_source_type",
        ),
    )
    op.create_index("ix_import_project_status", "import_tasks", ["project_id", "status"])
    op.create_index("ix_import_user_created", "import_tasks", ["user_id", "created_at"])
    op.create_index("ix_import_expires", "import_tasks", ["expires_at"])
    op.create_index("ix_import_status_created", "import_tasks", ["status", "created_at"])

    # ---- import_task_items 明细表 ----
    op.create_table(
        "import_task_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("ai_output", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("target_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
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
            ["task_id"],
            ["import_tasks.id"],
            ondelete="CASCADE",
            name="fk_import_item_task_id",
        ),
        sa.ForeignKeyConstraint(
            ["target_node_id"],
            ["nodes.id"],
            ondelete="SET NULL",
            name="fk_import_item_target_node_id",
        ),
        sa.CheckConstraint(
            f"status IN ({_quoted_in_list(_IMPORT_TASK_ITEM_STATUSES)})",
            name="ck_import_item_status",
        ),
    )
    op.create_index("ix_import_item_task_status", "import_task_items", ["task_id", "status"])

    # ---- 重建 activity_logs CHECK constraint：覆盖 M17 新增 8 ActionType + 1 TargetType ----
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
    # 回退 activity_logs CHECK：去掉 M17 新值
    _M17_ACTIONS = {
        "import_created",
        "import_status_changed",
        "import_ai_step_completed",
        "import_review_confirmed",
        "import_batch_inserted",
        "import_canceled",
        "import_failed",
        "import_partial_failed",
    }
    _OLD_ACTION_TYPES = tuple(v for v in _ACTION_TYPES if v not in _M17_ACTIONS)
    _OLD_TARGET_TYPES = tuple(v for v in _TARGET_TYPES if v != "import_task")
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

    op.drop_index("ix_import_item_task_status", table_name="import_task_items")
    op.drop_table("import_task_items")

    op.drop_index("ix_import_status_created", table_name="import_tasks")
    op.drop_index("ix_import_expires", table_name="import_tasks")
    op.drop_index("ix_import_user_created", table_name="import_tasks")
    op.drop_index("ix_import_project_status", table_name="import_tasks")
    op.drop_table("import_tasks")
