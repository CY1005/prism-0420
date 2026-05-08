"""M15 ActivityStreamService（design §6 + §8 / 纯读 — design §10 字面 N/A activity_log 写）。

design §8 Service 层细粒度权限：
- _check_activity_audit_access(user_id, project_id)：校验 project 存在 + 用户角色 in
  [owner, editor]；不存在/非角色 → ActivityStreamProjectNotFoundError（design line 706
  C-5 候选 β：避免泄露存在性）

design §3 ADR-003 规则 3 横切表豁免：Service 调 DAO 直查 activity_logs + JOIN users
取 user_name；不调任何业务模块 Service。

R10-1 N/A：M15 是纯读模块（design §10 line 728-729 字面 "M15 无 activity_log 事件"）。
本 service 自身不调 write_event。
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dao.activity_stream_dao import ActivityStreamDAO
from api.errors.exceptions import (
    ActivityStreamForbiddenError,
    ActivityStreamProjectNotFoundError,
)
from api.models.activity_log import ActivityLog
from api.models.project import Project, ProjectMember
from api.schemas.activity_stream_schema import (
    ActivityLogItem,
    ActivityStreamFilter,
    ActivityStreamResponse,
)

# design §8 line 700-701 C-5 ack：仅 owner + editor 可审计；viewer 不可
_AUDIT_ALLOWED_ROLES: frozenset[str] = frozenset({"owner", "editor"})


class ActivityStreamService:
    def __init__(self, dao: ActivityStreamDAO | None = None) -> None:
        self.dao = dao or ActivityStreamDAO()

    async def list_stream(
        self,
        db: AsyncSession,
        *,
        actor_user_id: UUID,
        project_id: UUID,
        filt: ActivityStreamFilter,
    ) -> ActivityStreamResponse:
        """主查询入口（design §7 GET /api/projects/{project_id}/activity-stream）。

        路径：
        1. _check_activity_audit_access：project 存在 + actor 角色 owner/editor
        2. DAO list_stream：JOIN users + 强 project_id tenant 过滤 + 多维过滤
        3. 整形 (ActivityLog, user_name) tuple → ActivityLogItem with metadata 字段
           （SA 列名 "metadata" / Python 属性 event_metadata 反向映射）
        4. has_more 判定（D-2：首页 total 精确用 total > page*page_size；后续 page 用
           rows 是否撑满 page_size）
        """
        await self._check_activity_audit_access(db, actor_user_id, project_id)

        rows, total = await self.dao.list_stream(
            db,
            project_id,
            page=filt.page,
            page_size=filt.page_size,
            user_id=filt.user_id,
            action_type=filt.action_type.value if filt.action_type else None,
            target_type=filt.target_type.value if filt.target_type else None,
            from_dt=filt.from_dt,
            to_dt=filt.to_dt,
        )

        items = [self._to_item(ev, user_name) for ev, user_name in rows]

        # has_more：首页 total 精确 → total > page*page_size；后续 page → rows 撑满
        if total is not None:
            has_more = total > filt.page * filt.page_size
        else:
            has_more = len(items) >= filt.page_size

        return ActivityStreamResponse(
            project_id=project_id,
            items=items,
            total=total,
            page=filt.page,
            page_size=filt.page_size,
            has_more=has_more,
        )

    # ─────────── 内部 ───────────

    async def _check_activity_audit_access(
        self, db: AsyncSession, actor_user_id: UUID, project_id: UUID
    ) -> None:
        """design §8 C-5：project 存在 + actor 角色 in [owner, editor]。

        设计选择（design line 706 C-5 候选 β）：viewer / 非成员 / project 不存在 三类
        统一抛 ActivityStreamProjectNotFoundError 不泄露 project 存在性；项目成员
        但 role=viewer → ActivityStreamForbiddenError 403（前端可区分"无项目权限"vs
        "无审计权限"语义）。

        R2 P2-1 注释（2026-05-08 子片 5 关闸）：
        ActivityStreamForbiddenError e2e 路径 **不可达**——Router 层 check_project_access
        (role="editor") rank 系统对 viewer 抢先抛 PermissionDeniedError（403 通用 code），
        本 _check 在 e2e 中永远先经过 router 拦截。本路径仅在 service unit 测中可达
        （test_check_access_viewer_raises_forbidden）。这是 design §8 双层防御范式（非
        dead code）：service 层防御未来 caller 跳过 router 直调（如 Background task /
        admin 后台 / future GraphQL resolver）。与 R1 P1-1 立修的 InvalidFilterError
        "schema 注册无 raise"不同结论：那是真 dead exception；本项是 router 抢先 +
        service 防御未来。
        """
        stmt = (
            select(Project, ProjectMember)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(
                Project.id == project_id,
                ProjectMember.user_id == actor_user_id,
            )
        )
        row = (await db.execute(stmt)).one_or_none()
        if row is None:
            raise ActivityStreamProjectNotFoundError(project_id=str(project_id))
        _, m = row
        if m.role not in _AUDIT_ALLOWED_ROLES:
            raise ActivityStreamForbiddenError(
                project_id=str(project_id),
                actual_role=m.role,
                allowed_roles=sorted(_AUDIT_ALLOWED_ROLES),
            )

    @staticmethod
    def _to_item(ev: ActivityLog, user_name: str) -> ActivityLogItem:
        """SA model → Pydantic：event_metadata（Python 属性）→ metadata（schema 字段）。"""
        data: dict[str, Any] = {
            "id": ev.id,
            "user_id": ev.user_id,
            "user_name": user_name,
            "action_type": ev.action_type,
            "target_type": ev.target_type,
            "target_id": ev.target_id,
            "summary": ev.summary,
            "metadata": ev.event_metadata,
            "created_at": ev.created_at,
        }
        return ActivityLogItem.model_validate(data)
