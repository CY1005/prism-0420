"""M20 子片 2 — TeamDAO + TeamMemberDAO + M20TenantContext L3 SQL 注入 单元测试。

覆盖 design §9 DAO tenant 过滤 + ADR-005 §3.1 L3 SQL 注入升级：
- TeamDAO.get_by_id：tenant 过滤（非 member 返回 None / 防 leak）
- TeamDAO.get_by_id_no_tenant：内部 service 持锁场景
- TeamDAO.list_for_user：JOIN team_members 反向解析
- TeamDAO.get_member_count：聚合字段
- TeamDAO.find_by_creator_name：UniqueConstraint 字面 lookup
- TeamDAO.count_projects_in_team / list_active_project_ids_in_team：删 team 前置校验
  （排除 archived 走豁免路径 / B14 archived 自动迁出）
- TeamDAO.list_archived_project_ids_in_team：B14 archived 路径
- TeamMemberDAO.get / list_for_team / count_owners / get_role_for_user：成员 CRUD
- M20TenantContext.user_accessible_project_ids_subquery：UNION（project_members ∪
  projects via team_members 反向解析 / M03-M19 既有 DAO 自动获益）
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from api.dao.teams_dao import M20TenantContext, TeamDAO, TeamMemberDAO
from api.models.project import Project
from api.models.teams import TeamMember, TeamRole


@pytest.fixture
def team_dao():
    return TeamDAO()


@pytest.fixture
def member_dao():
    return TeamMemberDAO()


# ─────────────── M20-DAO-T1 TeamDAO.get_by_id tenant 过滤 ───────────────


async def test_get_by_id_returns_team_for_member(db_session, team_dao, make_team_with_owner):
    creator, team = await make_team_with_owner()
    result = await team_dao.get_by_id(db_session, team.id, creator.id)
    assert result is not None
    assert result.id == team.id


async def test_get_by_id_returns_none_for_non_member(
    db_session, team_dao, make_team_with_owner, make_user
):
    """T1：U1 不在 team T → 不可见（404 TEAM_NOT_FOUND / 防 leak 存在性）。"""
    _creator, team = await make_team_with_owner()
    outsider = await make_user()
    result = await team_dao.get_by_id(db_session, team.id, outsider.id)
    assert result is None


async def test_get_by_id_no_tenant_bypasses_filter(db_session, team_dao, make_team_with_owner):
    """get_by_id_no_tenant：caller 必须先做 L1 校验 / 内部持锁场景。"""
    _creator, team = await make_team_with_owner()
    result = await team_dao.get_by_id_no_tenant(db_session, team.id)
    assert result is not None and result.id == team.id


# ─────────────── M20-DAO-T2 TeamDAO.list_for_user ───────────────


async def test_list_for_user_returns_only_user_teams(
    db_session, team_dao, make_team_with_owner, make_user
):
    """G10：U 仅看到自己加入的 team。"""
    creator_a, team_a = await make_team_with_owner(name_suffix="-A")
    _creator_b, team_b = await make_team_with_owner(name_suffix="-B")  # creator_a 不在 team_b
    teams = await team_dao.list_for_user(db_session, creator_a.id)
    team_ids = {t.id for t in teams}
    assert team_a.id in team_ids
    assert team_b.id not in team_ids


# ─────────────── M20-DAO-T3 TeamDAO.get_member_count ───────────────


async def test_get_member_count(db_session, team_dao, make_team_with_owner, make_user):
    creator, team = await make_team_with_owner()
    assert await team_dao.get_member_count(db_session, team.id) == 1
    member_user = await make_user()
    db_session.add(TeamMember(team_id=team.id, user_id=member_user.id, role=TeamRole.MEMBER.value))
    await db_session.flush()
    assert await team_dao.get_member_count(db_session, team.id) == 2


# ─────────────── M20-DAO-T4 TeamDAO.find_by_creator_name ───────────────


async def test_find_by_creator_name(db_session, team_dao, make_team):
    creator, team = await make_team()
    result = await team_dao.find_by_creator_name(db_session, creator.id, team.name)
    assert result is not None and result.id == team.id

    result = await team_dao.find_by_creator_name(db_session, creator.id, "Nonexistent")
    assert result is None


# ─────────────── M20-DAO-T5 TeamDAO.count_projects_in_team / archived 豁免 ───────────────


async def test_count_projects_excludes_archived(
    db_session, team_dao, make_team_with_owner, make_project
):
    """B14：count_projects_in_team 排除 archived（archived 走自动迁出豁免路径）。"""
    creator, team = await make_team_with_owner()
    user, proj_active = await make_project(owner=creator, name_suffix="-active")
    user, proj_archived = await make_project(owner=creator, name_suffix="-archived")
    proj_active.team_id = team.id
    proj_archived.team_id = team.id
    proj_archived.status = "archived"
    await db_session.flush()

    assert await team_dao.count_projects_in_team(db_session, team.id) == 1


async def test_list_active_project_ids_limit_10(
    db_session, team_dao, make_team_with_owner, make_project
):
    creator, team = await make_team_with_owner()
    proj_ids = []
    for i in range(15):
        _user, proj = await make_project(owner=creator, name_suffix=f"-{i}")
        proj.team_id = team.id
        proj_ids.append(proj.id)
    await db_session.flush()
    result = await team_dao.list_active_project_ids_in_team(db_session, team.id)
    assert len(result) == 10  # detail.project_ids[:10] 字面契约


async def test_list_archived_project_ids(db_session, team_dao, make_team_with_owner, make_project):
    creator, team = await make_team_with_owner()
    _user, proj = await make_project(owner=creator)
    proj.team_id = team.id
    proj.status = "archived"
    await db_session.flush()
    result = await team_dao.list_archived_project_ids_in_team(db_session, team.id)
    assert proj.id in result


# ─────────────── M20-DAO-T6 TeamMemberDAO ───────────────


async def test_member_dao_get(db_session, member_dao, make_team_with_owner):
    creator, team = await make_team_with_owner()
    m = await member_dao.get(db_session, team.id, creator.id)
    assert m is not None and m.role == TeamRole.OWNER.value


async def test_member_dao_get_none_for_non_member(
    db_session, member_dao, make_team_with_owner, make_user
):
    _creator, team = await make_team_with_owner()
    outsider = await make_user()
    result = await member_dao.get(db_session, team.id, outsider.id)
    assert result is None


async def test_member_dao_list_ordered_by_joined_at(
    db_session, member_dao, make_team_with_owner, make_user
):
    """design §10.3 R10-1：删 team N 条 team_member_removed 必按 joined_at ASC 写入。"""
    creator, team = await make_team_with_owner()
    u2 = await make_user()
    db_session.add(TeamMember(team_id=team.id, user_id=u2.id, role=TeamRole.MEMBER.value))
    await db_session.flush()

    members = await member_dao.list_for_team(db_session, team.id)
    assert len(members) == 2
    assert members[0].user_id == creator.id  # 先 joined
    assert members[1].user_id == u2.id


async def test_member_dao_count_owners(db_session, member_dao, make_team_with_owner, make_user):
    creator, team = await make_team_with_owner()
    assert await member_dao.count_owners(db_session, team.id) == 1
    u2 = await make_user()
    db_session.add(TeamMember(team_id=team.id, user_id=u2.id, role=TeamRole.OWNER.value))
    await db_session.flush()
    assert await member_dao.count_owners(db_session, team.id) == 2


async def test_member_dao_get_role_for_user(
    db_session, member_dao, make_team_with_owner, make_user
):
    creator, team = await make_team_with_owner()
    role = await member_dao.get_role_for_user(db_session, team.id, creator.id)
    assert role == TeamRole.OWNER

    outsider = await make_user()
    role = await member_dao.get_role_for_user(db_session, team.id, outsider.id)
    assert role is None


# ─────────────── M20-DAO-T7 M20TenantContext L3 SQL 注入升级 ───────────────


async def test_m20_tenant_context_includes_project_members_path(
    db_session, make_project_with_member
):
    """M02 路径：U 是 ProjectMember → projects.id 在 subquery 结果集。"""
    user, proj = await make_project_with_member()
    ctx = M20TenantContext()
    sub = ctx.user_accessible_project_ids_subquery(db_session, user.id)
    rows = (await db_session.execute(select(Project.id).where(Project.id.in_(sub)))).scalars().all()
    assert proj.id in rows


async def test_m20_tenant_context_includes_team_members_path(
    db_session, make_team_with_owner, make_project
):
    """M20 升级路径：U 通过 team_members 反向解析到 project（即使不是 ProjectMember）。"""
    creator, team = await make_team_with_owner()
    _user, proj = await make_project(owner=creator)
    proj.team_id = team.id
    await db_session.flush()

    ctx = M20TenantContext()
    sub = ctx.user_accessible_project_ids_subquery(db_session, creator.id)
    rows = (await db_session.execute(select(Project.id).where(Project.id.in_(sub)))).scalars().all()
    assert proj.id in rows


async def test_m20_tenant_context_excludes_outsider(
    db_session, make_team_with_owner, make_project, make_user
):
    """T3：outsider 既不是 ProjectMember 也不在 team → subquery 不召回 project。"""
    creator, team = await make_team_with_owner()
    _user, proj = await make_project(owner=creator)
    proj.team_id = team.id
    await db_session.flush()

    outsider = await make_user()
    ctx = M20TenantContext()
    sub = ctx.user_accessible_project_ids_subquery(db_session, outsider.id)
    rows = (await db_session.execute(select(Project.id).where(Project.id.in_(sub)))).scalars().all()
    assert proj.id not in rows


async def test_m20_tenant_context_union_dedup(
    db_session, make_team_with_owner, make_project_with_member
):
    """UNION 去重：U 同时是 ProjectMember 又通过 team 可访问 → 仅一条记录（DB UNION 自动去重）。"""
    user, proj = await make_project_with_member()
    creator, team = await make_team_with_owner(creator=user)
    proj.team_id = team.id
    await db_session.flush()

    ctx = M20TenantContext()
    sub = ctx.user_accessible_project_ids_subquery(db_session, user.id)
    # IN(subquery) 不会因为 dup 多召回；用 distinct count 验证幂等
    rows = (await db_session.execute(select(Project.id).where(Project.id.in_(sub)))).scalars().all()
    assert rows.count(proj.id) == 1


async def test_outsider_uuid_not_in_dao_list(db_session, team_dao, make_user, make_team_with_owner):
    """T1 复合：fresh user with no teams/projects → list_for_user empty + get_by_id 404 复合验证。"""
    outsider = await make_user()
    teams = await team_dao.list_for_user(db_session, outsider.id)
    assert teams == []
    creator, team = await make_team_with_owner()
    result = await team_dao.get_by_id(db_session, team.id, outsider.id)
    assert result is None
