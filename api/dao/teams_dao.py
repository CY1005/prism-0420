"""M20 DAO（async）+ M20 TenantContext concrete impl（升级 M02 → UNION 形态）。

design/02-modules/M20-team/00-design.md §9 + ADR-005 §3.1。

R-X3 精神：DAO 接受外部 session、不自 commit / 不自 begin。事务由 Service 层
``async with db.begin():`` 包裹（delete_team / transfer_ownership 多表事务）或 Router 层
（单表 CRUD 通过 db_session 默认事务边界）。

DAO 主查询模式（design §9.1）：
- TeamDAO.get_by_id：默认 tenant 过滤（user_id 必须是 team_members 行 / 防 leak）
- TeamDAO.list_for_user：JOIN team_members 反向解析 user 所在所有 team
- TeamMemberDAO.list_for_team：L1 已校验 user 是 team 成员后才进 DAO / 仅 WHERE team_id

# horizontal: 否（M20 own 业务实现）
# owner: M20 (api.dao.teams_dao)
# 范畴: M20 团队 own DAO + TenantContext L3 升级 concrete impl
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.project import ProjectMember
from api.models.teams import Team, TeamMember, TeamRole


class TeamDAO:
    """teams 主表 DAO（design §9.1）。"""

    async def get_by_id(self, db: AsyncSession, team_id: UUID, user_id: UUID) -> Team | None:
        """tenant 过滤：返回 team 仅当 user 是 team 成员（防 leak 存在性）。

        WHERE id=tid AND id IN (SELECT team_id FROM team_members WHERE user_id=:uid)
        """
        stmt = (
            select(Team)
            .where(Team.id == team_id)
            .where(Team.id.in_(select(TeamMember.team_id).where(TeamMember.user_id == user_id)))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_no_tenant(self, db: AsyncSession, team_id: UUID) -> Team | None:
        """无 tenant 过滤（用于 SELECT FOR UPDATE / 内部 service 持锁场景）。

        Caller 必须保证已通过 L1 require_team_access(min_role) 校验。
        """
        result = await db.execute(select(Team).where(Team.id == team_id))
        return result.scalar_one_or_none()

    async def list_for_user(self, db: AsyncSession, user_id: UUID) -> Sequence[Team]:
        """U 所在所有 team（含 member_count 聚合 / design §7.1 GET /api/teams）。

        SELECT teams.*, COUNT(team_members.id) AS member_count
        FROM teams JOIN team_members ON ...
        WHERE teams.id IN (SELECT team_id FROM team_members WHERE user_id=:uid)
        """
        accessible = select(TeamMember.team_id).where(TeamMember.user_id == user_id)
        stmt = select(Team).where(Team.id.in_(accessible)).order_by(Team.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_member_count(self, db: AsyncSession, team_id: UUID) -> int:
        """COUNT(team_members WHERE team_id=:tid) 用于 TeamRead 聚合字段。"""
        result = await db.execute(
            select(func.count(TeamMember.id)).where(TeamMember.team_id == team_id)
        )
        return int(result.scalar_one())

    async def find_by_creator_name(
        self, db: AsyncSession, creator_id: UUID, name: str
    ) -> Team | None:
        """B5b 复用：UniqueConstraint(creator_id, name) 字面 lookup（pre-INSERT 查重 / 但
        DAO 不做 IntegrityError catch / Service 层 try/except 转 TeamNameDuplicateError）。
        """
        result = await db.execute(
            select(Team).where(Team.creator_id == creator_id, Team.name == name)
        )
        return result.scalar_one_or_none()

    async def count_projects_in_team(self, db: AsyncSession, team_id: UUID) -> int:
        """删 team 前置校验：COUNT(projects WHERE team_id=:tid)（B7/B8/E3 / Q8 强制前置迁出）。

        排除 archived project（B14 archived 走豁免路径自动迁出 / 不计入 project_count）。
        """
        from api.models.project import Project, ProjectStatus

        result = await db.execute(
            select(func.count(Project.id)).where(
                Project.team_id == team_id,
                Project.status != ProjectStatus.ARCHIVED.value,
            )
        )
        return int(result.scalar_one())

    async def list_active_project_ids_in_team(
        self, db: AsyncSession, team_id: UUID, limit: int = 10
    ) -> list[UUID]:
        """删 team 失败 detail.project_ids[:10]（design §13 TEAM_HAS_PROJECTS detail schema）。

        排除 archived（同 count_projects_in_team 语义）。
        """
        from api.models.project import Project, ProjectStatus

        result = await db.execute(
            select(Project.id)
            .where(
                Project.team_id == team_id,
                Project.status != ProjectStatus.ARCHIVED.value,
            )
            .limit(limit)
        )
        return [row for row in result.scalars().all()]

    async def list_archived_project_ids_in_team(
        self, db: AsyncSession, team_id: UUID
    ) -> list[UUID]:
        """B14 archived 自动迁出路径：team 删除前列出所有 archived project_id。"""
        from api.models.project import Project, ProjectStatus

        result = await db.execute(
            select(Project.id).where(
                Project.team_id == team_id,
                Project.status == ProjectStatus.ARCHIVED.value,
            )
        )
        return [row for row in result.scalars().all()]


class TeamMemberDAO:
    """team_members 成员表 DAO（design §9.1）。"""

    async def get(self, db: AsyncSession, team_id: UUID, user_id: UUID) -> TeamMember | None:
        """SELECT team_members WHERE team_id=:tid AND user_id=:uid（单行 lookup）。"""
        result = await db.execute(
            select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_for_team(self, db: AsyncSession, team_id: UUID) -> Sequence[TeamMember]:
        """team_members WHERE team_id=:tid（L1 require_team_access 已校验 / 仅 tenant filter team_id）。

        按 joined_at 升序（删 team 写 N+1 条 activity_log 的 N 条顺序契约 / design §10.3）。
        """
        result = await db.execute(
            select(TeamMember)
            .where(TeamMember.team_id == team_id)
            .order_by(TeamMember.joined_at.asc())
        )
        return list(result.scalars().all())

    async def count_owners(self, db: AsyncSession, team_id: UUID) -> int:
        """C2 防 demote 最后 owner / E5 remove 最后 owner 守护：COUNT(role='owner')。

        Service 层 transfer/demote/remove 路径必先调用本方法 + Service.assert_team_has_owner()
        在事务内 SELECT FOR UPDATE 持锁守护（design §5.3）。
        """
        result = await db.execute(
            select(func.count(TeamMember.id)).where(
                TeamMember.team_id == team_id,
                TeamMember.role == TeamRole.OWNER.value,
            )
        )
        return int(result.scalar_one())

    async def get_role_for_user(
        self, db: AsyncSession, team_id: UUID, user_id: UUID
    ) -> TeamRole | None:
        """L2 assert_team_role 用：返回 user 在 team 的 role（None 表示非 member）。"""
        result = await db.execute(
            select(TeamMember.role).where(
                TeamMember.team_id == team_id, TeamMember.user_id == user_id
            )
        )
        role_str = result.scalar_one_or_none()
        if role_str is None:
            return None
        return TeamRole(role_str)


# ─────────────── M20 concrete TenantContext impl（升级 M02 → UNION 形态）───────────────


class M20TenantContext:
    """M20 own：UNION 形态（project_members ∪ projects via team_members 反向解析）。

    design §9.2 字面 + ADR-005 §3.1：M20 lifespan 替换 M02TenantContext，启用 L3 SQL 兜底
    注入。M03-M19 既有 DAO 在 list/get/search 入口引用 user_accessible_project_ids_subquery
    自动获益（不动 DAO 内部 query / 仅升级 helper concrete impl）。

    豁免：M18 embedding backfill DAO 走 ADR-003 规则 4，不引用本 helper（无用户上下文）。

    # horizontal: 否（M20 own 业务实现，注入到横切 helper）
    # owner: M20 (api.dao.teams_dao)
    # 位置: api/dao/teams_dao.py（业务模块层；横切 helper 在 api/auth/tenant_filter.py）
    # 范畴: TenantContextProtocol concrete impl（M20 升级阶段）
    """

    def user_accessible_project_ids_subquery(self, db: Any, user_id: UUID) -> Any:
        """返回 user 可访问的 project_id 子查询（UNION 并集 / design §9.2 line 685-707）。

        并集来源（不去重 — DB 子查询 IN 自动去重）：
          1. project_members WHERE user_id = X        ← M02 已落
          2. projects WHERE team_id IN (SELECT team_id FROM team_members WHERE user_id = X)  ← M20 升级

        返回 SQLAlchemy CTE / .union() select：caller 用 ``IN (subquery)`` 形式。
        """
        from api.models.project import Project

        return (
            select(ProjectMember.project_id)
            .where(ProjectMember.user_id == user_id)
            .union(
                select(Project.id).where(
                    Project.team_id.in_(
                        select(TeamMember.team_id).where(TeamMember.user_id == user_id)
                    )
                )
            )
        )
