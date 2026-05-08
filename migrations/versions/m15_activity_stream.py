"""m15 activity stream — activity_logs 横切表（M15 R10-2 owner）

Revision ID: m15activity01
Revises: m14industrynews01
Create Date: 2026-05-08

design §3 SQLAlchemy block + R10-2 owner：
- activity_logs 表：所有业务模块共享；M15 实装 ActivityLog model + 本迁移落库
- project_id NULLABLE：M14 全局豁免业务模块首发（write_event UUID→Optional 升级 /
  M15 sprint 子片 0 prep baseline-patch 反向回写 2026-05-08）
- ImmutableMixin：append-only / 无 updated_at（日志不可修改）
- 3 索引：(project_id, created_at) 主查询 / (user_id, project_id) 按用户 / (target_type, target_id) 按目标
- 2 CHECK constraint：action_type / target_type 字面 IN 列表（与 model._ACTION_TYPES /
  _TARGET_TYPES 同步 / R10-2 owner 维护）
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from api.models.activity_log import _ACTION_TYPES, _TARGET_TYPES

revision: str = "m15activity01"
down_revision: str | Sequence[str] | None = "m14industrynews01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _quoted_in_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    op.create_table(
        "activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_activity_log_project_id",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_activity_log_user_id",
        ),
        sa.CheckConstraint(
            f"action_type IN ({_quoted_in_list(_ACTION_TYPES)})",
            name="ck_activity_log_action_type",
        ),
        sa.CheckConstraint(
            f"target_type IN ({_quoted_in_list(_TARGET_TYPES)})",
            name="ck_activity_log_target_type",
        ),
    )
    op.create_index(
        "ix_activity_logs_project_id",
        "activity_logs",
        ["project_id"],
    )
    op.create_index(
        "ix_activity_log_project_created",
        "activity_logs",
        ["project_id", "created_at"],
    )
    op.create_index(
        "ix_activity_log_user_project",
        "activity_logs",
        ["user_id", "project_id"],
    )
    op.create_index(
        "ix_activity_log_target",
        "activity_logs",
        ["target_type", "target_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_activity_log_target", table_name="activity_logs")
    op.drop_index("ix_activity_log_user_project", table_name="activity_logs")
    op.drop_index("ix_activity_log_project_created", table_name="activity_logs")
    op.drop_index("ix_activity_logs_project_id", table_name="activity_logs")
    op.drop_table("activity_logs")
