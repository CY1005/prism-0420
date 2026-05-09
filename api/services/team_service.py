"""M20 TeamService — design/02-modules/M20-team/00-design.md §6 + §8 + §8.7 + §10。

业务能力：
  - create_team (G1 + B11)：单事务原子 INSERT teams + INSERT team_members(creator=owner) +
    write 2 events (team_created + team_member_added)
  - get_team (T1)：tenant 过滤（防 leak 存在性 / DAO.get_by_id）
  - list_for_user (G10)：返回 user 所在所有 team + member_count 聚合
  - update_team (G5)：name / description PATCH + version 乐观锁 + write 1-2 events
    （team_renamed / team_description_changed / Q10.1② 拆分）
  - delete_team (G8 + R-X3 5-step)：design §8.7 字面 + B14 archived 双路径
  - add_member (G2)：UniqueConstraint catch → TeamMemberDuplicateError + write event
  - update_member_role (G3 / state machine)：状态机 4 条禁止转换 + assert_team_has_owner 守护
  - remove_member (G9 软切断)：activity_log 含 residual_project_count（F2.4）
  - transfer_ownership (G4 + R-X3)：design §8.7 字面 6-step + version++
  - move_project_team (G6 / G7 / B13 / B14)：cross-team 拒绝 + archived 源头拒
  - resolve_project_role (Q1=B 嵌套 max + Q2=B 三角色映射)：design §8.6 字面 + R-X3 跨模块只读

事务边界（design §8.7 R-X3 共享外部 session）：
  delete_team / transfer_ownership 是 M20 仅有的两个跨步骤事务，Service 方法签名显式
  接受外部 ``db: AsyncSession``，由 Router 层的 transaction context（FastAPI 隐式事务边界）
  持有 commit/rollback 权 —— 不在本方法内 commit。

权限三层（design §8.1 + §8.6）：
  L1 Router require_team_access(min_role) 粗校验
  L2 Service assert_team_role(user, team_id, required: TeamRole) 精校验
  L3 SQL 兜底（M20TenantContext UNION 已注入 lifespan / M03-M19 自动获益）

R-X3 跨模块只读：
  - resolve_project_role 调 M02 ProjectMember + Project 表（design §8.6 字面 / 不引入 M02 service）
  - move_project_team 校验 archived project status（design §1 边界灰区 F2.3 双路径）
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.dao.teams_dao import TeamDAO, TeamMemberDAO
from api.errors.exceptions import (
    CrossTeamMoveForbiddenError,
    PermissionDeniedError,
    ProjectArchivedError,
    TeamHasProjectsError,
    TeamMemberDuplicateError,
    TeamMemberNotFoundError,
    TeamNameDuplicateError,
    TeamNotFoundError,
    TeamOwnerRequiredError,
    TeamPermissionDeniedError,
)
from api.models.project import MemberRole, Project, ProjectMember, ProjectStatus
from api.models.teams import Team, TeamMember, TeamRole
from api.services.activity_log_service import write_event

# action_type 字面（design §10.1 / R14 全过去式 + snake_case）
ACTION_TEAM_CREATED = "team_created"
ACTION_TEAM_RENAMED = "team_renamed"
ACTION_TEAM_DESC_CHANGED = "team_description_changed"
ACTION_TEAM_DELETED = "team_deleted"
ACTION_MEMBER_ADDED = "team_member_added"
ACTION_MEMBER_REMOVED = "team_member_removed"
ACTION_MEMBER_PROMOTED = "team_member_promoted_admin"
ACTION_MEMBER_DEMOTED = "team_member_demoted_member"
ACTION_PROJECT_JOINED = "project_joined_team"
ACTION_PROJECT_LEFT = "project_left_team"
TARGET_TEAM = "team"
TARGET_PROJECT = "project"


# Q2=B 三角色映射 owner/admin/member → owner/editor/viewer（design §8.6）
_TEAM_TO_PROJECT_ROLE = {
    TeamRole.OWNER: MemberRole.OWNER,
    TeamRole.ADMIN: MemberRole.EDITOR,
    TeamRole.MEMBER: MemberRole.VIEWER,
}
# 角色优先级（owner > editor > viewer）
_PROJECT_ROLE_PRIORITY = {
    MemberRole.OWNER: 3,
    MemberRole.EDITOR: 2,
    MemberRole.VIEWER: 1,
}
# Team role 优先级（owner > admin > member）— L2 assert_team_role 用
_TEAM_ROLE_PRIORITY = {
    TeamRole.OWNER: 3,
    TeamRole.ADMIN: 2,
    TeamRole.MEMBER: 1,
}


class TeamService:
    """M20 团队 service。"""

    def __init__(
        self,
        team_dao: TeamDAO | None = None,
        member_dao: TeamMemberDAO | None = None,
    ) -> None:
        self.team_dao = team_dao or TeamDAO()
        self.member_dao = member_dao or TeamMemberDAO()

    # ─────────────── L2 内部校验 ───────────────

    async def assert_team_role(
        self,
        db: AsyncSession,
        user_id: UUID,
        team_id: UUID,
        required: TeamRole,
    ) -> TeamRole:
        """L2 精校验：user 在 team 的 role >= required；返回 user 当前 role。

        - user 不在 team_members → TeamNotFoundError(404)（防 leak / 与 P15 / T1 对齐）
        - user role < required → TeamPermissionDeniedError(403)（P11/P12/P15）
        """
        role = await self.member_dao.get_role_for_user(db, team_id, user_id)
        if role is None:
            raise TeamNotFoundError(team_id=str(team_id))
        if _TEAM_ROLE_PRIORITY[role] < _TEAM_ROLE_PRIORITY[required]:
            raise TeamPermissionDeniedError(required_role=required.value, current_role=role.value)
        return role

    async def _get_team_or_raise(self, db: AsyncSession, team_id: UUID, user_id: UUID) -> Team:
        team = await self.team_dao.get_by_id(db, team_id, user_id)
        if team is None:
            raise TeamNotFoundError(team_id=str(team_id))
        return team

    # ─────────────── G1 / B11 创建 team ───────────────

    async def create_team(
        self,
        db: AsyncSession,
        actor_id: UUID,
        name: str,
        description: str | None,
    ) -> Team:
        """单事务原子：INSERT teams + INSERT team_members(creator=owner) + 2 activity_log。

        IntegrityError catch：UniqueConstraint(creator_id, name) 违反 → TeamNameDuplicateError(409)。
        """
        team = Team(
            id=uuid4(),
            creator_id=actor_id,
            name=name,
            description=description,
            version=1,
        )
        db.add(team)
        try:
            await db.flush()
        except IntegrityError as e:
            if "uq_teams_creator_name" in str(e.orig):
                raise TeamNameDuplicateError(name=name, creator_id=str(actor_id)) from e
            raise

        # creator 自动成为 owner（B11 单事务原子）
        member = TeamMember(
            id=uuid4(),
            team_id=team.id,
            user_id=actor_id,
            role=TeamRole.OWNER.value,
        )
        db.add(member)
        await db.flush()

        # write 2 events（team_created + team_member_added / 单事务）
        correlation_id = str(uuid4())
        await write_event(
            db=db,
            actor_user_id=actor_id,
            project_id=None,  # team 是 project tenant 之外的实体（design §10）
            action_type=ACTION_TEAM_CREATED,
            target_type=TARGET_TEAM,
            target_id=str(team.id),
            summary=f"创建了团队『{team.name}』",
            metadata={
                "name": team.name,
                "description": team.description,
                "correlation_id": correlation_id,
            },
        )
        await write_event(
            db=db,
            actor_user_id=actor_id,
            project_id=None,
            action_type=ACTION_MEMBER_ADDED,
            target_type=TARGET_TEAM,
            target_id=str(team.id),
            summary=f"加入了团队『{team.name}』",
            metadata={
                "user_id": str(actor_id),
                "role": TeamRole.OWNER.value,
                "correlation_id": correlation_id,
            },
        )
        return team

    # ─────────────── T1 / G10 read ───────────────

    async def get_team(self, db: AsyncSession, team_id: UUID, user_id: UUID) -> Team:
        return await self._get_team_or_raise(db, team_id, user_id)

    async def list_for_user(self, db: AsyncSession, user_id: UUID) -> list[tuple[Team, int]]:
        """返回 (team, member_count) 列表 / TeamRead 聚合字段。"""
        teams = await self.team_dao.list_for_user(db, user_id)
        result: list[tuple[Team, int]] = []
        for team in teams:
            count = await self.team_dao.get_member_count(db, team.id)
            result.append((team, count))
        return result

    # ─────────────── G5 update name / description ───────────────

    async def update_team(
        self,
        db: AsyncSession,
        actor_id: UUID,
        team_id: UUID,
        version: int,
        name: str | None,
        description: str | None,
    ) -> Team:
        """L2 assert admin + 乐观锁 + Q10.1② 拆分事件（renamed / description_changed）。"""
        await self.assert_team_role(db, actor_id, team_id, TeamRole.ADMIN)
        team = await self._get_team_or_raise(db, team_id, actor_id)
        if team.version != version:
            from api.errors.exceptions import ConflictError

            raise ConflictError(
                resource="team",
                expected_version=version,
                current_version=team.version,
            )

        events: list[tuple[str, dict]] = []
        if name is not None and name != team.name:
            events.append(
                (
                    ACTION_TEAM_RENAMED,
                    {"from_name": team.name, "to_name": name},
                )
            )
            team.name = name
        if description is not None and description != team.description:
            events.append(
                (
                    ACTION_TEAM_DESC_CHANGED,
                    {
                        "from_description": team.description,
                        "to_description": description,
                    },
                )
            )
            team.description = description
        team.version += 1

        try:
            await db.flush()
        except IntegrityError as e:
            await db.rollback()
            if "uq_teams_creator_name" in str(e.orig) and name is not None:
                raise TeamNameDuplicateError(name=name, creator_id=str(team.creator_id)) from e
            raise

        correlation_id = str(uuid4())
        for action, meta in events:
            await write_event(
                db=db,
                actor_user_id=actor_id,
                project_id=None,
                action_type=action,
                target_type=TARGET_TEAM,
                target_id=str(team.id),
                summary=f"更新了团队『{team.name}』",
                metadata={**meta, "correlation_id": correlation_id},
            )
        return team

    # ─────────────── G8 + R-X3 5-step delete ───────────────

    async def delete_team(
        self,
        db: AsyncSession,
        actor_id: UUID,
        team_id: UUID,
    ) -> None:
        """删 team 5-step（design §8.7 字面 / R10-1 N+1 条独立事件 / B14 archived 双路径）。

        1. assert owner + 校验 projects 非 archived 必须为空（B7/B8/E3）
        2. archived projects 自动迁出（B14 / project_left_team detail.reason="team_deleted_archived_auto_unbind"）
        3. 列出 N 个 team_members + 写 1 条 team_deleted + N 条 team_member_removed (reason="team_deleted")
        4. DELETE team_members WHERE team_id (N 行)
        5. DELETE teams WHERE id (1 行)
        """
        await self.assert_team_role(db, actor_id, team_id, TeamRole.OWNER)
        team = await self._get_team_or_raise(db, team_id, actor_id)

        # 1+2: 校验 projects 空（active 路径）+ archived 自动迁出
        active_count = await self.team_dao.count_projects_in_team(db, team_id)
        if active_count > 0:
            project_ids = await self.team_dao.list_active_project_ids_in_team(db, team_id)
            raise TeamHasProjectsError(
                team_id=str(team_id),
                project_count=active_count,
                project_ids=[str(pid) for pid in project_ids],
            )

        correlation_id = str(uuid4())

        # B14 archived 自动迁出
        archived_ids = await self.team_dao.list_archived_project_ids_in_team(db, team_id)
        for pid in archived_ids:
            proj = await db.get(Project, pid)
            if proj is not None:
                proj.team_id = None
                await write_event(
                    db=db,
                    actor_user_id=actor_id,
                    project_id=pid,
                    action_type=ACTION_PROJECT_LEFT,
                    target_type=TARGET_PROJECT,
                    target_id=str(pid),
                    summary=f"项目自动从团队『{team.name}』迁出（团队删除豁免路径）",
                    metadata={
                        "from_team_id": str(team_id),
                        "reason": "team_deleted_archived_auto_unbind",
                        "correlation_id": correlation_id,
                    },
                )

        # 3: 列 N 个 members + 写 1 + N 条 activity_log（按 joined_at ASC / R10-1 独立）
        members = await self.member_dao.list_for_team(db, team_id)
        team_name = team.name
        member_count = len(members)

        await write_event(
            db=db,
            actor_user_id=actor_id,
            project_id=None,
            action_type=ACTION_TEAM_DELETED,
            target_type=TARGET_TEAM,
            target_id=str(team_id),
            summary=f"删除了团队『{team_name}』",
            metadata={
                "name": team_name,
                "member_count": member_count,
                "correlation_id": correlation_id,
            },
        )
        for m in members:
            # F2.4 软切断 audit：member_removed 必填 residual_project_count + residual_project_ids[:10]
            residual_pms = await db.execute(
                select(ProjectMember.project_id)
                .join(Project, Project.id == ProjectMember.project_id)
                .where(ProjectMember.user_id == m.user_id)
                .where(Project.team_id == team_id)
                .limit(10)
            )
            residual_ids = [str(r) for r in residual_pms.scalars().all()]
            await write_event(
                db=db,
                actor_user_id=actor_id,
                project_id=None,
                action_type=ACTION_MEMBER_REMOVED,
                target_type=TARGET_TEAM,
                target_id=str(team_id),
                summary=f"成员从团队『{team_name}』被移除（团队删除）",
                metadata={
                    "user_id": str(m.user_id),
                    "reason": "team_deleted",
                    "residual_project_count": len(residual_ids),
                    "residual_project_ids": residual_ids,
                    "correlation_id": correlation_id,
                },
            )

        # 4+5: DELETE team_members 后 DELETE teams（顺序由 RESTRICT FK 强制）
        for m in members:
            await db.delete(m)
        await db.flush()
        await db.delete(team)
        await db.flush()

    # ─────────────── G2 add member ───────────────

    async def add_member(
        self,
        db: AsyncSession,
        actor_id: UUID,
        team_id: UUID,
        user_id: UUID,
        role: TeamRole,
    ) -> TeamMember:
        """L2 assert admin + UniqueConstraint catch + activity_log。"""
        await self.assert_team_role(db, actor_id, team_id, TeamRole.ADMIN)
        team = await self._get_team_or_raise(db, team_id, actor_id)
        # 不允许直接加 owner（schema Literal 限 admin/member）/ Service 兜底
        if role == TeamRole.OWNER:
            raise TeamPermissionDeniedError(required_role="admin", current_role="member")
        member = TeamMember(
            id=uuid4(),
            team_id=team_id,
            user_id=user_id,
            role=role.value,
        )
        db.add(member)
        try:
            await db.flush()
        except IntegrityError as e:
            if "uq_team_members_team_user" in str(e.orig):
                raise TeamMemberDuplicateError(team_id=str(team_id), user_id=str(user_id)) from e
            raise
        await write_event(
            db=db,
            actor_user_id=actor_id,
            project_id=None,
            action_type=ACTION_MEMBER_ADDED,
            target_type=TARGET_TEAM,
            target_id=str(team_id),
            summary=f"成员加入了团队『{team.name}』",
            metadata={
                "user_id": str(user_id),
                "role": role.value,
            },
        )
        return member

    # ─────────────── G3 update_member_role / 状态机 4 条禁止转换 ───────────────

    async def update_member_role(
        self,
        db: AsyncSession,
        actor_id: UUID,
        team_id: UUID,
        target_user_id: UUID,
        new_role: TeamRole,
    ) -> TeamMember:
        """状态机 4 条禁止转换（design §4.2）：

        1. owner → [*]：team_member_removed 拒（last_owner_remove）— 在 remove_member
        2. member → owner：禁止跨级直升（new_role=owner 时 / Pydantic Literal 已限 / Service 兜底）
        3. owner → admin（非 transfer 场景）：直降拒 → last_owner_demote（仅 1 owner 时）
        4. owner → member（直降）：拒 / Pydantic Literal 已限 / Service 兜底

        合规路径：member → admin / admin → member / 经 transfer_ownership 流程换 owner
        """
        await self.assert_team_role(db, actor_id, team_id, TeamRole.ADMIN)
        member = await self.member_dao.get(db, team_id, target_user_id)
        if member is None:
            raise TeamMemberNotFoundError(team_id=str(team_id), user_id=str(target_user_id))

        current_role = TeamRole(member.role)

        # 状态机禁止转换 #2：member → owner（schema Literal 已限 / Service 兜底）
        if new_role == TeamRole.OWNER:
            raise TeamPermissionDeniedError(required_role="admin", current_role=current_role.value)

        # 状态机禁止转换 #3+#4：owner → admin/member（非 transfer 场景）
        if current_role == TeamRole.OWNER:
            owner_count = await self.member_dao.count_owners(db, team_id)
            if owner_count <= 1:
                # 最后一个 owner / 必须走 transfer 流程
                raise TeamOwnerRequiredError(reason="last_owner_demote")
            # 即使有多个 owner，也禁止"直降"（设计契约：owner 角色变更必须走 transfer 流程）
            raise TeamOwnerRequiredError(reason="last_owner_demote")

        # 合规：member ↔ admin
        old_role = current_role
        member.role = new_role.value
        await db.flush()

        action = (
            ACTION_MEMBER_PROMOTED
            if _TEAM_ROLE_PRIORITY[new_role] > _TEAM_ROLE_PRIORITY[old_role]
            else ACTION_MEMBER_DEMOTED
        )
        await write_event(
            db=db,
            actor_user_id=actor_id,
            project_id=None,
            action_type=action,
            target_type=TARGET_TEAM,
            target_id=str(team_id),
            summary=f"成员角色变更：{old_role.value} → {new_role.value}",
            metadata={
                "user_id": str(target_user_id),
                "from_role": old_role.value,
                "to_role": new_role.value,
            },
        )
        return member

    # ─────────────── G9 软切断 remove_member ───────────────

    async def remove_member(
        self,
        db: AsyncSession,
        actor_id: UUID,
        team_id: UUID,
        target_user_id: UUID,
    ) -> dict:
        """软切断（Q3=A）：删 team_members 不级联清 ProjectMember + 响应附 residual 列表。

        E5 守护：拒移除最后 owner（last_owner_remove）。
        """
        await self.assert_team_role(db, actor_id, team_id, TeamRole.ADMIN)
        member = await self.member_dao.get(db, team_id, target_user_id)
        if member is None:
            raise TeamMemberNotFoundError(team_id=str(team_id), user_id=str(target_user_id))

        # E5：移除最后 owner 拒
        if member.role == TeamRole.OWNER.value:
            owner_count = await self.member_dao.count_owners(db, team_id)
            if owner_count <= 1:
                raise TeamOwnerRequiredError(reason="last_owner_remove")

        # F2.4 residual ProjectMember 列表
        residual = await db.execute(
            select(ProjectMember.project_id)
            .join(Project, Project.id == ProjectMember.project_id)
            .where(ProjectMember.user_id == target_user_id)
            .where(Project.team_id == team_id)
        )
        residual_ids: list[UUID] = list(residual.scalars().all())

        await db.delete(member)
        await db.flush()

        await write_event(
            db=db,
            actor_user_id=actor_id,
            project_id=None,
            action_type=ACTION_MEMBER_REMOVED,
            target_type=TARGET_TEAM,
            target_id=str(team_id),
            summary="成员从团队中移除",
            metadata={
                "user_id": str(target_user_id),
                "reason": "manual",
                "residual_project_count": len(residual_ids),
                "residual_project_ids": [str(pid) for pid in residual_ids[:10]],
            },
        )
        return {
            "removed_user_id": target_user_id,
            "residual_project_members": residual_ids,
            "residual_count": len(residual_ids),
        }

    # ─────────────── G4 + R-X3 transfer_ownership ───────────────

    async def transfer_ownership(
        self,
        db: AsyncSession,
        actor_id: UUID,
        team_id: UUID,
        new_owner_id: UUID,
    ) -> None:
        """转让 owner 流程（design §8.7 字面 / 单事务原子 / 2 条 activity_log）。

        1. assert actor 是 owner + assert new_owner ∈ team_members
        2. assert new_owner != actor（B4 / target_is_self）
        3. UPDATE actor → admin / new_owner → owner（同事务）
        4. write 2 events (demoted + promoted) 同 correlation_id
        5. UPDATE teams.version += 1（防 C1 并发 transfer）
        """
        await self.assert_team_role(db, actor_id, team_id, TeamRole.OWNER)

        # B4：拒 transfer 给自己
        if new_owner_id == actor_id:
            raise TeamOwnerRequiredError(reason="target_is_self")

        # E6：new_owner 必须是 team_members
        new_member = await self.member_dao.get(db, team_id, new_owner_id)
        if new_member is None:
            raise TeamOwnerRequiredError(reason="transfer_target_not_member")

        # actor (current owner)
        actor_member = await self.member_dao.get(db, team_id, actor_id)
        # actor_member 不可能为 None（assert_team_role 已通过 owner 校验）
        assert actor_member is not None

        # 同事务原子：先 demote actor 后 promote new_owner（B4 已挡 self / role 升序避免临时双 owner）
        actor_member.role = TeamRole.ADMIN.value
        new_member.role = TeamRole.OWNER.value
        await db.flush()

        # version += 1（防 C1 并发 transfer）
        team = await self._get_team_or_raise(db, team_id, actor_id)
        team.version += 1
        await db.flush()

        correlation_id = str(uuid4())
        # 2 events 同事务（design §10.1 注释：to_role 含 admin 或 owner）
        await write_event(
            db=db,
            actor_user_id=actor_id,
            project_id=None,
            action_type=ACTION_MEMBER_DEMOTED,
            target_type=TARGET_TEAM,
            target_id=str(team_id),
            summary="原 owner 降级为 admin（transfer ownership 流程）",
            metadata={
                "user_id": str(actor_id),
                "from_role": TeamRole.OWNER.value,
                "to_role": TeamRole.ADMIN.value,
                "correlation_id": correlation_id,
            },
        )
        await write_event(
            db=db,
            actor_user_id=actor_id,
            project_id=None,
            action_type=ACTION_MEMBER_PROMOTED,
            target_type=TARGET_TEAM,
            target_id=str(team_id),
            summary="新 owner 升级（transfer ownership 流程）",
            metadata={
                "user_id": str(new_owner_id),
                "from_role": new_member.role
                if new_member.role != TeamRole.OWNER.value
                else TeamRole.ADMIN.value,
                "to_role": TeamRole.OWNER.value,
                "correlation_id": correlation_id,
            },
        )

    # ─────────────── G6 / G7 / B13 / E10 move_project_team ───────────────

    async def move_project_team(
        self,
        db: AsyncSession,
        actor_id: UUID,
        project_id: UUID,
        target_team_id: UUID | None,
    ) -> Project:
        """project 归属变更（仅个人 ↔ team 双向 / Q7=A 禁 cross-team 直跳 / B13 archived 拒）。

        - target_team_id=None：移回个人（仅当 project.team_id 当前非 null）
        - target_team_id=tid：加入 team（前提 project.team_id IS NULL + project.status != archived）
        - cross-team 直跳（current.team_id != null && target_team_id != null）→ E10
        - archived project 加入 team → B13 PROJECT_ARCHIVED 拒（M02 ErrorCode 复用）
        """
        proj = await db.get(Project, project_id)
        if proj is None:
            from api.errors.exceptions import NotFoundError

            raise NotFoundError(resource="project", resource_id=str(project_id))

        # 校验 actor 是 project owner
        owner_pm = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == actor_id,
                ProjectMember.role == MemberRole.OWNER.value,
            )
        )
        if owner_pm.scalar_one_or_none() is None:
            raise PermissionDeniedError(required_role="owner", current_role="non-owner")

        current_team_id = proj.team_id

        # B13：archived project 加入 team 拒（仅入 team 路径触发 / 移回个人豁免）
        if target_team_id is not None and proj.status == ProjectStatus.ARCHIVED.value:
            raise ProjectArchivedError(project_id=str(project_id))

        # E10：cross-team 直跳拒
        if current_team_id is not None and target_team_id is not None:
            raise CrossTeamMoveForbiddenError(
                current_team_id=str(current_team_id),
                target_team_id=str(target_team_id),
            )

        # 加入 team：assert actor 是 target_team admin
        if target_team_id is not None:
            await self.assert_team_role(db, actor_id, target_team_id, TeamRole.ADMIN)

        proj.team_id = target_team_id
        await db.flush()

        if target_team_id is not None:
            await write_event(
                db=db,
                actor_user_id=actor_id,
                project_id=project_id,
                action_type=ACTION_PROJECT_JOINED,
                target_type=TARGET_PROJECT,
                target_id=str(project_id),
                summary="项目加入团队",
                metadata={"team_id": str(target_team_id)},
            )
        else:
            await write_event(
                db=db,
                actor_user_id=actor_id,
                project_id=project_id,
                action_type=ACTION_PROJECT_LEFT,
                target_type=TARGET_PROJECT,
                target_id=str(project_id),
                summary="项目移出团队（迁回个人）",
                metadata={"from_team_id": str(current_team_id)},
            )
        return proj

    # ─────────────── 嵌套 max 权限解析（design §8.6） ───────────────

    async def resolve_project_role(
        self,
        db: AsyncSession,
        user_id: UUID,
        project_id: UUID,
    ) -> MemberRole | None:
        """Q1=B 嵌套式 + Q2=B 三角色映射：max(team_role_mapped, project_member_role)。

        返回 None 表示无访问权（design §8.6 字面 / R-X3 跨模块只读 M02 ProjectMember + Project）。
        """
        # 1. project_member 直接 role
        pm_row = await db.execute(
            select(ProjectMember.role).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        pm_role_str = pm_row.scalar_one_or_none()
        pm_role = MemberRole(pm_role_str) if pm_role_str else None

        # 2. team baseline role（仅当 project 归属 team）
        team_role_mapped: MemberRole | None = None
        proj_row = await db.execute(select(Project.team_id).where(Project.id == project_id))
        team_id = proj_row.scalar_one_or_none()
        if team_id is not None:
            tm_role = await self.member_dao.get_role_for_user(db, team_id, user_id)
            if tm_role is not None:
                team_role_mapped = _TEAM_TO_PROJECT_ROLE[tm_role]

        # 3. max
        candidates = [r for r in (pm_role, team_role_mapped) if r is not None]
        if not candidates:
            return None
        return max(candidates, key=lambda r: _PROJECT_ROLE_PRIORITY[r])
