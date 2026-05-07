"""M02 ProjectService + MemberService (design §6).

事务边界: 所有"产生副作用 + 写 activity_log"的方法用 ``async with db.begin():``
单原子事务包裹 (与 M01 AuthService 范式一致)。

# 实施期处理段 (design §3.X):
# - C 路径 (team_id 写入): service 不校验 team_id 合法性 — DAO 完全允许 (R-X5 子选项实证决:
#   schema 已允许任意 UUID, service 拒会引入双源真相; M20 ALTER 前 data migration reset)
# - A 路径 (SearchConfig owner): get_search_config 返回 api.schemas.project_schema.SearchConfig
#   (M02 own; M18 sprint 期 import M02 schema 符合 M18→M02 分层依赖方向)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.crypto import CryptoKeyError, encrypt
from api.dao.project_dao import (
    DimensionTypeDAO,
    ProjectDAO,
    ProjectDimensionConfigDAO,
    ProjectMemberDAO,
)
from api.errors.exceptions import (
    AiKeyEncryptFailedError,
    MemberAlreadyExistsError,
    MemberCannotRemoveOwnerError,
    MemberNotFoundError,
    PermissionDeniedError,
    ProjectAlreadyArchivedError,
    ProjectArchivedError,
    ProjectNameDuplicateError,
    ProjectNotFoundError,
)
from api.models.project import (
    MemberRole,
    Project,
    ProjectMember,
    ProjectStatus,
)
from api.schemas.project_schema import SearchConfig
from api.services.activity_log_service import write_event


class ProjectService:
    def __init__(self) -> None:
        self.projects = ProjectDAO()
        self.members = ProjectMemberDAO()
        self.dim_configs = ProjectDimensionConfigDAO()
        self.dim_types = DimensionTypeDAO()

    # ─── create / read ───

    async def create_project(
        self,
        db: AsyncSession,
        *,
        owner_id: UUID,
        name: str,
        description: str | None = None,
        template_type: str = "custom",
        hierarchy_labels: list[str] | None = None,
    ) -> Project:
        """事务: INSERT projects + owner ProjectMember + activity_log."""
        try:
            fields: dict[str, Any] = {
                "owner_id": owner_id,
                "name": name,
                "description": description,
                "template_type": template_type,
            }
            if hierarchy_labels is not None:
                fields["hierarchy_labels"] = hierarchy_labels
            proj = await self.projects.create(db, **fields)
            await self.members.create(
                db,
                project_id=proj.id,
                user_id=owner_id,
                role=MemberRole.OWNER.value,
                invited_by=None,
            )
            await write_event(
                db=db,
                actor_user_id=owner_id,
                project_id=proj.id,
                action_type="create",
                target_type="project",
                target_id=str(proj.id),
                summary=f"Created project '{name}'",
                metadata={"template_type": template_type, "name": name},
            )
            await db.flush()
            return proj
        except IntegrityError as e:
            await db.rollback()
            msg = str(e.orig) if e.orig else str(e)
            if "uq_project_owner_name_active" in msg:
                raise ProjectNameDuplicateError(project_name=name) from e
            raise

    async def get_for_user(self, db: AsyncSession, project_id: UUID, user_id: UUID) -> Project:
        """tenant 校验 + raise PROJECT_NOT_FOUND 当非 member."""
        proj = await self.projects.get_by_id_for_user(db, project_id, user_id)
        if proj is None:
            raise ProjectNotFoundError(project_id=str(project_id))
        return proj

    async def list_for_user(
        self, db: AsyncSession, user_id: UUID, *, include_archived: bool = False
    ) -> list[Project]:
        rows = await self.projects.list_by_user(db, user_id, include_archived=include_archived)
        return list(rows)

    # ─── update / archive ───

    async def update_project(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        changes: dict[str, Any],
    ) -> Project:
        """要求 actor 是 owner; 返回更新后的 project. archived project 拒改 (R1 P2-A)."""
        proj, _m = await self.require_owner(db, project_id, actor_user_id)
        if proj.status == ProjectStatus.ARCHIVED.value:
            raise ProjectArchivedError(project_id=str(project_id), reason="cannot_update_archived")

        changed_fields = []
        for key, val in changes.items():
            if val is not None and hasattr(proj, key):
                setattr(proj, key, val)
                changed_fields.append(key)
        await db.flush()
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="update",
            target_type="project",
            target_id=str(project_id),
            summary=f"Updated project (fields: {','.join(changed_fields)})",
            metadata={"changed_fields": changed_fields},
        )
        return proj

    async def archive_project(
        self, db: AsyncSession, *, project_id: UUID, actor_user_id: UUID
    ) -> Project:
        """active → archived; 重复 archive raise PROJECT_ALREADY_ARCHIVED (design §4 R4-2)."""
        proj, _m = await self.require_owner(db, project_id, actor_user_id)
        if proj.status == ProjectStatus.ARCHIVED.value:
            raise ProjectAlreadyArchivedError(project_id=str(project_id))
        proj.status = ProjectStatus.ARCHIVED.value
        await db.flush()
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="archive",
            target_type="project",
            target_id=str(project_id),
            summary=f"Archived project '{proj.name}'",
            metadata={"previous_status": "active"},
        )
        return proj

    # ─── ai provider (含 AES 加密) ───

    async def update_ai_provider(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        ai_provider: str | None,
        ai_api_key: str | None,
    ) -> Project:
        proj, _m = await self.require_owner(db, project_id, actor_user_id)
        proj.ai_provider = ai_provider
        if ai_api_key is not None:
            try:
                proj.ai_api_key_enc = encrypt(ai_api_key)
            except (CryptoKeyError, ValueError) as e:
                raise AiKeyEncryptFailedError() from e
        await db.flush()
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="update_ai_provider",
            target_type="project",
            target_id=str(project_id),
            summary=f"Updated AI provider to '{ai_provider}'",
            metadata={"new_provider": ai_provider},
        )
        return proj

    # ─── M18 baseline-patch caller ───

    async def get_search_config(self, db: AsyncSession, project_id: UUID) -> SearchConfig:
        """M18 SearchService.hybrid_search 入口取 RRF 调优参数 (design §6 M18 baseline-patch).

        无 tenant 过滤 — caller (M18 service) 已在自身路径校验 project 访问权限。
        """
        proj = await self.projects.get_by_id(db, project_id)
        if proj is None:
            raise ProjectNotFoundError(project_id=str(project_id))
        return SearchConfig(rrf_k=proj.rrf_k, similarity_threshold=proj.similarity_threshold)

    # ─── helpers ───

    async def require_owner(
        self, db: AsyncSession, project_id: UUID, user_id: UUID
    ) -> tuple[Project, ProjectMember]:
        """合并 project + membership 一次 JOIN 查询 (R1 E1/E5/E4 修).

        - 非 member → ProjectNotFoundError (R1 P2-A: 与 get_for_user 行为对齐 + 防 enum 攻击)
        - 非 owner → PermissionDeniedError
        返回 (project, member) 元组,caller 不再重复 get_by_id.
        """
        from sqlalchemy import select as _sel

        stmt = (
            _sel(Project, ProjectMember)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(Project.id == project_id, ProjectMember.user_id == user_id)
        )
        result = await db.execute(stmt)
        row = result.one_or_none()
        if row is None:
            raise ProjectNotFoundError(project_id=str(project_id))
        proj, m = row
        if m.role != MemberRole.OWNER.value:
            raise PermissionDeniedError(project_id=str(project_id), role=m.role)
        return proj, m


class MemberService:
    def __init__(self, project_service: ProjectService | None = None) -> None:
        self.members = ProjectMemberDAO()
        # R1 P2-A: 共享 ProjectService 实例 (避免重复构造 4 个 DAO)
        self.projects_svc = project_service or ProjectService()

    async def list_members(
        self, db: AsyncSession, *, project_id: UUID, actor_user_id: UUID
    ) -> list[ProjectMember]:
        # caller-side check_project_access 校验过, 此处直接读
        rows = await self.members.list_by_project(db, project_id)
        return list(rows)

    async def invite_member(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        invited_user_id: UUID,
        role: MemberRole | str = MemberRole.VIEWER,
    ) -> ProjectMember:
        await self.projects_svc.require_owner(db, project_id, actor_user_id)
        role_value = role.value if isinstance(role, MemberRole) else role
        try:
            m = await self.members.create(
                db,
                project_id=project_id,
                user_id=invited_user_id,
                role=role_value,
                invited_by=actor_user_id,
            )
            await write_event(
                db=db,
                actor_user_id=actor_user_id,
                project_id=project_id,
                action_type="invite_member",
                target_type="project_member",
                target_id=str(m.id),
                summary=f"Invited user {invited_user_id} as {role_value}",
                metadata={
                    "project_id": str(project_id),
                    "invited_user_id": str(invited_user_id),
                    "role": role_value,
                },
            )
            return m
        except IntegrityError as e:
            await db.rollback()
            raise MemberAlreadyExistsError(
                project_id=str(project_id), user_id=str(invited_user_id)
            ) from e

    async def update_member_role(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        target_user_id: UUID,
        new_role: MemberRole | str,
    ) -> ProjectMember:
        await self.projects_svc.require_owner(db, project_id, actor_user_id)
        m = await self.members.get_member(db, project_id, target_user_id)
        if m is None:
            raise MemberNotFoundError(project_id=str(project_id), user_id=str(target_user_id))
        new_role_value = new_role.value if isinstance(new_role, MemberRole) else new_role
        if m.role == MemberRole.OWNER.value and new_role_value != MemberRole.OWNER.value:
            # owner 降级 + owner 移除 共用 MemberCannotRemoveOwnerError (R1 P1-A: message 已改宽)
            raise MemberCannotRemoveOwnerError(
                project_id=str(project_id), reason="cannot_demote_owner"
            )
        old_role = m.role
        m.role = new_role_value
        await db.flush()
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="update_member_role",
            target_type="project_member",
            target_id=str(m.id),
            summary=f"Changed role for user {target_user_id}: {old_role} → {new_role_value}",
            metadata={
                "project_id": str(project_id),
                "user_id": str(target_user_id),
                "old_role": old_role,
                "new_role": new_role_value,
            },
        )
        return m

    async def remove_member(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        target_user_id: UUID,
    ) -> int:
        await self.projects_svc.require_owner(db, project_id, actor_user_id)
        m = await self.members.get_member(db, project_id, target_user_id)
        if m is None:
            raise MemberNotFoundError(project_id=str(project_id), user_id=str(target_user_id))
        if m.role == MemberRole.OWNER.value:
            raise MemberCannotRemoveOwnerError(
                project_id=str(project_id),
                user_id=str(target_user_id),
                reason="cannot_remove_owner",
            )
        deleted = await self.members.delete(db, project_id, target_user_id)
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="remove_member",
            target_type="project_member",
            target_id=str(m.id),
            summary=f"Removed user {target_user_id} from project",
            metadata={
                "project_id": str(project_id),
                "removed_user_id": str(target_user_id),
            },
        )
        return deleted
