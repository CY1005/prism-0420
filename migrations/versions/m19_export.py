"""m19 导入/导出 — ActionType+1 ALTER CHECK constraint（"export"）

Revision ID: m19export01
Revises: m18semsearch01
Create Date: 2026-05-09

M19 是只读聚合导出模块（design §3 字面：无主表）。本 migration 仅扩展
activity_logs.action_type CHECK constraint 以容纳新值 "export"——M19 service
导出完成后调 write_event(action_type="export", target_type="node") 写一条
activity_log（design §10 字面）。

TargetType "node" 已存在于 _TARGET_TYPES tuple line 139（M03 baseline-patch
已落 / 不需 ALTER ck_activity_log_target_type）。

迁移做 2 步：DROP 旧 CHECK constraint + ADD 新 CHECK constraint（含 "export"）。
import _ACTION_TYPES 后字面同步，与 m15/m16r14 alembic 同款 SoT 范式
（M15 横切表 owner enum 4 处同步范式：model tuple + schema StrEnum +
CHECK constraint + Alembic）。
"""

from collections.abc import Sequence

from alembic import op

from api.models.activity_log import _ACTION_TYPES

revision: str = "m19export01"
down_revision: str | Sequence[str] | None = "m18semsearch01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _quoted_in_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    op.drop_constraint("ck_activity_log_action_type", "activity_logs", type_="check")
    op.create_check_constraint(
        "ck_activity_log_action_type",
        "activity_logs",
        f"action_type IN ({_quoted_in_list(_ACTION_TYPES)})",
    )


def downgrade() -> None:
    # 回退到 m18 baseline 的 _ACTION_TYPES（不含 "export"）。注意：若已存在
    # action_type='export' 的行会导致 downgrade 失败——这是设计契约：
    # 回退前需手工清洗 activity_logs 行（DELETE WHERE action_type = 'export'）。
    _OLD_ACTION_TYPES = tuple(v for v in _ACTION_TYPES if v != "export")
    op.drop_constraint("ck_activity_log_action_type", "activity_logs", type_="check")
    op.create_check_constraint(
        "ck_activity_log_action_type",
        "activity_logs",
        f"action_type IN ({_quoted_in_list(_OLD_ACTION_TYPES)})",
    )
