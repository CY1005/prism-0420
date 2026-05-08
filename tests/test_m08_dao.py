"""M08 子片 2 — ModuleRelationDAO 测试。

覆盖 design §9 主查询模式 + tenant 过滤 + 双向 OR 条件 +
R-X2 delete_by_node_id 双向删除 + search_by_keyword（M09 pilot pass-through）。
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from api.dao.module_relation_dao import ModuleRelationDAO
from api.models.module_relation import ModuleRelation


@pytest.fixture
def dao():
    return ModuleRelationDAO()


async def _make_relation(
    db_session, *, user, project, source_node, target_node, relation_type="depends_on", notes=None
) -> ModuleRelation:
    r = ModuleRelation(
        project_id=project.id,
        source_node_id=source_node.id,
        target_node_id=target_node.id,
        relation_type=relation_type,
        notes=notes,
        created_by=user.id,
    )
    db_session.add(r)
    await db_session.flush()
    return r


# ─────────────── M08-DAO-T1 list_by_project / list_by_node 双向 ───────────────


async def test_dao_list_by_project_returns_all(db_session, dao, make_project, make_node):
    user, proj = await make_project()
    n1, n2, n3 = (
        await make_node(proj.id, name="A"),
        await make_node(proj.id, name="B"),
        await make_node(proj.id, name="C"),
    )
    await _make_relation(db_session, user=user, project=proj, source_node=n1, target_node=n2)
    await _make_relation(db_session, user=user, project=proj, source_node=n2, target_node=n3)
    rows = await dao.list_by_project(db_session, proj.id)
    assert len(rows) == 2


async def test_dao_list_by_node_bidirectional(db_session, dao, make_project, make_node):
    """双向 OR：list_by_node 既返 source=node 也返 target=node。"""
    user, proj = await make_project()
    n1, n2, n3 = (
        await make_node(proj.id, name="A"),
        await make_node(proj.id, name="B"),
        await make_node(proj.id, name="C"),
    )
    # n1 → n2（n1 出向）；n3 → n1（n1 入向）；n2 → n3（n1 无关）
    await _make_relation(db_session, user=user, project=proj, source_node=n1, target_node=n2)
    await _make_relation(db_session, user=user, project=proj, source_node=n3, target_node=n1)
    await _make_relation(db_session, user=user, project=proj, source_node=n2, target_node=n3)

    rows = await dao.list_by_node(db_session, n1.id, proj.id)
    assert len(rows) == 2, "n1 应有 1 出向 + 1 入向 = 2 条"


async def test_dao_list_by_project_isolates_tenants(db_session, dao, make_project, make_node):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA1, nA2 = await make_node(projA.id, name="A1"), await make_node(projA.id, name="A2")
    nB1, nB2 = await make_node(projB.id, name="B1"), await make_node(projB.id, name="B2")
    await _make_relation(db_session, user=user, project=projA, source_node=nA1, target_node=nA2)
    await _make_relation(db_session, user=user, project=projB, source_node=nB1, target_node=nB2)

    rowsA = await dao.list_by_project(db_session, projA.id)
    assert len(rowsA) == 1


# ─────────────── M08-DAO-T2 get_by_id + cross-tenant ───────────────


async def test_dao_get_by_id_in_tenant(db_session, dao, make_project, make_node):
    user, proj = await make_project()
    n1, n2 = await make_node(proj.id, name="A"), await make_node(proj.id, name="B")
    r = await _make_relation(db_session, user=user, project=proj, source_node=n1, target_node=n2)
    found = await dao.get_by_id(db_session, r.id, proj.id)
    assert found is not None and found.id == r.id


async def test_dao_get_by_id_blocks_cross_tenant(db_session, dao, make_project, make_node):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA1, nA2 = await make_node(projA.id, name="A1"), await make_node(projA.id, name="A2")
    r = await _make_relation(db_session, user=user, project=projA, source_node=nA1, target_node=nA2)
    found = await dao.get_by_id(db_session, r.id, projB.id)
    assert found is None


# ─────────────── M08-DAO-T3 update_notes / delete_by_id ───────────────


async def test_dao_update_notes(db_session, dao, make_project, make_node):
    user, proj = await make_project()
    n1, n2 = await make_node(proj.id, name="A"), await make_node(proj.id, name="B")
    r = await _make_relation(
        db_session, user=user, project=proj, source_node=n1, target_node=n2, notes="orig"
    )
    rows = await dao.update_notes(db_session, r.id, proj.id, notes="updated")
    assert rows == 1
    await db_session.refresh(r)
    assert r.notes == "updated"


async def test_dao_update_notes_blocks_cross_tenant(db_session, dao, make_project, make_node):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA1, nA2 = await make_node(projA.id, name="A1"), await make_node(projA.id, name="A2")
    r = await _make_relation(db_session, user=user, project=projA, source_node=nA1, target_node=nA2)
    rows = await dao.update_notes(db_session, r.id, projB.id, notes="hack")
    assert rows == 0


async def test_dao_delete_by_id(db_session, dao, make_project, make_node):
    user, proj = await make_project()
    n1, n2 = await make_node(proj.id, name="A"), await make_node(proj.id, name="B")
    r = await _make_relation(db_session, user=user, project=proj, source_node=n1, target_node=n2)
    rows = await dao.delete_by_id(db_session, r.id, proj.id)
    assert rows == 1
    assert await dao.get_by_id(db_session, r.id, proj.id) is None


# ─────────────── M08-DAO-T4 R-X2 delete_by_node_id 双向 ───────────────


async def test_dao_delete_by_node_id_bidirectional(db_session, dao, make_project, make_node):
    """R-X2: 双向 DELETE — n1 作 source 或 target 的所有 relation 都被删。"""
    user, proj = await make_project()
    n1, n2, n3 = (
        await make_node(proj.id, name="A"),
        await make_node(proj.id, name="B"),
        await make_node(proj.id, name="C"),
    )
    r1 = await _make_relation(db_session, user=user, project=proj, source_node=n1, target_node=n2)
    r2 = await _make_relation(db_session, user=user, project=proj, source_node=n3, target_node=n1)
    r3 = await _make_relation(db_session, user=user, project=proj, source_node=n2, target_node=n3)
    r1_id, r2_id, r3_id = r1.id, r2.id, r3.id

    rows = await dao.delete_by_node_id(db_session, n1.id, proj.id)
    assert rows == 2, "n1 出向+入向各 1 条 = 2 条删除"

    db_session.expire_all()
    res = await db_session.execute(
        text("SELECT id FROM module_relations WHERE id IN (:r1, :r2, :r3)"),
        {"r1": r1_id, "r2": r2_id, "r3": r3_id},
    )
    remaining = {row[0] for row in res.fetchall()}
    assert remaining == {r3_id}, "只剩 n2→n3（与 n1 无关）"


async def test_dao_delete_by_node_id_blocks_cross_tenant(db_session, dao, make_project, make_node):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA1, nA2 = await make_node(projA.id, name="A1"), await make_node(projA.id, name="A2")
    r = await _make_relation(db_session, user=user, project=projA, source_node=nA1, target_node=nA2)
    r_id = r.id

    rows = await dao.delete_by_node_id(db_session, nA1.id, projB.id)
    assert rows == 0
    # 直 SQL 验证（避免 expire 后 ORM cache 触发异步 IO）
    res = await db_session.execute(
        text("SELECT id FROM module_relations WHERE id = :id"), {"id": r_id}
    )
    assert res.scalar_one_or_none() == r_id, "B 项目不应能删 A 项目 relation"


async def test_dao_list_by_node_for_delete(db_session, dao, make_project, make_node):
    """R-X2 list_by_node_for_delete = list_by_node alias，双向。"""
    user, proj = await make_project()
    n1, n2 = await make_node(proj.id, name="A"), await make_node(proj.id, name="B")
    await _make_relation(db_session, user=user, project=proj, source_node=n1, target_node=n2)
    rows = await dao.list_by_node_for_delete(db_session, n1.id, proj.id)
    assert len(rows) == 1


# ─────────────── M08-DAO-T5 count_by_project + search_by_keyword ───────────────


async def test_dao_count_by_project(db_session, dao, make_project, make_node):
    user, proj = await make_project()
    n1, n2 = await make_node(proj.id, name="A"), await make_node(proj.id, name="B")
    await _make_relation(db_session, user=user, project=proj, source_node=n1, target_node=n2)
    assert await dao.count_by_project(db_session, proj.id) == 1


async def test_dao_search_by_keyword(db_session, dao, make_project, make_node):
    """M09 pilot pass-through: notes ilike。"""
    user, proj = await make_project()
    n1, n2 = await make_node(proj.id, name="A"), await make_node(proj.id, name="B")
    await _make_relation(
        db_session,
        user=user,
        project=proj,
        source_node=n1,
        target_node=n2,
        notes="performance critical path",
    )
    rows = await dao.search_by_keyword(db_session, "PERFORMANCE", proj.id)
    assert len(rows) == 1


async def test_dao_search_by_keyword_blocks_cross_tenant(db_session, dao, make_project, make_node):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA1, nA2 = await make_node(projA.id, name="A1"), await make_node(projA.id, name="A2")
    await _make_relation(
        db_session, user=user, project=projA, source_node=nA1, target_node=nA2, notes="secret"
    )
    rows = await dao.search_by_keyword(db_session, "secret", projB.id)
    assert rows == []
