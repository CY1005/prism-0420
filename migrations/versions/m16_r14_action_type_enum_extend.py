"""m16 R14 action_type enum 扩展（M16 sprint 子片 0.5 L1+L3 batch / 2026-05-08）

Revision ID: m16r14enumext01
Revises: m15activity01
Create Date: 2026-05-08

R14 立规对账（M15 design §10 R14 段 / M16 sprint 子片 0.5 batch）：
M16 sprint 启动 reconcile pass 实证 7 业务模块（M02-M08+M11）共 41 处 service 层
write_event 调用裸 CRUD 字符串漂移与 _ACTION_TYPES 元组（过去式）不匹配。立 L1
write_event 调用契约（design §10 R14）+ ci-lint.sh R14 grep 守护 + L3 实证：

- 31+ 处 service action_type 字面机械批量改为过去式（M02 7 / M03 5 / M04 5 / M05 4
  / M06 7 / M07 6 / M08 4 / M11 3）
- 4 个新过去式 enum 值识别 + 入 model._ACTION_TYPES + schema StrEnum + 本迁移
  ALTER CHECK constraint：
  1) version_record_set_current（M05 set_current 行为）
  2) competitor_ref_updated（M06 update_ref 行为）
  3) issue_unassigned（M07 unassign assignee 行为）
  4) module_relation_updated（M08 update relation notes 行为）

迁移做 2 步：DROP 旧 CHECK constraint + ADD 新 CHECK constraint（含 4 个新值）。
import _ACTION_TYPES 后字面同步，与 m15 alembic 同款 SoT 范式。
"""

from collections.abc import Sequence

from alembic import op

from api.models.activity_log import _ACTION_TYPES

revision: str = "m16r14enumext01"
down_revision: str | Sequence[str] | None = "m15activity01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _quoted_in_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    # 重建 CHECK constraint：覆盖 4 个新过去式 enum 值
    op.drop_constraint("ck_activity_log_action_type", "activity_logs", type_="check")
    op.create_check_constraint(
        "ck_activity_log_action_type",
        "activity_logs",
        f"action_type IN ({_quoted_in_list(_ACTION_TYPES)})",
    )


def downgrade() -> None:
    # 回退到 m15 baseline 的 _ACTION_TYPES（不含 4 新值）。注意：若已存在含新值的行
    # 会导致 downgrade 失败——这是设计契约：4 新值是 R14 立规后 service 层 raise 路径，
    # 回退前需手工清洗 activity_logs 行（DELETE WHERE action_type IN (4 新值)）。
    _OLD_ACTION_TYPES = tuple(
        v
        for v in _ACTION_TYPES
        if v
        not in {
            "version_record_set_current",
            "competitor_ref_updated",
            "issue_unassigned",
            "module_relation_updated",
        }
    )
    op.drop_constraint("ck_activity_log_action_type", "activity_logs", type_="check")
    op.create_check_constraint(
        "ck_activity_log_action_type",
        "activity_logs",
        f"action_type IN ({_quoted_in_list(_OLD_ACTION_TYPES)})",
    )
