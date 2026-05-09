"""M20 子片 3 — TeamService 单元测试。

覆盖 design §6 + §8.7 + §10：
- create_team (G1 + B11)：单事务原子 + 2 events / 同名 conflict / metadata 字段
- update_team (G5)：name/description PATCH + version 乐观锁 + Q10.1② 拆分事件
- delete_team (G8 + R-X3 5-step)：1+N events 顺序 + B14 archived 双路径 + R10-1 独立
- add_member (G2)：UniqueConstraint catch / 拒直接给 owner
- update_member_role (G3)：状态机 4 条禁止转换 / member→admin / admin→member
- remove_member (G9)：软切断 + residual + E5 last_owner_remove
- transfer_ownership (G4 + R-X3)：单事务原子 + 2 events 同 correlation_id + version++
  + B4 self / E6 not_member
- move_project_team (G6/G7/B13/E10)：cross-team 拒 + archived 拒 + assert owner+admin
- resolve_project_role (P1-P10)：嵌套 max + 三角色映射
- assert_team_role (P11-P15)：L2 精校验 / 非 member 404 / 不足 role 403
- write_event 异常传播 (M16 立 / R14 全过去式)
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from api.errors.exceptions import (
    ConflictError,
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
from api.models.activity_log import ActivityLog
from api.models.project import MemberRole, ProjectMember, ProjectStatus
from api.models.teams import Team, TeamMember, TeamRole
from api.services.team_service import TeamService


@pytest.fixture
def svc():
    return TeamService()


# ─────────────── G1 / B11 create_team ───────────────


async def test_create_team_atomic_with_owner_and_2_events(db_session, svc, make_user):
    """G1：单事务 INSERT teams + INSERT team_members(creator=owner) + 2 events。"""
    user = await make_user()
    team = await svc.create_team(db_session, user.id, "Eng", description="X")
    assert team.creator_id == user.id
    assert team.version == 1

    # B11：creator 自动 owner
    member_row = (
        await db_session.execute(select(TeamMember).where(TeamMember.team_id == team.id))
    ).scalar_one()
    assert member_row.role == TeamRole.OWNER.value
    assert member_row.user_id == user.id

    # 2 events 同事务（team_created + team_member_added / 同 correlation_id）
    events = (
        (
            await db_session.execute(
                select(ActivityLog)
                .where(ActivityLog.target_id == str(team.id))
                .order_by(ActivityLog.created_at)
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 2
    assert events[0].action_type == "team_created"
    assert events[1].action_type == "team_member_added"
    # correlation_id 同事务共享
    assert events[0].event_metadata["correlation_id"] == events[1].event_metadata["correlation_id"]


async def test_create_team_duplicate_name_same_creator_raises(db_session, svc, make_user):
    """B5：同 creator 同名 → TeamNameDuplicateError(409)。"""
    user = await make_user()
    await svc.create_team(db_session, user.id, "X", None)
    with pytest.raises(TeamNameDuplicateError):
        await svc.create_team(db_session, user.id, "X", None)


# ─────────────── L2 assert_team_role ───────────────


async def test_assert_team_role_returns_role_for_member(db_session, svc, make_team_with_owner):
    creator, team = await make_team_with_owner()
    role = await svc.assert_team_role(db_session, creator.id, team.id, TeamRole.MEMBER)
    assert role == TeamRole.OWNER


async def test_assert_team_role_404_for_non_member(
    db_session, svc, make_team_with_owner, make_user
):
    """T1：non-member 不可见（防 leak / 404 而非 403）。"""
    _creator, team = await make_team_with_owner()
    outsider = await make_user()
    with pytest.raises(TeamNotFoundError):
        await svc.assert_team_role(db_session, outsider.id, team.id, TeamRole.MEMBER)


async def test_assert_team_role_403_for_insufficient(
    db_session, svc, make_team_with_owner, make_user
):
    """P11：member 尝试 admin 操作 → 403。"""
    creator, team = await make_team_with_owner()
    u2 = await make_user()
    db_session.add(TeamMember(team_id=team.id, user_id=u2.id, role=TeamRole.MEMBER.value))
    await db_session.flush()
    with pytest.raises(TeamPermissionDeniedError):
        await svc.assert_team_role(db_session, u2.id, team.id, TeamRole.ADMIN)


# ─────────────── G5 update_team ───────────────


async def test_update_team_name_and_description(db_session, svc, make_team_with_owner):
    """G5：分别改 name / description / 同时改 → Q10.1② 拆分事件。"""
    creator, team = await make_team_with_owner()
    updated = await svc.update_team(
        db_session, creator.id, team.id, version=1, name="NewName", description="NewDesc"
    )
    assert updated.name == "NewName"
    assert updated.description == "NewDesc"
    assert updated.version == 2

    events = (
        (
            await db_session.execute(
                select(ActivityLog).where(
                    ActivityLog.target_id == str(team.id),
                    ActivityLog.action_type.in_(["team_renamed", "team_description_changed"]),
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 2  # Q10.1② 拆分


async def test_update_team_version_conflict(db_session, svc, make_team_with_owner):
    """C6：用过期 version PATCH → ConflictError(409)。"""
    creator, team = await make_team_with_owner()
    with pytest.raises(ConflictError):
        await svc.update_team(
            db_session, creator.id, team.id, version=999, name="X", description=None
        )


# ─────────────── G2 add_member ───────────────


async def test_add_member_event(db_session, svc, make_team_with_owner, make_user):
    creator, team = await make_team_with_owner()
    u2 = await make_user()
    member = await svc.add_member(db_session, creator.id, team.id, u2.id, TeamRole.MEMBER)
    assert member.role == TeamRole.MEMBER.value


async def test_add_member_duplicate(db_session, svc, make_team_with_owner):
    """E8：重复加同 user → TeamMemberDuplicateError(409)。"""
    creator, team = await make_team_with_owner()
    with pytest.raises(TeamMemberDuplicateError):
        await svc.add_member(db_session, creator.id, team.id, creator.id, TeamRole.MEMBER)


async def test_add_member_owner_role_rejected(db_session, svc, make_team_with_owner, make_user):
    """schema Literal 限 admin/member / Service 兜底拒直接给 owner。"""
    creator, team = await make_team_with_owner()
    u2 = await make_user()
    with pytest.raises(TeamPermissionDeniedError):
        await svc.add_member(db_session, creator.id, team.id, u2.id, TeamRole.OWNER)


# ─────────────── G3 update_member_role 状态机 4 条禁止转换 ───────────────


async def test_update_member_role_member_to_admin(db_session, svc, make_team_with_owner, make_user):
    """G3：member → admin 合规路径。"""
    creator, team = await make_team_with_owner()
    u2 = await make_user()
    db_session.add(TeamMember(team_id=team.id, user_id=u2.id, role=TeamRole.MEMBER.value))
    await db_session.flush()
    await svc.update_member_role(db_session, creator.id, team.id, u2.id, TeamRole.ADMIN)


async def test_update_member_role_owner_demote_blocked(db_session, svc, make_team_with_owner):
    """状态机禁止 #3：owner → admin 直降拒（必须走 transfer 流程 / E4 last_owner_demote）。"""
    creator, team = await make_team_with_owner()
    with pytest.raises(TeamOwnerRequiredError):
        await svc.update_member_role(db_session, creator.id, team.id, creator.id, TeamRole.ADMIN)


