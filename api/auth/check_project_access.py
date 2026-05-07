"""项目访问权限校验横切 helper（horizontal）。

# horizontal: 是
# owner: M02 own (M03-M19 业务模块都通过此 Depends 校验粗粒度 project 访问)
# 位置: api/auth/（横切层，对齐原则 6 + R-X6 + 04-layer Q7）
# 范畴: design §8 权限三层 — Router 粗粒度 (membership/role) 校验

接口契约 (M03-M19 各模块 router 使用):
    @router.get("/api/projects/{pid}/items")
    async def list_items(
        pid: UUID,
        access: ProjectAccess = Depends(check_project_access(role="viewer")),
        db: AsyncSession = Depends(get_db),
    ): ...

role 取值:
    "viewer" — 只要是 member 即通过 (read 入口)
    "editor" — editor / owner 通过 (write 入口)
    "owner"  — 仅 owner 通过 (admin 入口: archive / 邀请 / 删除等)

非 member → ProjectNotFoundError (与 ProjectService.get_for_user 一致, R1 修)
member 但 role 不足 → PermissionDeniedError
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import Depends, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.db import get_db
from api.errors.exceptions import PermissionDeniedError, ProjectNotFoundError
from api.models.project import MemberRole, Project, ProjectMember
from api.models.user import User
from api.routers.auth import current_user

_ROLE_RANK = {
    MemberRole.VIEWER.value: 1,
    MemberRole.EDITOR.value: 2,
    MemberRole.OWNER.value: 3,
}


@dataclass(frozen=True)
class ProjectAccess:
    """Depends 注入 caller 的对象: 含 project + 当前 user 的 role."""

    project: Project
    user: User
    member_role: str


def check_project_access(
    role: str = "viewer",
) -> Callable[..., Coroutine[Any, Any, ProjectAccess]]:
    """FastAPI Depends 工厂,生成校验闭包."""
    required_rank = _ROLE_RANK.get(role, 1)

    async def _dep(
        project_id: UUID = Path(..., alias="project_id"),
        user: User = Depends(current_user),
        db: AsyncSession = Depends(get_db),
    ) -> ProjectAccess:
        stmt = (
            select(Project, ProjectMember)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(Project.id == project_id, ProjectMember.user_id == user.id)
        )
        row = (await db.execute(stmt)).one_or_none()
        if row is None:
            raise ProjectNotFoundError(project_id=str(project_id))
        proj, m = row
        if _ROLE_RANK.get(m.role, 0) < required_rank:
            raise PermissionDeniedError(
                project_id=str(project_id), required_role=role, actual_role=m.role
            )
        return ProjectAccess(project=proj, user=user, member_role=m.role)

    return _dep
