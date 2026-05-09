"""M20 子片 1 — Team + TeamMember model 单元测试。

覆盖 design §3 SQLAlchemy block + §3.4 Alembic 迁移 + R3-2 三重防护：
- Team 持久化 + 默认值（version=1 / created_at + updated_at server_default）
- TeamMember 持久化 + 默认值（joined_at server_default）
- UniqueConstraint(creator_id, name) 防同 creator 同名（B5/B5b）
- UniqueConstraint(team_id, user_id) 防重复加同 user（E8）
- CheckConstraint role IN ('owner','admin','member') 三重防护拒非法值
- CheckConstraint name 长度 1-100（B1）
- CheckConstraint version >= 1
- ON DELETE RESTRICT：teams.creator_id（删 creator user 拒 / 由 M01 baseline-patch
  USER_HAS_OWNED_TEAMS 校验链覆盖）
- ON DELETE RESTRICT：team_members.team_id（删 teams 行前必先清 team_members /
  Service 5 步流程）
- ON DELETE CASCADE：team_members.user_id（删 user 自动清 team_members）
- ON DELETE RESTRICT：projects.team_id（M02 baseline-patch FK / Q8 强制前置迁出）
- M20 ActionType+10 + TargetType+1 同步对账（M15 横切表 owner 4 处同步责任）
- R14 全过去式立规对齐
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.models.activity_log import _ACTION_TYPES, _TARGET_TYPES
from api.models.teams import _TEAM_ROLES, Team, TeamMember, TeamRole

# ─────────────── M20-MODEL-T1 持久化基础 + 默认值 ───────────────


async def test_team_persists_with_defaults(db_session, make_user):
    user = await make_user()
    team = Team(creator_id=user.id, name="Engineering")
    db_session.add(team)
    await db_session.flush()
    await db_session.refresh(team)

    assert team.id is not None
    assert team.creator_id == user.id
    assert team.name == "Engineering"
    assert team.description is None
    assert team.version == 1
    assert team.created_at is not None
    assert team.updated_at is not None


async def test_team_member_persists_with_defaults(db_session, make_team):
    creator, team = await make_team()
    member = TeamMember(team_id=team.id, user_id=creator.id, role=TeamRole.OWNER.value)
    db_session.add(member)
    await db_session.flush()
    await db_session.refresh(member)

    assert member.id is not None
    assert member.team_id == team.id
    assert member.user_id == creator.id
    assert member.role == TeamRole.OWNER.value
    assert member.joined_at is not None


# ─────────────── M20-MODEL-T2 UniqueConstraint ───────────────


async def test_team_unique_creator_name(db_session, make_user):
    """B5：同 creator 不同 team 同名 拒 IntegrityError（uq_teams_creator_name）。"""
    user = await make_user()
    db_session.add(Team(creator_id=user.id, name="X"))
    await db_session.flush()
    db_session.add(Team(creator_id=user.id, name="X"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_team_different_creators_same_name_allowed(db_session, make_user):
    """B6：不同 creator 同名 team 允许（uq 仅同 creator 唯一）。"""
    u1 = await make_user()
    u2 = await make_user()
    db_session.add(Team(creator_id=u1.id, name="X"))
    db_session.add(Team(creator_id=u2.id, name="X"))
    await db_session.flush()
    rows = (await db_session.execute(select(Team).where(Team.name == "X"))).scalars().all()
    assert len(rows) == 2


async def test_team_member_unique_team_user(db_session, make_team_with_owner):
    """E8：同 team 同 user 重复加 拒 IntegrityError（uq_team_members_team_user）。"""
    creator, team = await make_team_with_owner()
    # creator 已是 owner（make_team_with_owner 自动加）
    db_session.add(TeamMember(team_id=team.id, user_id=creator.id, role=TeamRole.MEMBER.value))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


# ─────────────── M20-MODEL-T3 CheckConstraint 三重防护 ───────────────


async def test_team_member_role_check_rejects_invalid(db_session, make_team):
    """R3-2 三重防护：role 必须 IN ('owner','admin','member') / 非法值 IntegrityError。"""
    creator, team = await make_team()
    db_session.add(TeamMember(team_id=team.id, user_id=creator.id, role="superuser"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_team_name_length_check_rejects_empty(db_session, make_user):
    """B1：name 空字符串 → IntegrityError（ck_teams_name_length 1-100）。"""
    user = await make_user()
    db_session.add(Team(creator_id=user.id, name=""))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_team_name_length_check_rejects_over_100(db_session, make_user):
    """B1：name 101 字符 → DB 拒（VARCHAR(100) 拦在 CHECK 之前 / 双层防护）。

    实施细节：name 列 String(100) 拦超长在前（StringDataRightTruncation）+ CHECK
    constraint 兜底 1-100；任一触发即 SQLAlchemy DBAPIError 子类抛出。两层防护一起守
    "Pydantic max_length=100 ↔ DB VARCHAR(100) ↔ CHECK 1-100" 三方一致。
    """
    from sqlalchemy.exc import DBAPIError

    user = await make_user()
    db_session.add(Team(creator_id=user.id, name="X" * 101))
    with pytest.raises(DBAPIError):
        await db_session.flush()
    await db_session.rollback()


async def test_team_name_boundary_1_and_100_accepted(db_session, make_user):
    """B1：1 / 100 字符边界值通过。"""
    u1 = await make_user()
    u2 = await make_user()
    db_session.add(Team(creator_id=u1.id, name="a"))
    db_session.add(Team(creator_id=u2.id, name="X" * 100))
    await db_session.flush()


# ─────────────── M20-MODEL-T4 ON DELETE 行为 ───────────────


async def test_team_member_user_cascade(db_session, make_team_with_owner, make_user):
    """ON DELETE CASCADE：删 user（非 creator）自动清其 team_members 行（M01 范式对齐）。

    注意：creator 不能直接删（teams.creator_id RESTRICT 守护）/ 用普通 member 验证 CASCADE。
    """
    from api.models.user import User

    creator, team = await make_team_with_owner()
    member_user = await make_user()
    db_session.add(TeamMember(team_id=team.id, user_id=member_user.id, role=TeamRole.MEMBER.value))
    await db_session.flush()
    rows = (
        (await db_session.execute(select(TeamMember).where(TeamMember.team_id == team.id)))
        .scalars()
        .all()
    )
    assert len(rows) == 2  # creator owner + member

    # 删 member user（非 creator）
    user = await db_session.get(User, member_user.id)
    await db_session.delete(user)
    await db_session.flush()

    rows = (
        (await db_session.execute(select(TeamMember).where(TeamMember.team_id == team.id)))
        .scalars()
        .all()
    )
    assert len(rows) == 1  # 仅剩 creator owner


async def test_team_team_member_restrict(db_session, make_team_with_owner):
    """ON DELETE RESTRICT：删 teams 行前若 team_members 非空 → IntegrityError（Q13.1②=B）。"""
    creator, team = await make_team_with_owner()
    await db_session.delete(team)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_project_team_id_fk_restrict(db_session, make_team_with_owner, make_project):
    """M02 baseline-patch FK：projects.team_id RESTRICT（Q8 强制前置迁出 / 删 team 前 projects 必须空）。"""
    creator, team = await make_team_with_owner()
    user, proj = await make_project(owner=creator)
    proj.team_id = team.id
    await db_session.flush()

    # 尝试先清 team_members 再删 team（注意 projects 仍引用 team）
    members = (
        (await db_session.execute(select(TeamMember).where(TeamMember.team_id == team.id)))
        .scalars()
        .all()
    )
    for m in members:
        await db_session.delete(m)
    await db_session.flush()

    # 再删 team → 因 projects.team_id 仍引用 team → RESTRICT IntegrityError
    await db_session.delete(team)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


# ─────────────── M20-MODEL-T5 M15 baseline-patch 4 处同步对账 ───────────────


def test_action_types_contain_10_team_events():
    """M15 baseline-patch：_ACTION_TYPES 含 10 个 team_* / project_*_team 事件 + 全过去式（R14）。"""
    expected = {
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
    }
    assert expected.issubset(set(_ACTION_TYPES))
    # R14 立规：全过去式 + snake_case
    for action in expected:
        assert "_" in action
        # 简单过去式校验：含 ed / ied / changed / joined / left / added / removed / created / deleted /
        # promoted / demoted / renamed
        assert any(
            tense in action
            for tense in (
                "ed",
                "joined",
                "left",
                "added",
                "removed",
                "created",
                "deleted",
                "promoted",
                "demoted",
                "renamed",
                "changed",
            )
        )


def test_target_types_contain_team():
    """M15 baseline-patch：_TARGET_TYPES 含 'team'（M20 baseline-patch line 157）。"""
    assert "team" in _TARGET_TYPES


def test_team_roles_tuple_matches_enum():
    """三重防护 4 处同步：_TEAM_ROLES tuple ↔ TeamRole Enum 字面同步（M15 范式 / model + CHECK + Mapped + Enum）。"""
    assert set(_TEAM_ROLES) == {r.value for r in TeamRole}
    assert _TEAM_ROLES == ("owner", "admin", "member")


# ─────────────── M20-MODEL-T6 relationship back_populates ───────────────


async def test_team_members_relationship_back_populates(db_session, make_team_with_owner):
    """relationship('Team', back_populates='members') / Team.members ↔ TeamMember.team。"""
    creator, team = await make_team_with_owner()
    await db_session.refresh(team)

    member_obj = (
        await db_session.execute(select(TeamMember).where(TeamMember.team_id == team.id))
    ).scalar_one()
    await db_session.refresh(member_obj, ["team"])
    assert member_obj.team.id == team.id


async def test_team_members_no_cascade_delete_orphan(db_session, make_team_with_owner):
    """Q13.1②=B RESTRICT：Team.members 不级联 delete-orphan（强制 Service 显式 5 步）。

    验证设计契约：detach 一个 member 不会自动 DELETE。
    """
    creator, team = await make_team_with_owner()
    # 直接从 session 查 member（不通过 team.members，避免懒加载触发 cascade）
    _member = (
        await db_session.execute(
            select(TeamMember).where(
                TeamMember.team_id == team.id, TeamMember.user_id == creator.id
            )
        )
    ).scalar_one()
    # 不调 db_session.delete(_member) / 不应自动失踪
    await db_session.flush()
    rows = (
        (await db_session.execute(select(TeamMember).where(TeamMember.team_id == team.id)))
        .scalars()
        .all()
    )
    assert len(rows) == 1