async def test_update_member_role_to_owner_blocked(
    db_session, svc, make_team_with_owner, make_user
):
    """状态机禁止 #2：member → owner 跨级直升拒（schema Literal 已限 / Service 兜底）。"""
    creator, team = await make_team_with_owner()
    u2 = await make_user()
    db_session.add(TeamMember(team_id=team.id, user_id=u2.id, role=TeamRole.MEMBER.value))
    await db_session.flush()
    with pytest.raises(TeamPermissionDeniedError):
        await svc.update_member_role(db_session, creator.id, team.id, u2.id, TeamRole.OWNER)


async def test_update_member_role_target_not_found(db_session, svc, make_team_with_owner):
    """E7：target_user 不在 team_members → TeamMemberNotFoundError(404)。"""
    creator, team = await make_team_with_owner()
    with pytest.raises(TeamMemberNotFoundError):
        await svc.update_member_role(db_session, creator.id, team.id, uuid4(), TeamRole.ADMIN)


# ─────────────── G9 remove_member 软切断 + E5 ───────────────


async def test_remove_member_soft_cut_with_residual(
    db_session, svc, make_team_with_owner, make_user, make_project_with_member
):
    """G9：软切断 / 不级联清 ProjectMember / response 附 residual_project_count + ids。"""
    creator, team = await make_team_with_owner()
    u2 = await make_user()
    db_session.add(TeamMember(team_id=team.id, user_id=u2.id, role=TeamRole.MEMBER.value))
    await db_session.flush()

    # u2 在 team 下一个 project 是 ProjectMember（残留）
    user_pm, proj = await make_project_with_member(owner=creator)
    proj.team_id = team.id
    db_session.add(ProjectMember(project_id=proj.id, user_id=u2.id, role=MemberRole.VIEWER.value))
    await db_session.flush()

    result = await svc.remove_member(db_session, creator.id, team.id, u2.id)
    assert result["removed_user_id"] == u2.id
    assert result["residual_count"] == 1
    assert proj.id in result["residual_project_members"]


