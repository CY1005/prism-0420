"""M05 子片 2 — VersionDAO 测试。

覆盖 design §9 主查询模式 + tenant 过滤 + (node, created_at DESC) 排序 +
clear_current_flag / set_current_flag / count_by_node。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from api.dao.version_dao import VersionDAO


@pytest.fixture
def dao():
    return VersionDAO()


# ─────────────── M05-DAO-T1 list_by_node 时间线排序 ───────────────


async def test_dao_list_by_node_orders_by_created_at_desc(
    db_session, dao, make_project, make_node, make_version
):
    """时间线 DESC：created_at 主序 + id DESC tie-break（同事务 now() 等值场景）。"""
    from datetime import UTC, datetime, timedelta

    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    base = datetime(2026, 5, 8, 12, 0, 0, tzinfo=UTC)
    v1 = await make_version(user=user, project=proj, node=node, label="v1")
    v1.created_at = base
    v2 = await make_version(user=user, project=proj, node=node, label="v2")
    v2.created_at = base + timedelta(seconds=1)
    v3 = await make_version(user=user, project=proj, node=node, label="v3")
    v3.created_at = base + timedelta(seconds=2)
    await db_session.flush()

    rows = await dao.list_by_node(db_session, node.id, proj.id)
    # 时间线要求 DESC：最新先（v3 时间最晚 → 最先返回）
    assert [r.id for r in rows] == [v3.id, v2.id, v1.id]


async def test_dao_list_by_node_isolates_tenants(
    db_session, dao, make_project, make_node, make_version
):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    nB = await make_node(projB.id, name="B")
    await make_version(user=user, project=projA, node=nA, label="vA")
    await make_version(user=user, project=projB, node=nB, label="vB")

    rowsA = await dao.list_by_node(db_session, nA.id, projA.id)
    assert len(rowsA) == 1
    rowsCross = await dao.list_by_node(db_session, nA.id, projB.id)
    assert rowsCross == [], "B 项目查 A 节点不应返回 A 数据"


async def test_dao_list_by_node_respects_limit(
    db_session, dao, make_project, make_node, make_version
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    for i in range(5):
        await make_version(user=user, project=proj, node=node, label=f"v{i}")

    rows = await dao.list_by_node(db_session, node.id, proj.id, limit=2)
    assert len(rows) == 2


# ─────────────── M05-DAO-T2 get_by_id ───────────────


async def test_dao_get_by_id_returns_in_tenant(
    db_session, dao, make_project, make_node, make_version
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    rec = await make_version(user=user, project=proj, node=node, label="v1")

    found = await dao.get_by_id(db_session, rec.id, proj.id)
    assert found is not None and found.id == rec.id


async def test_dao_get_by_id_blocks_cross_tenant(
    db_session, dao, make_project, make_node, make_version
):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    rec = await make_version(user=user, project=projA, node=nA, label="v1")

    found = await dao.get_by_id(db_session, rec.id, projB.id)
    assert found is None


async def test_dao_get_by_id_returns_none_when_missing(db_session, dao, make_project):
    _, proj = await make_project()
    found = await dao.get_by_id(db_session, uuid4(), proj.id)
    assert found is None


# ─────────────── M05-DAO-T3 get_current ───────────────


async def test_dao_get_current_returns_is_current_row(
    db_session, dao, make_project, make_node, make_version
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    await make_version(user=user, project=proj, node=node, label="v1")
    cur = await make_version(user=user, project=proj, node=node, label="v2", is_current=True)

    found = await dao.get_current(db_session, node.id, proj.id)
    assert found is not None and found.id == cur.id


async def test_dao_get_current_returns_none_when_no_current(
    db_session, dao, make_project, make_node, make_version
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    await make_version(user=user, project=proj, node=node, label="v1")

    assert await dao.get_current(db_session, node.id, proj.id) is None


# ─────────────── M05-DAO-T4 count_by_node ───────────────


async def test_dao_count_by_node(db_session, dao, make_project, make_node, make_version):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    for label in ("v1", "v2", "v3"):
        await make_version(user=user, project=proj, node=node, label=label)

    assert await dao.count_by_node(db_session, node.id, proj.id) == 3
    other = await make_node(proj.id, name="B")
    assert await dao.count_by_node(db_session, other.id, proj.id) == 0


async def test_dao_count_by_node_blocks_cross_tenant(
    db_session, dao, make_project, make_node, make_version
):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    await make_version(user=user, project=projA, node=nA, label="v1")

    assert await dao.count_by_node(db_session, nA.id, projB.id) == 0


# ─────────────── M05-DAO-T5 update_metadata ───────────────


async def test_dao_update_metadata_changes_fields(
    db_session, dao, make_project, make_node, make_version
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    rec = await make_version(user=user, project=proj, node=node, label="v1")

    rows = await dao.update_metadata(
        db_session,
        rec.id,
        proj.id,
        fields={"summary": "updated", "details": "more info"},
    )
    assert rows == 1
    await db_session.refresh(rec)
    assert rec.summary == "updated"
    assert rec.details == "more info"


async def test_dao_update_metadata_blocks_cross_tenant(
    db_session, dao, make_project, make_node, make_version
):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    rec = await make_version(user=user, project=projA, node=nA, label="v1")

    rows = await dao.update_metadata(db_session, rec.id, projB.id, fields={"summary": "hack"})
    assert rows == 0
    await db_session.refresh(rec)
    assert rec.summary == "s", "B 项目不应能改 A 项目记录"


async def test_dao_update_metadata_empty_fields_raises(db_session, dao):
    with pytest.raises(ValueError):
        await dao.update_metadata(db_session, uuid4(), uuid4(), fields={})


# ─────────────── M05-DAO-T6 clear_current_flag / set_current_flag ───────────────


async def test_dao_clear_current_flag_resets_existing(
    db_session, dao, make_project, make_node, make_version
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    cur = await make_version(user=user, project=proj, node=node, label="v1", is_current=True)

    rows = await dao.clear_current_flag(db_session, node.id, proj.id)
    assert rows == 1
    await db_session.refresh(cur)
    assert cur.is_current is False


async def test_dao_set_current_flag_marks(db_session, dao, make_project, make_node, make_version):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    rec = await make_version(user=user, project=proj, node=node, label="v1")

    rows = await dao.set_current_flag(db_session, rec.id, proj.id)
    assert rows == 1
    await db_session.refresh(rec)
    assert rec.is_current is True


async def test_dao_clear_current_flag_blocks_cross_tenant(
    db_session, dao, make_project, make_node, make_version
):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    cur = await make_version(user=user, project=projA, node=nA, label="v1", is_current=True)

    rows = await dao.clear_current_flag(db_session, nA.id, projB.id)
    assert rows == 0
    await db_session.refresh(cur)
    assert cur.is_current is True, "B 项目不应能清 A 项目 is_current"


# ─────────────── M05-DAO-T7 delete_by_id ───────────────


async def test_dao_delete_by_id(db_session, dao, make_project, make_node, make_version):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    rec = await make_version(user=user, project=proj, node=node, label="v1")

    rows = await dao.delete_by_id(db_session, rec.id, proj.id)
    assert rows == 1
    found = await dao.get_by_id(db_session, rec.id, proj.id)
    assert found is None


async def test_dao_delete_by_id_blocks_cross_tenant(
    db_session, dao, make_project, make_node, make_version
):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    rec = await make_version(user=user, project=projA, node=nA, label="v1")

    rows = await dao.delete_by_id(db_session, rec.id, projB.id)
    assert rows == 0
    found = await dao.get_by_id(db_session, rec.id, projA.id)
    assert found is not None
