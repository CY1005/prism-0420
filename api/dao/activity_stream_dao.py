"""M15 activity stream DAO (async) — design/02-modules/M15-activity-stream/00-design.md §3+§9.

R-X3 精神：DAO 接受外部 session，不自 commit / 不自 begin。事务由 Service / Router 控制。

R10-2 owner：M15 拥有 activity_logs 横切表 + ActionType/TargetType 字面 +
本 DAO 是该横切表的唯一展示消费者（其他模块写入走 api/services/activity_log_service.py
write_event；M15 只读）。

ADR-003 规则 3 豁免（design §3 line 192-204）：
M15 直查 activity_logs 横切表 + JOIN users 取 name；不通过各业务模块的"日志接口"，
保留时间顺序连贯性。

tenant 过滤（design §9）：
- list_stream：强制 `WHERE activity_logs.project_id = :project_id` 第一过滤条件
- list_for_team：走 target_type='team' + target_id=team_id 路径（M20 baseline-patch
  F2.5 / 8 类 team_* 事件无 project_id，list_stream 召不回）
- users 表 JOIN 豁免 project_id 过滤（清单 5 全局数据豁免）

D-2 CY ack（design §3 line 380-385）：
首页（offset==0）返回精确 total；后续分页（offset>0）total=None，前端用 has_more 判断。
避免每次全表 COUNT 防百万级日志性能问题。
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.activity_log import ActivityLog
from api.models.user import User


class ActivityStreamDAO:
    """M15 只读 DAO（design §3 ActivityStreamDAO）。

    所有查询：JOIN users 取 user_name + 强 tenant 过滤（design §9）。
    """

    async def list_stream(
        self,
        db: AsyncSession,
        project_id: UUID,
        *,
        page: int = 1,
        page_size: int = 50,
        user_id: UUID | None = None,
        action_type: str | None = None,
        target_type: str | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> tuple[Sequence[tuple[ActivityLog, str]], int | None]:
        """项目操作日志列表（design §7 GET /api/projects/{project_id}/activity-stream）。

        - 第一过滤条件强制 `activity_logs.project_id = project_id`（design §9 防绕过）
        - JOIN users.id == activity_logs.user_id 取 user_name
        - ORDER BY created_at DESC 走 ix_activity_log_project_created 索引
        - 首页 total 精确；后续 page total=None（D-2）
        - page/page_size <= 0 ValueError（M14 R1-C P1-2 范式延续）

        Returns: (rows, total) — rows: list of (ActivityLog, user_name) JOIN 元组
        """
        if page < 1 or page_size < 1:
            raise ValueError(
                f"page and page_size must be >= 1, got page={page} page_size={page_size}"
            )

        base = (
            select(ActivityLog, User.name.label("user_name"))
            .join(User, User.id == ActivityLog.user_id)
            .where(ActivityLog.project_id == project_id)
        )
        if user_id is not None:
            base = base.where(ActivityLog.user_id == user_id)
        if action_type is not None:
            base = base.where(ActivityLog.action_type == action_type)
        if target_type is not None:
            base = base.where(ActivityLog.target_type == target_type)
        if from_dt is not None:
            base = base.where(ActivityLog.created_at >= from_dt)
        if to_dt is not None:
            base = base.where(ActivityLog.created_at <= to_dt)

        total: int | None = None
        if page == 1:
            total_stmt = select(func.count(ActivityLog.id)).where(
                ActivityLog.project_id == project_id,
            )
            if user_id is not None:
                total_stmt = total_stmt.where(ActivityLog.user_id == user_id)
            if action_type is not None:
                total_stmt = total_stmt.where(ActivityLog.action_type == action_type)
            if target_type is not None:
                total_stmt = total_stmt.where(ActivityLog.target_type == target_type)
            if from_dt is not None:
                total_stmt = total_stmt.where(ActivityLog.created_at >= from_dt)
            if to_dt is not None:
                total_stmt = total_stmt.where(ActivityLog.created_at <= to_dt)
            total = int((await db.execute(total_stmt)).scalar_one())

        stmt = (
            base.order_by(desc(ActivityLog.created_at), desc(ActivityLog.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await db.execute(stmt)).all()
        return rows, total

    async def list_for_team(
        self,
        db: AsyncSession,
        team_id: UUID,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[Sequence[tuple[ActivityLog, str]], int | None]:
        """团队 audit 列表（design §3 list_for_team / M20 baseline-patch F2.5）。

        team_* 事件 8/10 类（target_type='team' 且无 project_id）；list_stream 召不回。
        本入口走 target_type+target_id 路径。

        L1 require_team_access(member) 由 Router 层校验（M20 sprint 注入实现）；
        本 DAO 仅读 activity_logs。
        """
        if page < 1 or page_size < 1:
            raise ValueError(
                f"page and page_size must be >= 1, got page={page} page_size={page_size}"
            )

        team_id_str = str(team_id)
        base = (
            select(ActivityLog, User.name.label("user_name"))
            .join(User, User.id == ActivityLog.user_id)
            .where(
                ActivityLog.target_type == "team",
                ActivityLog.target_id == team_id_str,
            )
        )

        total: int | None = None
        if page == 1:
            total_stmt = select(func.count(ActivityLog.id)).where(
                ActivityLog.target_type == "team",
                ActivityLog.target_id == team_id_str,
            )
            total = int((await db.execute(total_stmt)).scalar_one())

        stmt = (
            base.order_by(desc(ActivityLog.created_at), desc(ActivityLog.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await db.execute(stmt)).all()
        return rows, total
