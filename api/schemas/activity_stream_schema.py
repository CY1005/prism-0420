"""M15 activity stream Pydantic schema (design §7)。

ActionType / TargetType Enum：与 api/models/activity_log.py 中的 _ACTION_TYPES /
_TARGET_TYPES 字面同步（R10-2 owner 维护 / 字符串值一致）。

design §7 字面：
- ActivityStreamFilter（GET 查询参数 / model_validator from_dt <= to_dt）
- ActivityLogItem（单条响应）
- ActivityStreamResponse（分页响应 / total | None D-2 / has_more）

A1 命名规范（08-namespaces.md §2.1）：{entity}_{past_verb} snake_case 过去式；禁通用
CRUD（M14 baseline-patch 反向回写 2026-05-08 / α 路线 5 个过去式与 M01-M13 11 模块统一）。
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ActionType(StrEnum):
    """全集枚举（R10-2 owner = M15）；新值扩增流程见 design §3。"""

    # M01 用户账号
    user_created = "user_created"
    user_updated = "user_updated"
    user_deleted = "user_deleted"
    # M02 项目管理
    project_created = "project_created"
    project_updated = "project_updated"
    project_archived = "project_archived"
    project_deleted = "project_deleted"
    project_member_invited = "project_member_invited"
    project_member_role_updated = "project_member_role_updated"
    project_member_removed = "project_member_removed"
    project_dimension_config_updated = "project_dimension_config_updated"
    project_ai_provider_updated = "project_ai_provider_updated"
    # M03 模块树
    node_created = "node_created"
    node_updated = "node_updated"
    node_deleted = "node_deleted"
    node_reordered = "node_reordered"
    node_moved = "node_moved"
    # M04 维度记录
    dimension_record_created = "dimension_record_created"
    dimension_record_updated = "dimension_record_updated"
    dimension_record_deleted = "dimension_record_deleted"
    # M05 版本时间线
    version_record_created = "version_record_created"
    version_record_updated = "version_record_updated"
    version_record_deleted = "version_record_deleted"
    version_record_set_current = (
        "version_record_set_current"  # M16 sprint 子片 0.5 batch / R14 对账
    )
    # M06 竞品
    competitor_created = "competitor_created"
    competitor_updated = "competitor_updated"
    competitor_deleted = "competitor_deleted"
    competitor_ref_created = "competitor_ref_created"
    competitor_ref_updated = "competitor_ref_updated"  # M16 sprint 子片 0.5 batch / R14 对账
    competitor_ref_deleted = "competitor_ref_deleted"
    # M07 问题
    issue_created = "issue_created"
    issue_updated = "issue_updated"
    issue_deleted = "issue_deleted"
    issue_status_changed = "issue_status_changed"
    issue_unassigned = "issue_unassigned"  # M16 sprint 子片 0.5 batch / R14 对账
    issue_orphaned = "issue_orphaned"
    # M08 模块关系
    module_relation_created = "module_relation_created"
    module_relation_updated = "module_relation_updated"  # M16 sprint 子片 0.5 batch / R14 对账
    module_relation_deleted = "module_relation_deleted"
    # M11 冷启动
    cold_start_created = "cold_start_created"
    cold_start_completed = "cold_start_completed"
    cold_start_failed = "cold_start_failed"
    # M12 对比
    comparison_snapshot_created = "comparison_snapshot_created"
    comparison_snapshot_renamed = "comparison_snapshot_renamed"
    comparison_snapshot_deleted = "comparison_snapshot_deleted"
    # M16 AI 快照（§12B 后台 fire-and-forget / 2026-05-09 sprint）
    ai_snapshot_started = "ai_snapshot_started"
    ai_snapshot_completed = "ai_snapshot_completed"
    ai_snapshot_failed = "ai_snapshot_failed"
    # M14 行业新闻 (baseline-patch 2026-05-08 / α 路线)
    news_created = "news_created"
    news_updated = "news_updated"
    news_deleted = "news_deleted"
    news_linked = "news_linked"
    news_unlinked = "news_unlinked"
    # M17 AI 导入
    import_created = "import_created"
    import_status_changed = "import_status_changed"
    import_ai_step_completed = "import_ai_step_completed"
    import_review_confirmed = "import_review_confirmed"
    import_batch_inserted = "import_batch_inserted"
    import_canceled = "import_canceled"
    import_failed = "import_failed"
    import_partial_failed = "import_partial_failed"
    # M18 语义搜索 (baseline-patch 2026-04-26)
    embedding_model_upgrade_triggered = "embedding_model_upgrade_triggered"
    embedding_backfill_triggered = "embedding_backfill_triggered"
    # M20 团队 (baseline-patch 2026-04-26)
    team_created = "team_created"
    team_renamed = "team_renamed"
    team_description_changed = "team_description_changed"
    team_deleted = "team_deleted"
    team_member_added = "team_member_added"
    team_member_removed = "team_member_removed"
    team_member_promoted_admin = "team_member_promoted_admin"
    team_member_demoted_member = "team_member_demoted_member"
    project_joined_team = "project_joined_team"
    project_left_team = "project_left_team"
    # M19 导入/导出（2026-05-09 sprint / R1 立修：M16 R14 过去式立规精神对齐 / design §10 回写 "exported"）
    exported = "exported"


class TargetType(StrEnum):
    node = "node"
    dimension_record = "dimension_record"
    version_record = "version_record"
    competitor = "competitor"
    competitor_ref = "competitor_ref"
    issue = "issue"
    project = "project"
    project_member = "project_member"
    project_dimension_config = "project_dimension_config"
    module_relation = "module_relation"
    cold_start_task = "cold_start_task"
    comparison_snapshot = "comparison_snapshot"
    ai_snapshot_task = "ai_snapshot_task"  # M16 AI 快照（2026-05-09 sprint）
    import_task = "import_task"
    team = "team"  # M20 baseline-patch 2026-04-26
    industry_news = "industry_news"  # M14 baseline-patch 2026-05-08
    news_node_link = "news_node_link"  # M14 baseline-patch 2026-05-08


class ActivityStreamFilter(BaseModel):
    """GET 查询参数（query string）—— design §7 字面。

    M15-B4 修复：from_dt > to_dt 触发 ActivityStreamInvalidFilterError（service 层 raise；
    schema 层 model_validator 提前抛 422 由 FastAPI ValidationException Handler 处理）。
    """

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)
    user_id: UUID | None = None
    action_type: ActionType | None = None
    target_type: TargetType | None = None
    from_dt: datetime | None = None
    to_dt: datetime | None = None

    @model_validator(mode="after")
    def check_time_range(self) -> ActivityStreamFilter:
        """R1 P1-1 立修（2026-05-08）：原裸 ``ValueError`` → 业务 code
        ``ActivityStreamInvalidFilterError``。

        design §13 把 ``ACTIVITY_STREAM_INVALID_FILTER`` 列为 M15 own ErrorCode 之一；
        裸 ValueError 经 FastAPI 转 422 但响应 code 字段是通用 ``validation_error``，
        丢失业务语义。改用自定义 Error → AppError 子类 → 响应 ``code`` 字段为
        ``activity_stream_invalid_filter``（与 design §13 字面一致）。
        """
        if self.from_dt and self.to_dt and self.from_dt > self.to_dt:
            # 局部 import 避循环：errors → schemas 不能反向（schemas → errors 单向）
            from api.errors.exceptions import ActivityStreamInvalidFilterError

            raise ActivityStreamInvalidFilterError(
                from_dt=self.from_dt.isoformat(),
                to_dt=self.to_dt.isoformat(),
            )
        return self


class ActivityLogItem(BaseModel):
    """单条操作日志（design §7 字面）。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    user_name: str  # JOIN users.name
    action_type: ActionType
    target_type: TargetType
    target_id: str
    summary: str
    metadata: dict[str, Any] | None = None  # 与 design §7 字面 + write_event stub 一致
    created_at: datetime


class ActivityStreamResponse(BaseModel):
    """项目操作日志分页响应（design §7 字面）。

    D-2 CY ack：首页（page=1）total 精确；后续 page total=None；前端用 has_more 判断。
    """

    project_id: UUID
    items: list[ActivityLogItem]
    total: int | None
    page: int
    page_size: int
    has_more: bool
