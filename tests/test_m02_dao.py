"""M02 子片 2 — DAO + tenant_filter concrete impl。

覆盖：
- ProjectDAO.list_by_user (tenant 过滤 + active 过滤)
- ProjectDAO.get_by_id_for_user (tenant 过滤)
- ProjectMemberDAO (list_by_project / get_member / 越权返回空)
- ProjectDimensionConfigDAO (list_by_project)
- DimensionTypeDAO (list_all / get_by_id)
- M02 concrete TenantContext impl 注入后 user_accessible_project_ids_subquery 工作
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

# ─────────────── Fixtures ───────────────


async def _make_user(db_session, email: str | None = None):
    from api.auth.password import hash_password
    from api.models.user import User

    user = User(
        email=email or f"u-{uuid4().hex[:8]}@example.com",
        name="X",
        password_hash=hash_password("Password123!"),
        role="user",
        status="active",
        failed_login_count=0,
        version=1,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture(loop_scope="session")
async def m02_seed(db_session):
    """种 2 user + 3 project (含 archived) + members 关系。"""
    from api.models.project import Project, ProjectMember

    alice = await _make_user(db_session, "alice@example.com")
    bob = await _make_user(db_session, "bob@example.com")

    p_alice_active = Project(name="AliceActive", owner_id=alice.id, status="active")
    p_alice_archived = Project(name="AliceArchived", owner_id=alice.id, status="archived")
    p_bob_active = Project(name="BobActive", owner_id=bob.id, status="active")
    db_session.add_all([p_alice_active, p_alice_archived, p_bob_active])
    await db_session.flush()

    db_session.add_all(
        [
            ProjectMember(project_id=p_alice_active.id, user_id=alice.id, role="owner"),
            ProjectMember(project_id=p_alice_archived.id, user_id=alice.id, role="owner"),
            ProjectMember(project_id=p_bob_active.id, user_id=bob.id, role="owner"),
        ]
    )
    await db_session.flush()

    return {
        "alice": alice,
        "bob": bob,
        "p_alice_active": p_alice_active,
        "p_alice_archived": p_alice_archived,
        "p_bob_active": p_bob_active,
    }


# ─────────────── ProjectDAO ───────────────


async def test_project_dao_list_by_user_returns_only_active_member_projects(db_session, m02_seed):
    from api.dao.project_dao import ProjectDAO

    dao = ProjectDAO()
    rows = await dao.list_by_user(db_session, m02_seed["alice"].id)
    names = {p.name for p in rows}
    assert names == {"AliceActive"}, f"应只返回 alice 的 active project，got {names}"


async def test_project_dao_list_by_user_include_archived(db_session, m02_seed):
    from api.dao.project_dao import ProjectDAO

    dao = ProjectDAO()
    rows = await dao.list_by_user(db_session, m02_seed["alice"].id, include_archived=True)
    names = {p.name for p in rows}
    assert names == {"AliceActive", "AliceArchived"}


async def test_project_dao_list_by_user_excludes_other_users(db_session, m02_seed):
    """alice 不应看到 bob 的 project。"""
    from api.dao.project_dao import ProjectDAO

    dao = ProjectDAO()
    rows = await dao.list_by_user(db_session, m02_seed["alice"].id)
    names = {p.name for p in rows}
    assert "BobActive" not in names


async def test_project_dao_get_by_id_for_user_member_returns_project(db_session, m02_seed):
    from api.dao.project_dao import ProjectDAO

    dao = ProjectDAO()
    proj = await dao.get_by_id_for_user(
        db_session, m02_seed["p_alice_active"].id, m02_seed["alice"].id
    )
    assert proj is not None
    assert proj.name == "AliceActive"


async def test_project_dao_get_by_id_for_user_non_member_returns_none(db_session, m02_seed):
    """alice 拿 bob project id 应返回 None（tenant 过滤）。"""
    from api.dao.project_dao import ProjectDAO

    dao = ProjectDAO()
    proj = await dao.get_by_id_for_user(
        db_session, m02_seed["p_bob_active"].id, m02_seed["alice"].id
    )
    assert proj is None


async def test_project_dao_get_by_id_raw_no_tenant_check(db_session, m02_seed):
    """get_by_id 不带 tenant 过滤——只用于 service 内部已校验权限场景。"""
    from api.dao.project_dao import ProjectDAO

    dao = ProjectDAO()
    proj = await dao.get_by_id(db_session, m02_seed["p_bob_active"].id)
    assert proj is not None
    assert proj.name == "BobActive"


async def test_project_dao_create_inserts_row(db_session):
    from api.dao.project_dao import ProjectDAO
    from api.models.project import Project

    dao = ProjectDAO()
    user = await _make_user(db_session)
    proj = await dao.create(db_session, name="NewProj", owner_id=user.id)
    assert proj.id is not None

    r = await db_session.execute(select(Project).where(Project.id == proj.id))
    assert r.scalar_one().name == "NewProj"


# ─────────────── ProjectMemberDAO ───────────────


async def test_member_dao_list_by_project_returns_all_members(db_session, m02_seed):
    from api.dao.project_dao import ProjectMemberDAO

    dao = ProjectMemberDAO()
    members = await dao.list_by_project(db_session, m02_seed["p_alice_active"].id)
    assert len(members) == 1
    assert members[0].user_id == m02_seed["alice"].id


async def test_member_dao_get_member_returns_existing(db_session, m02_seed):
    from api.dao.project_dao import ProjectMemberDAO

    dao = ProjectMemberDAO()
    m = await dao.get_member(db_session, m02_seed["p_alice_active"].id, m02_seed["alice"].id)
    assert m is not None
    assert m.role == "owner"


async def test_member_dao_get_member_returns_none_for_non_member(db_session, m02_seed):
    """alice 不是 bob project 的 member。"""
    from api.dao.project_dao import ProjectMemberDAO

    dao = ProjectMemberDAO()
    m = await dao.get_member(db_session, m02_seed["p_bob_active"].id, m02_seed["alice"].id)
    assert m is None


async def test_member_dao_create_inserts_row(db_session, m02_seed):
    from api.dao.project_dao import ProjectMemberDAO

    dao = ProjectMemberDAO()
    new_user = await _make_user(db_session)
    m = await dao.create(
        db_session,
        project_id=m02_seed["p_alice_active"].id,
        user_id=new_user.id,
        role="editor",
        invited_by=m02_seed["alice"].id,
    )
    assert m.role == "editor"


async def test_member_dao_delete_removes_row(db_session, m02_seed):
    from api.dao.project_dao import ProjectMemberDAO
    from api.models.project import ProjectMember

    dao = ProjectMemberDAO()
    deleted = await dao.delete(db_session, m02_seed["p_alice_active"].id, m02_seed["alice"].id)
    assert deleted == 1

    r = await db_session.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == m02_seed["p_alice_active"].id,
            ProjectMember.user_id == m02_seed["alice"].id,
        )
    )
    assert r.scalar_one_or_none() is None


# ─────────────── ProjectDimensionConfigDAO ───────────────


async def test_dim_config_dao_list_by_project_empty(db_session, m02_seed):
    from api.dao.project_dao import ProjectDimensionConfigDAO

    dao = ProjectDimensionConfigDAO()
    rows = await dao.list_by_project(db_session, m02_seed["p_alice_active"].id)
    assert rows == []


async def test_dim_config_dao_create_and_list(db_session, m02_seed):
    from sqlalchemy import text

    from api.dao.project_dao import ProjectDimensionConfigDAO

    dao = ProjectDimensionConfigDAO()
    r = await db_session.execute(text("SELECT id FROM dimension_types WHERE key='default'"))
    dim_type_id = r.scalar_one()

    cfg = await dao.create(
        db_session,
        project_id=m02_seed["p_alice_active"].id,
        dimension_type_id=dim_type_id,
        enabled=True,
        sort_order=0,
    )
    assert cfg.id is not None

    rows = await dao.list_by_project(db_session, m02_seed["p_alice_active"].id)
    assert len(rows) == 1
    assert rows[0].dimension_type_id == dim_type_id


# ─────────────── DimensionTypeDAO ───────────────


async def test_dim_type_dao_list_all_includes_default_seed(db_session):
    from api.dao.project_dao import DimensionTypeDAO

    dao = DimensionTypeDAO()
    rows = await dao.list_all(db_session)
    keys = {r.key for r in rows}
    assert "default" in keys


# ─────────────── TenantContext concrete impl ───────────────


async def test_tenant_context_subquery_returns_user_accessible_project_ids(db_session, m02_seed):
    """M02 concrete impl 注入后，user_accessible_project_ids_subquery 返回 alice 可访问的 pid。"""
    from sqlalchemy import select as _select

    from api.auth import tenant_filter
    from api.dao.project_dao import M02TenantContext
    from api.models.project import Project

    tenant_filter.set_tenant_context(M02TenantContext())
    try:
        subq = tenant_filter.user_accessible_project_ids_subquery(db_session, m02_seed["alice"].id)
        # 应只含 alice 是 member 的 project（active+archived 都算，是否 active 由 caller 自己过滤）
        r = await db_session.execute(_select(Project.id).where(Project.id.in_(subq)))
        ids = {row[0] for row in r.all()}
        assert m02_seed["p_alice_active"].id in ids
        assert m02_seed["p_alice_archived"].id in ids
        assert m02_seed["p_bob_active"].id not in ids
    finally:
        tenant_filter.set_tenant_context(None)


async def test_tenant_filter_raises_when_not_initialized(db_session):
    """未注入时调用应 NotImplementedError（B2.4 scaffold 行为不变）。"""
    from api.auth import tenant_filter

    tenant_filter.set_tenant_context(None)
    with pytest.raises(NotImplementedError):
        tenant_filter.user_accessible_project_ids_subquery(db_session, uuid4())
