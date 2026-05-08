"""M10 子片 1 — OverviewDAO 测试（纯读聚合）。

覆盖 design §9 主查询模式 + tenant 过滤 + 实时 JOIN（ADR-003 规则 2 豁免）。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from api.dao.overview_dao import OverviewDAO


@pytest.fixture
def dao():
    return OverviewDAO()


# ─────────────── M10-DAO-T1 count_enabled_dimensions ───────────────


async def test_dao_count_enabled_dimensions_basic(db_session, dao, make_project, make_dim_type):
    """count 启用维度（enabled=True 的 PDC 行数）。"""
    user, proj = await make_project()
    await make_dim_type(key="t1", project_id=proj.id, enabled=True)
    await make_dim_type(key="t2", project_id=proj.id, enabled=True)
    await make_dim_type(key="t3", project_id=proj.id, enabled=False)  # 不计

    assert await dao.count_enabled_dimensions(db_session, proj.id) == 2


async def test_dao_count_enabled_dimensions_zero(db_session, dao, make_project):
    _, proj = await make_project()
    assert await dao.count_enabled_dimensions(db_session, proj.id) == 0


async def test_dao_count_enabled_dimensions_isolates_tenants(
    db_session, dao, make_project, make_dim_type
):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    await make_dim_type(key="a", project_id=projA.id, enabled=True)
    await make_dim_type(key="b", project_id=projB.id, enabled=True)

    assert await dao.count_enabled_dimensions(db_session, projA.id) == 1
    assert await dao.count_enabled_dimensions(db_session, projB.id) == 1


# ─────────────── M10-DAO-T2 list_nodes_with_fill_count ───────────────


async def test_dao_list_nodes_with_fill_count_empty_project(db_session, dao, make_project):
    _, proj = await make_project()
    rows = await dao.list_nodes_with_fill_count(db_session, proj.id)
    assert rows == []


async def test_dao_list_nodes_with_fill_count_basic(
    db_session, dao, make_project, make_node, make_dim_type, make_dim_record
):
    user, proj = await make_project()
    n1 = await make_node(proj.id, name="A")
    n2 = await make_node(proj.id, name="B")
    t1 = await make_dim_type(key="t1", project_id=proj.id, enabled=True)
    t2 = await make_dim_type(key="t2", project_id=proj.id, enabled=True)
    # n1 填 2 维度 / n2 填 0 维度
    await make_dim_record(user=user, project=proj, node=n1, dim_type_id=t1)
    await make_dim_record(user=user, project=proj, node=n1, dim_type_id=t2)

    rows = await dao.list_nodes_with_fill_count(db_session, proj.id)
    by_id = {r["id"]: r for r in rows}
    assert by_id[n1.id]["filled_count"] == 2
    assert by_id[n2.id]["filled_count"] == 0


async def test_dao_list_nodes_with_fill_count_isolates_tenants(
    db_session, dao, make_project, make_node, make_dim_type, make_dim_record
):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    nB = await make_node(projB.id, name="B")
    t = await make_dim_type(key="t", project_id=projA.id, enabled=True)
    await make_dim_record(user=user, project=projA, node=nA, dim_type_id=t)

    rowsA = await dao.list_nodes_with_fill_count(db_session, projA.id)
    rowsB = await dao.list_nodes_with_fill_count(db_session, projB.id)
    assert {r["id"] for r in rowsA} == {nA.id}
    assert {r["id"] for r in rowsB} == {nB.id}
    # B 项目的节点 nB 的 filled_count 不应包含 A 项目的 dim_record
    assert rowsB[0]["filled_count"] == 0


# ─────────────── M10-DAO-T3 get_node_fill_count ───────────────


async def test_dao_get_node_fill_count_returns_count(
    db_session, dao, make_project, make_node, make_dim_type, make_dim_record
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    t = await make_dim_type(key="t", project_id=proj.id, enabled=True)
    await make_dim_record(user=user, project=proj, node=node, dim_type_id=t)

    info = await dao.get_node_fill_count(db_session, node.id, proj.id)
    assert info is not None
    assert info["filled_count"] == 1


async def test_dao_get_node_fill_count_missing_returns_none(db_session, dao, make_project):
    _, proj = await make_project()
    info = await dao.get_node_fill_count(db_session, uuid4(), proj.id)
    assert info is None


async def test_dao_get_node_fill_count_blocks_cross_tenant(
    db_session, dao, make_project, make_node
):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    info = await dao.get_node_fill_count(db_session, nA.id, projB.id)
    assert info is None