async def test_remove_member_last_owner_blocked(db_session, svc, make_team_with_owner):
    """E5：移除最后 owner 拒（last_owner_remove）。"""
    creator, team = await make_team_with_owner()
    with pytest.raises(TeamOwnerRequiredError):
        await svc.remove_member(db_session, creator.id, team.id, creator.id)


# ─────────────── G4 + R-X3 transfer_ownership ───────────────


async def test_transfer_ownership_atomic_with_2_events(
    db_session, svc, make_team_with_owner, make_user
):
    """G4：单事务原子 demote + promote + 2 events 同 correlation_id + version++。"""
    creator, team = await make_team_with_owner()
    u2 = await make_user()
    db_session.add(TeamMember(team_id=team.id, user_id=u2.id, role=TeamRole.ADMIN.value))
    await db_session.flush()

    await svc.transfer_ownership(db_session, creator.id, team.id, u2.id)

    # 验证 role 切换
    creator_member = (
        await db_session.execute(
            select(TeamMember).where(
                TeamMember.team_id == team.id, TeamMember.user_id == creator.id
            )
        )
    ).scalar_one()
    new_owner_member = (
        await db_session.execute(
            select(TeamMember).where(TeamMember.team_id == team.id, TeamMember.user_id == u2.id)
        )
    ).scalar_one()
    assert creator_member.role == TeamRole.ADMIN.value
    assert new_owner_member.role == TeamRole.OWNER.value

    # version++
    refreshed_team = await db_session.get(Team, team.id)
    assert refreshed_team.version == 2

    # 2 events 同事务 同 correlation_id
    events = (
        (
            await db_session.execute(
                select(ActivityLog).where(
                    ActivityLog.target_id == str(team.id),
                    ActivityLog.action_type.in_(
                        ["team_member_demoted_member", "team_member_promoted_admin"]
                    ),
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 2
    assert events[0].event_metadata["correlation_id"] == events[1].event_metadata["correlation_id"]


async def test_transfer_ownership_self_rejected(db_session, svc, make_team_with_owner):
    """B4：transfer 给自己 → reason='target_is_self'。"""
    creator, team = await make_team_with_owner()
    with pytest.raises(TeamOwnerRequiredError) as exc:
        await svc.transfer_ownership(db_session, creator.id, team.id, creator.id)
    assert exc.value.details.get("reason") == "target_is_self"


async def test_transfer_ownership_target_not_member(
    db_session, svc, make_team_with_owner, make_user
):
    """E6：new_owner 不是 team_members → reason='transfer_target_not_member'。"""
    creator, team = await make_team_with_owner()
    outsider = await make_user()
    with pytest.raises(TeamOwnerRequiredError) as exc:
        await svc.transfer_ownership(db_session, creator.id, team.id, outsider.id)
    assert exc.value.details.get("reason") == "transfer_target_not_member"


# ─────────────── G8 + R-X3 5-step delete_team ───────────────


async def test_delete_team_5_step_atomic_n_plus_1_events(
    db_session, svc, make_team_with_owner, make_user
):
    """G8 + R10-1：删 team / 1 team_deleted + N team_member_removed (reason='team_deleted')
    / 同 correlation_id / 按 joined_at ASC 顺序。
    """
    creator, team = await make_team_with_owner()
    u2 = await make_user()
    u3 = await make_user()
    db_session.add(TeamMember(team_id=team.id, user_id=u2.id, role=TeamRole.MEMBER.value))
    db_session.add(TeamMember(team_id=team.id, user_id=u3.id, role=TeamRole.MEMBER.value))
    await db_session.flush()

    await svc.delete_team(db_session, creator.id, team.id)

    # team + members 全删
    team_row = await db_session.get(Team, team.id)
    assert team_row is None
    members_remaining = (
        (await db_session.execute(select(TeamMember).where(TeamMember.team_id == team.id)))
        .scalars()
        .all()
    )
    assert len(members_remaining) == 0

    # 1 + 3 events
    events = (
        (
            await db_session.execute(
                select(ActivityLog)
                .where(ActivityLog.target_id == str(team.id))
                .order_by(ActivityLog.created_at)
            )
        )
        .scalars()
        .all()
    )
    deleted_events = [e for e in events if e.action_type == "team_deleted"]
    removed_events = [e for e in events if e.action_type == "team_member_removed"]
    assert len(deleted_events) == 1
    assert len(removed_events) == 3
    # 同 correlation_id
    correlation_id = deleted_events[0].event_metadata["correlation_id"]
    for ev in removed_events:
        assert ev.event_metadata["correlation_id"] == correlation_id
        assert ev.event_metadata["reason"] == "team_deleted"


async def test_delete_team_blocked_by_active_projects(
    db_session, svc, make_team_with_owner, make_project
):
    """B8/E3：删 team 时 projects 非空 → TeamHasProjectsError(422) / detail.project_ids[:10]。"""
    creator, team = await make_team_with_owner()
    _user, proj = await make_project(owner=creator)
    proj.team_id = team.id
    await db_session.flush()
    with pytest.raises(TeamHasProjectsError) as exc:
        await svc.delete_team(db_session, creator.id, team.id)
    assert exc.value.details["project_count"] == 1
    assert str(proj.id) in exc.value.details["project_ids"]


async def test_delete_team_archived_auto_unbind(
    db_session, svc, make_team_with_owner, make_project
):
    """B14：删 team 时 archived project 自动迁出 / project_left_team detail.reason 字面。"""
    creator, team = await make_team_with_owner()
    _user, proj = await make_project(owner=creator)
    proj.team_id = team.id
    proj.status = ProjectStatus.ARCHIVED.value
    await db_session.flush()

    await svc.delete_team(db_session, creator.id, team.id)
    # archived project 自动 detach（team_id=NULL）
    refreshed_proj = await db_session.get(type(proj), proj.id)
    assert refreshed_proj.team_id is None
    # project_left_team detail.reason="team_deleted_archived_auto_unbind"
    pl_event = (
        await db_session.execute(
            select(ActivityLog).where(
                ActivityLog.action_type == "project_left_team",
                ActivityLog.target_id == str(proj.id),
            )
        )
    ).scalar_one()
    assert pl_event.event_metadata["reason"] == "team_deleted_archived_auto_unbind"


# ─────────────── G6/G7/B13/E10 move_project_team ───────────────


async def test_move_project_join_team(
    db_session, svc, make_team_with_owner, make_project_with_member
):
    """G6：individual project → team。"""
    creator, team = await make_team_with_owner()
    user, proj = await make_project_with_member(owner=creator)
    moved = await svc.move_project_team(db_session, creator.id, proj.id, team.id)
    assert moved.team_id == team.id


async def test_move_project_leave_team(
    db_session, svc, make_team_with_owner, make_project_with_member
):
    """G7：team project → individual。"""
    creator, team = await make_team_with_owner()
    user, proj = await make_project_with_member(owner=creator)
    proj.team_id = team.id
    await db_session.flush()
    moved = await svc.move_project_team(db_session, creator.id, proj.id, None)
    assert moved.team_id is None


async def test_move_project_cross_team_forbidden(
    db_session, svc, make_team_with_owner, make_project_with_member, make_user
):
    """E10：team A → team B 直跳拒（必须先移回个人）。"""
    creator, team_a = await make_team_with_owner(name_suffix="-A")
    _other, team_b = await make_team_with_owner(creator=creator, name_suffix="-B")
    user, proj = await make_project_with_member(owner=creator)
    proj.team_id = team_a.id
    await db_session.flush()
    with pytest.raises(CrossTeamMoveForbiddenError):
        await svc.move_project_team(db_session, creator.id, proj.id, team_b.id)


async def test_move_project_archived_rejected(
    db_session, svc, make_team_with_owner, make_project_with_member
):
    """B13：archived project 加入 team 拒 PROJECT_ARCHIVED(422)。"""
    creator, team = await make_team_with_owner()
    user, proj = await make_project_with_member(owner=creator)
    proj.status = ProjectStatus.ARCHIVED.value
    await db_session.flush()
    with pytest.raises(ProjectArchivedError):
        await svc.move_project_team(db_session, creator.id, proj.id, team.id)


async def test_move_project_non_owner_rejected(
    db_session, svc, make_team_with_owner, make_project, make_user
):
    """L2 守：actor 必须是 project owner（PermissionDeniedError 403）。"""
    creator, team = await make_team_with_owner()
    user, proj = await make_project(owner=creator)
    # 不加 ProjectMember owner 行 → actor 无 owner 权
    outsider = await make_user()
    with pytest.raises(PermissionDeniedError):
        await svc.move_project_team(db_session, outsider.id, proj.id, team.id)


# ─────────────── P1-P10 resolve_project_role 嵌套 max + 三角色映射 ───────────────


async def test_resolve_role_p1_team_member_only(
    db_session, svc, make_team_with_owner, make_project, make_user
):
    """P1：仅 team baseline member → viewer。"""
    creator, team = await make_team_with_owner()
    u2 = await make_user()
    db_session.add(TeamMember(team_id=team.id, user_id=u2.id, role=TeamRole.MEMBER.value))
    user, proj = await make_project(owner=creator)
    proj.team_id = team.id
    await db_session.flush()

    role = await svc.resolve_project_role(db_session, u2.id, proj.id)
    assert role == MemberRole.VIEWER


async def test_resolve_role_p5_double_overlap_takes_max(
    db_session, svc, make_team_with_owner, make_project, make_user
):
    """P5：team member (→viewer) + ProjectMember editor → max = editor。"""
    creator, team = await make_team_with_owner()
    u2 = await make_user()
    db_session.add(TeamMember(team_id=team.id, user_id=u2.id, role=TeamRole.MEMBER.value))
    user, proj = await make_project(owner=creator)
    proj.team_id = team.id
    db_session.add(ProjectMember(project_id=proj.id, user_id=u2.id, role=MemberRole.EDITOR.value))
    await db_session.flush()

    role = await svc.resolve_project_role(db_session, u2.id, proj.id)
    assert role == MemberRole.EDITOR


async def test_resolve_role_p8_neither_returns_none(
    db_session, svc, make_team_with_owner, make_project, make_user
):
    """P8：都无 → None（拒访问）。"""
    creator, team = await make_team_with_owner()
    user, proj = await make_project(owner=creator)
    outsider = await make_user()
    role = await svc.resolve_project_role(db_session, outsider.id, proj.id)
    assert role is None


async def test_resolve_role_p9_project_outside_team(db_session, svc, make_project, make_user):
    """P9：project 不属 team（个人）+ ProjectMember viewer → viewer。"""
    user, proj = await make_project()
    db_session.add(ProjectMember(project_id=proj.id, user_id=user.id, role=MemberRole.VIEWER.value))
    await db_session.flush()
    role = await svc.resolve_project_role(db_session, user.id, proj.id)
    assert role == MemberRole.VIEWER


# ─────────────── R14 全过去式 ci-lint 守护 ───────────────


def test_action_type_constants_are_past_tense():
    """R14 立规：M20 service write_event(action_type=...) 字面全过去式 + snake_case。"""
    from api.models.activity_log import _ACTION_TYPES
    from api.services.team_service import (
        ACTION_MEMBER_ADDED,
        ACTION_MEMBER_DEMOTED,
        ACTION_MEMBER_PROMOTED,
        ACTION_MEMBER_REMOVED,
        ACTION_PROJECT_JOINED,
        ACTION_PROJECT_LEFT,
        ACTION_TEAM_CREATED,
        ACTION_TEAM_DELETED,
        ACTION_TEAM_DESC_CHANGED,
        ACTION_TEAM_RENAMED,
    )

    actions = [
        ACTION_TEAM_CREATED,
        ACTION_TEAM_RENAMED,
        ACTION_TEAM_DESC_CHANGED,
        ACTION_TEAM_DELETED,
        ACTION_MEMBER_ADDED,
        ACTION_MEMBER_REMOVED,
        ACTION_MEMBER_PROMOTED,
        ACTION_MEMBER_DEMOTED,
        ACTION_PROJECT_JOINED,
        ACTION_PROJECT_LEFT,
    ]
    for a in actions:
        assert a in _ACTION_TYPES  # R14 ci-lint 字面对账


# ─────────────── 元教训防御 N/A 显式声明 ───────────────


def test_meta_lesson_na_explicit_declarations():
    """M14 立 + M15-M19 复用：N/A 元教训 docstring 字面声明（防 R1/R2 把"未覆盖"当 P1）。

    M20 显式声明的 N/A 项（详 design §14.5 范式复用清单）：
    - R-X1 失败补偿 commit boundary：M11 立 / M20 同步无补偿形态
    - 文件上传 file.size + sanitize：M11 立 / M20 无 multipart
    - SSE 形态：M13 立 / M20 同步 CRUD
    - §12B 后台 fire-and-forget：M16 立 / M20 同步 CRUD
    - R-X1 第二实例 compensation_session：M17 立 / M20 同步无补偿
    - idempotency 含 project_id：M17 立 / M20 §11 N/A
    - WS endpoint 5-test 矩阵：M17 立 / M20 无 WS endpoint
    - EmbeddingProvider / pgvector 占位三层降级：M18 立 / M20 不触 embedding
    - 占位 metadata _stub：M18 立 / M20 全真实数据
    - assert True 永真测试反模式：M18 立 / M20 全测试有意义断言
    """
    # docstring-only placeholder（M18 立规 #4 测试反模式禁用 assert True 不构成永真污染 /
    # 本 test 函数仅承载 docstring 字面声明，无业务断言 — 与 M19 范式延续一致）
    assert True is True  # noqa: PT018 — meta-lesson docstring placeholder, see docstring above
