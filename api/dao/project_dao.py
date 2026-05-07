"""M02 DAO（async）+ M02 TenantContext concrete impl。

R-X3 精神：DAO 接受外部 session、不自 commit / 不自 begin。
事务由 Service 层 ``async with db.begin():`` 包裹。

# 实施期处理段（design §3.X A1）：
# C 路径中间态——本期 ProjectDAO.create 不校验 team_id 合法性
# （teams 表 M20 期才存在；R-X5 子选项「DAO 完全允许」延迟到子片 3 service 拍）。
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.project import (
    DimensionType,
    Project,
    ProjectDimensionConfig,
    ProjectMember,
    ProjectStatus,
)


class ProjectDAO:
    async def list_by_user(
        self, db: AsyncSession, user_id: UUID, *, include_archived: bool = False
    ) -> Sequence[Project]:
        """tenant 过滤：只返回 user 是 member 的 project。

        默认排除 archived（design §9 list_by_user 主查询模式）。
        """
        stmt = (
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == user_id)
            .order_by(Project.created_at.desc())
        )
        if not include_archived:
            stmt = stmt.where(Project.status == ProjectStatus.ACTIVE.value)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_id_for_user(
        self, db: AsyncSession, project_id: UUID, user_id: UUID
    ) -> Project | None:
        """tenant 过滤：仅当 user 是 project member 才返回（含 archived）。"""
        stmt = (
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(Project.id == project_id, ProjectMember.user_id == user_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, db: AsyncSession, project_id: UUID) -> Project | None:
        """无 tenant 过滤——仅供 service 内部已校验权限场景（如 archive 后 reload）。"""
        result = await db.execute(select(Project).where(Project.id == project_id))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, **fields: Any) -> Project:
        proj = Project(**fields)
        db.add(proj)
        await db.flush()
        return proj


class ProjectMemberDAO:
    async def list_by_project(self, db: AsyncSession, project_id: UUID) -> Sequence[ProjectMember]:
        result = await db.execute(
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.created_at.asc())
        )
        return result.scalars().all()

    async def get_member(
        self, db: AsyncSession, project_id: UUID, user_id: UUID
    ) -> ProjectMember | None:
        result = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        user_id: UUID,
        role: str = "viewer",
        invited_by: UUID | None = None,
    ) -> ProjectMember:
        m = ProjectMember(project_id=project_id, user_id=user_id, role=role, invited_by=invited_by)
        db.add(m)
        await db.flush()
        return m

    async def delete(self, db: AsyncSession, project_id: UUID, user_id: UUID) -> int:
        """返回被删除行数（0 = not found）。"""
        result = await db.execute(
            delete(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        await db.flush()
        return result.rowcount or 0


class ProjectDimensionConfigDAO:
    async def list_by_project(
        self, db: AsyncSession, project_id: UUID
    ) -> Sequence[ProjectDimensionConfig]:
        result = await db.execute(
            select(ProjectDimensionConfig)
            .where(ProjectDimensionConfig.project_id == project_id)
            .order_by(ProjectDimensionConfig.sort_order.asc())
        )
        return result.scalars().all()

    async def create(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        dimension_type_id: int,
        enabled: bool = True,
        sort_order: int = 0,
    ) -> ProjectDimensionConfig:
        cfg = ProjectDimensionConfig(
            project_id=project_id,
            dimension_type_id=dimension_type_id,
            enabled=enabled,
            sort_order=sort_order,
        )
        db.add(cfg)
        await db.flush()
        return cfg


class DimensionTypeDAO:
    async def list_all(self, db: AsyncSession) -> Sequence[DimensionType]:
        result = await db.execute(select(DimensionType).order_by(DimensionType.id.asc()))
        return result.scalars().all()

    async def get_by_id(self, db: AsyncSession, type_id: int) -> DimensionType | None:
        result = await db.execute(select(DimensionType).where(DimensionType.id == type_id))
        return result.scalar_one_or_none()


# ─────────────── M02 concrete TenantContext impl ───────────────


class M02TenantContext:
    """M02 own：仅 project_members 形态（design §9 主查询模式）。

    M20 sprint 启动时升级为 UNION（project_members ∪ team_members.team_id 反向解析）。
    详见 api/auth/tenant_filter.py docstring + design/adr/ADR-005-team-extension.md §3.1。

    # horizontal: 否（M02 own 业务实现，注入到横切 helper）
    # owner: M02 (api.dao.project_dao)
    # 位置: api/dao/project_dao.py（业务模块层；横切 helper 在 api/auth/tenant_filter.py）
    # 范畴: TenantContextProtocol concrete impl（M02 阶段）
    """

    def user_accessible_project_ids_subquery(self, db: Any, user_id: UUID) -> Any:
        """返回 user 可访问的 project_id 子查询（含 archived，是否过滤 status 由 caller 决定）。"""
        return select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
