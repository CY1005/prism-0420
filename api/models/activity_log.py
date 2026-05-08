"""M15 activity_log SQLAlchemy 模型（design/02-modules/M15-activity-stream/00-design.md §3）。

横切 owner（R10-2）：M15 拥有 activity_logs 表的 SQLAlchemy model + Alembic 迁移 +
ActionType / TargetType 枚举值集合（CHECK constraint 字面）。所有业务模块（M02-M14 已实装；
M16-M20 后续）通过 api/services/activity_log_service.py 的 write_event(...) 调用本模块。

# horizontal: 是
# owner: M15（design/02-modules/M15-activity-stream/00-design.md，R10-2）
# 范畴: 全模块共享 activity_logs 表 / Action+Target 枚举字面 / Alembic 迁移

设计要点：
- ImmutableMixin（base.py:37）：append-only / 无 updated_at
- project_id NULLABLE：M14 全局豁免业务模块首发（write_event UUID→Optional 升级 / 2026-05-08
  M15 sprint 子片 0 prep baseline-patch 反向回写）；UI 时间线"全局事件"分组
- 三重防护（R3-2）：Python 层 ActionType/TargetType Enum 由 schema 子片 3 引入；
  model 层 Mapped[str] + String(50) + CheckConstraint 字面（M02-M14 11 模块同款范式 /
  避免 model 反向依赖 schema layer 引循环 import）
- metadata 列：SQLAlchemy Base 保留 `metadata` 属性 → Python 属性名 event_metadata（避免冲突）
  + SQL column 名仍是 "metadata"（与 design §3 字面 + write_event stub 字面一致 / DAO 层
  serialize 时 ev["metadata"] 不漂移）
"""

from __future__ import annotations

from typing import Any
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.models.base import Base, ImmutableMixin

# action_type CheckConstraint 枚举值字面（与 schema 子片 3 ActionType Enum 同步 / R10-2 owner 维护）
# baseline-patch 时序：
# - M01-M13 11 模块（2026-04-21 → 2026-05-08）已写入
# - M14 baseline-patch 反向回写（2026-05-08 子片 0 prep / α 路线）：news_* 5 个
# - M18/M20 baseline-patch（2026-04-26）：embedding_* 2 + team_* 10
# 新值扩增流程见 design/02-modules/M15-activity-stream/00-design.md §3
_ACTION_TYPES = (
    # M01 用户账号
    "user_created",
    "user_updated",
    "user_deleted",
    # M02 项目管理
    "project_created",
    "project_updated",
    "project_archived",
    "project_deleted",
    "project_member_invited",
    "project_member_role_updated",
    "project_member_removed",
    "project_dimension_config_updated",
    "project_ai_provider_updated",
    # M03 模块树
    "node_created",
    "node_updated",
    "node_deleted",
    "node_reordered",
    "node_moved",
    # M04 维度记录
    "dimension_record_created",
    "dimension_record_updated",
    "dimension_record_deleted",
    # M05 版本时间线
    "version_record_created",
    "version_record_updated",
    "version_record_deleted",
    "version_record_set_current",  # M16 sprint 子片 0.5 batch（2026-05-08）/ R14 立规对账：M05 set_current 行为
    # M06 竞品
    "competitor_created",
    "competitor_updated",
    "competitor_deleted",
    "competitor_ref_created",
    "competitor_ref_updated",  # M16 sprint 子片 0.5 batch / R14 对账：M06 update_ref 行为
    "competitor_ref_deleted",
    # M07 问题
    "issue_created",
    "issue_updated",
    "issue_deleted",
    "issue_status_changed",
    "issue_unassigned",  # M16 sprint 子片 0.5 batch / R14 对账：M07 unassign assignee 行为
    "issue_orphaned",
    # M08 模块关系
    "module_relation_created",
    "module_relation_updated",  # M16 sprint 子片 0.5 batch / R14 对账：M08 update relation notes 行为
    "module_relation_deleted",
    # M11 冷启动
    "cold_start_created",
    "cold_start_completed",
    "cold_start_failed",
    # M12 对比
    "comparison_snapshot_created",
    "comparison_snapshot_renamed",
    "comparison_snapshot_deleted",
    # M16 AI 快照（§12B 后台 fire-and-forget 子模板首次实战 / 2026-05-09 sprint）
    "ai_snapshot_started",
    "ai_snapshot_completed",
    "ai_snapshot_failed",
    # M14 行业新闻（2026-05-08 baseline-patch 反向回写 α 路线）
    "news_created",
    "news_updated",
    "news_deleted",
    "news_linked",
    "news_unlinked",
    # M17 AI 导入
    "import_created",
    "import_status_changed",
    "import_ai_step_completed",
    "import_review_confirmed",
    "import_batch_inserted",
    "import_canceled",
    "import_failed",
    "import_partial_failed",
    # M18 语义搜索 baseline-patch 2026-04-26
    "embedding_model_upgrade_triggered",
    "embedding_backfill_triggered",
    # M20 团队 baseline-patch 2026-04-26
    "team_created",
    "team_renamed",
    "team_description_changed",
    "team_deleted",
    "team_member_added",
    "team_member_removed",
    "team_member_promoted_admin",
    "team_member_demoted_member",
    "project_joined_team",
    "project_left_team",
)

_TARGET_TYPES = (
    "node",
    "dimension_record",
    "version_record",
    "competitor",
    "competitor_ref",
    "issue",
    "project",
    "project_member",
    "project_dimension_config",
    "module_relation",
    "cold_start_task",
    "comparison_snapshot",
    "ai_snapshot_task",  # M16 AI 快照（2026-05-09 sprint）
    "import_task",
    "team",  # M20 baseline-patch 2026-04-26
    "industry_news",
    "news_node_link",  # M14 baseline-patch 反向回写 2026-05-08
)


def _in_sql_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


class ActivityLog(Base, ImmutableMixin):
    """activity_logs 横切表（design §3 / R10-2 owner = M15）。

    R3-1：含完整 SQLAlchemy class
    R3-2：action_type / target_type 三重防护（Mapped[str] + String(50) + CheckConstraint）
    R3-3：project_id NULLABLE（M14 全局豁免业务模块首发）
    """

    __tablename__ = "activity_logs"
    __table_args__ = (
        Index("ix_activity_log_project_created", "project_id", "created_at"),
        Index("ix_activity_log_user_project", "user_id", "project_id"),
        Index("ix_activity_log_target", "target_type", "target_id"),
        CheckConstraint(
            f"action_type IN ({_in_sql_list(_ACTION_TYPES)})",
            name="ck_activity_log_action_type",
        ),
        CheckConstraint(
            f"target_type IN ({_in_sql_list(_TARGET_TYPES)})",
            name="ck_activity_log_target_type",
        ),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    # SA Base.metadata 名冲突 → Python 属性名 event_metadata + SQL column 名 "metadata"
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    # created_at 由 ImmutableMixin 提供（无 updated_at / append-only 语义）


__all__ = ["ActivityLog", "_ACTION_TYPES", "_TARGET_TYPES"]
