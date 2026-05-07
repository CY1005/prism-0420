"""M04 子片 2 — DimensionDAO 测试。

覆盖 design §9 主查询模式 + tenant 过滤 + 乐观锁 update_with_version。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from api.dao.dimension_dao import DimensionDAO
from api.models.dimension_record import DimensionRecord

# ─────────────── helpers ───────────────


async def _seed_dim_type(db_session, key: str = "t") -> int:
    from api.models.project import DimensionType

    dt = DimensionType(key=key, name=f"DT-{key}")
    db_session.add(dt)
    await db_session.flush()
    return dt.id


async def _make_record(
    db_session, *, user, project, node, type_id, content=None
) -> DimensionRecord:
    rec = DimensionRecord(
        node_id=node.id,
        project_id=project.id,
        dimension_type_id=type_id,
        content=content or {},
        created_by=user.id,
        updated_by=user.id,
    )
    db_session.add(rec)
    await db_session.flush()
    return rec


@pytest.fixture
def dao():
    return DimensionDAO()


# ─────────────── M04-DAO-T1 list_by_node ───────────────


async def test_dao_list_by_node_orders_by_type_id(db_session, dao, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    t2 = await _seed_dim_type(db_session, "t2")
    t1 = await _seed_dim_type(db_session, "t1")
    await _make_record(db_session, user=user, project=proj, node=node, type_id=t2)
    await _make_record(db_session, user=user, project=proj, node=node, type_id=t1)

    rows = await dao.list_by_node(db_session, node.id, proj.id)
    assert [r.dimension_type_id for r in rows] == sorted([t1, t2])


async def test_dao_list_by_node_isolates_tenants(db_session, dao, make_project, make_node):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    nB = await make_node(projB.id, name="B")
    type_id = await _seed_dim_type(db_session, "t")
    # Same dimension_type_id is allowed cross-project (only (node, type) is unique)
    await _make_record(db_session, user=user, project=projA, node=nA, type_id=type_id)
    await _make_record(db_session, user=user, project=projB, node=nB, type_id=type_id)

    rowsA = await dao.list_by_node(db_session, nA.id, projA.id)
    assert len(rowsA) == 1
    rowsCross = await dao.list_by_node(db_session, nA.id, projB.id)
    assert rowsCross == [], "B 项目查 A 节点的维度记录应空"


# ─────────────── M04-DAO-T2 get_by_id / get_one ───────────────


async def test_dao_get_by_id_returns_in_tenant(db_session, dao, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await _seed_dim_type(db_session, "t")
    rec = await _make_record(db_session, user=user, project=proj, node=node, type_id=type_id)

    found = await dao.get_by_id(db_session, rec.id, proj.id)
    assert found is not None
    assert found.id == rec.id


async def test_dao_get_by_id_blocks_cross_tenant(db_session, dao, make_project, make_node):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    type_id = await _seed_dim_type(db_session, "t")
    rec = await _make_record(db_session, user=user, project=projA, node=nA, type_id=type_id)

    found = await dao.get_by_id(db_session, rec.id, projB.id)
    assert found is None, "tenant 过滤：B 项目不应能查到 A 项目记录"


async def test_dao_get_one_by_node_and_type(db_session, dao, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await _seed_dim_type(db_session, "t_one")
    rec = await _make_record(db_session, user=user, project=proj, node=node, type_id=type_id)

    found = await dao.get_one(db_session, node.id, proj.id, type_id)
    assert found is not None
    assert found.id == rec.id

    none = await dao.get_one(db_session, node.id, proj.id, type_id + 9999)
    assert none is None


# ─────────────── M04-DAO-T3 list_by_nodes batch ───────────────


async def test_dao_list_by_nodes_filters_by_project_and_node_ids(
    db_session, dao, make_project, make_node
):
    user, proj = await make_project()
    n1 = await make_node(proj.id, name="n1")
    n2 = await make_node(proj.id, name="n2")
    n3 = await make_node(proj.id, name="n3")
    t = await _seed_dim_type(db_session, "tb")
    await _make_record(db_session, user=user, project=proj, node=n1, type_id=t)
    await _make_record(db_session, user=user, project=proj, node=n2, type_id=t)
    await _make_record(db_session, user=user, project=proj, node=n3, type_id=t)

    rows = await dao.list_by_nodes(db_session, [n1.id, n2.id], proj.id)
    assert {r.node_id for r in rows} == {n1.id, n2.id}


async def test_dao_list_by_nodes_filters_by_dimension_type_ids(
    db_session, dao, make_project, make_node
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    t1 = await _seed_dim_type(db_session, "tb1")
    t2 = await _seed_dim_type(db_session, "tb2")
    await _make_record(db_session, user=user, project=proj, node=node, type_id=t1)
    await _make_record(db_session, user=user, project=proj, node=node, type_id=t2)

    rows = await dao.list_by_nodes(db_session, [node.id], proj.id, [t1])
    assert len(rows) == 1
    assert rows[0].dimension_type_id == t1


async def test_dao_list_by_nodes_empty_input(db_session, dao, make_project):
    _, proj = await make_project()
    assert await dao.list_by_nodes(db_session, [], proj.id) == []
    # node_ids 非空但 type_ids 空 → 也应空
    assert await dao.list_by_nodes(db_session, [uuid4()], proj.id, []) == []


async def test_dao_list_by_nodes_blocks_cross_tenant(db_session, dao, make_project, make_node):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    t = await _seed_dim_type(db_session, "tb_x")
    await _make_record(db_session, user=user, project=projA, node=nA, type_id=t)

    rows = await dao.list_by_nodes(db_session, [nA.id], projB.id)
    assert rows == [], "B 项目用 A 节点 id 查不应返回 A 项目记录"


# ─────────────── M04-DAO-T4 count_by_node ───────────────


async def test_dao_count_by_node(db_session, dao, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    t1 = await _seed_dim_type(db_session, "c1")
    t2 = await _seed_dim_type(db_session, "c2")
    await _make_record(db_session, user=user, project=proj, node=node, type_id=t1)
    await _make_record(db_session, user=user, project=proj, node=node, type_id=t2)

    assert await dao.count_by_node(db_session, node.id, proj.id) == 2

    other = await make_node(proj.id, name="B")
    assert await dao.count_by_node(db_session, other.id, proj.id) == 0


# ─────────────── M04-DAO-T5 update_with_version 乐观锁 ───────────────


async def test_dao_update_with_version_increments(db_session, dao, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await _seed_dim_type(db_session, "tu")
    rec = await _make_record(db_session, user=user, project=proj, node=node, type_id=type_id)
    assert rec.version == 1

    rows = await dao.update_with_version(
        db_session,
        rec.id,
        proj.id,
        expected_version=1,
        content={"x": 1},
        updated_by=user.id,
    )
    assert rows == 1
    await db_session.refresh(rec)
    assert rec.version == 2
    assert rec.content == {"x": 1}


async def test_dao_update_with_version_conflict_returns_zero(
    db_session, dao, make_project, make_node
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await _seed_dim_type(db_session, "tu_c")
    rec = await _make_record(db_session, user=user, project=proj, node=node, type_id=type_id)

    rows = await dao.update_with_version(
        db_session,
        rec.id,
        proj.id,
        expected_version=999,  # 不匹配
        content={"x": 1},
        updated_by=user.id,
    )
    assert rows == 0, "乐观锁不匹配应返回 0 行"


async def test_dao_update_with_version_blocks_cross_tenant(
    db_session, dao, make_project, make_node
):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    type_id = await _seed_dim_type(db_session, "tu_x")
    rec = await _make_record(db_session, user=user, project=projA, node=nA, type_id=type_id)

    rows = await dao.update_with_version(
        db_session,
        rec.id,
        projB.id,  # 错误 tenant
        expected_version=1,
        content={"x": 1},
        updated_by=user.id,
    )
    assert rows == 0


async def test_dao_update_with_version_requires_fields(db_session, dao):
    with pytest.raises(ValueError):
        await dao.update_with_version(db_session, uuid4(), uuid4(), expected_version=1)


# ─────────────── M04-DAO-T6 delete_one ───────────────


async def test_dao_delete_one_returns_rowcount(db_session, dao, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await _seed_dim_type(db_session, "td")
    rec = await _make_record(db_session, user=user, project=proj, node=node, type_id=type_id)

    n = await dao.delete_one(db_session, rec.id, proj.id)
    assert n == 1
    found = await dao.get_by_id(db_session, rec.id, proj.id)
    assert found is None


async def test_dao_delete_one_blocks_cross_tenant(db_session, dao, make_project, make_node):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    type_id = await _seed_dim_type(db_session, "td_x")
    rec = await _make_record(db_session, user=user, project=projA, node=nA, type_id=type_id)

    n = await dao.delete_one(db_session, rec.id, projB.id)
    assert n == 0
    # 原记录仍在
    found = await dao.get_by_id(db_session, rec.id, projA.id)
    assert found is not None


# ─────────────── M04-DAO-T7 list_by_node_for_delete ───────────────


async def test_dao_list_by_node_for_delete_returns_records(
    db_session, dao, make_project, make_node
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    t1 = await _seed_dim_type(db_session, "tdel1")
    t2 = await _seed_dim_type(db_session, "tdel2")
    await _make_record(db_session, user=user, project=proj, node=node, type_id=t1)
    await _make_record(db_session, user=user, project=proj, node=node, type_id=t2)

    rows = await dao.list_by_node_for_delete(db_session, node.id, proj.id)
    assert len(rows) == 2


async def test_dao_list_by_node_for_delete_blocks_cross_tenant(
    db_session, dao, make_project, make_node
):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    t = await _seed_dim_type(db_session, "tdelx")
    await _make_record(db_session, user=user, project=projA, node=nA, type_id=t)

    rows = await dao.list_by_node_for_delete(db_session, nA.id, projB.id)
    assert rows == []
