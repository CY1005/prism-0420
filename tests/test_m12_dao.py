"""M12 子片 2 — ComparisonDAO 单元测试（design §9 tenant 过滤 + R-X3 共享 session）。"""

from __future__ import annotations

from uuid import uuid4

import pytest

from api.dao.comparison_dao import ComparisonDAO
from api.models.comparison_snapshot import ComparisonSnapshot, ComparisonSnapshotItem


@pytest.fixture
def dao() -> ComparisonDAO:
    return ComparisonDAO()


# ─────────────── helpers ───────────────


async def _mk_snap(db_session, project_id, user_id, *, name="x", **extra):
    snap = ComparisonSnapshot(project_id=project_id, user_id=user_id, name=name, **extra)
    db_session.add(snap)
    await db_session.flush()
    return snap


# ─────────────── M12-DAO-T1 list/get/count + tenant 过滤 ───────────────


async def test_list_snapshots_tenant_isolated(db_session, dao, make_project):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(owner=user, name_suffix="-B")
    await _mk_snap(db_session, projA.id, user.id, name="A1")
    await _mk_snap(db_session, projA.id, user.id, name="A2")
    await _mk_snap(db_session, projB.id, user.id, name="B1")

    rows = await dao.list_snapshots(db_session, projA.id)
    assert {r.name for r in rows} == {"A1", "A2"}
    rows_b = await dao.list_snapshots(db_session, projB.id)
    assert {r.name for r in rows_b} == {"B1"}


async def test_list_snapshots_orders_created_desc(db_session, dao, make_project):
    """ORDER BY created_at DESC（M05/M07/M11 同款 tie-break 处理：显式 created_at 偏移）。"""
    from datetime import UTC, datetime, timedelta

    user, proj = await make_project()
    base = datetime.now(UTC)
    s1 = await _mk_snap(
        db_session, proj.id, user.id, name="first", created_at=base, updated_at=base
    )
    s2 = await _mk_snap(
        db_session,
        proj.id,
        user.id,
        name="second",
        created_at=base + timedelta(seconds=1),
        updated_at=base + timedelta(seconds=1),
    )
    rows = await dao.list_snapshots(db_session, proj.id)
    assert rows[0].id == s2.id
    assert rows[1].id == s1.id


async def test_count_snapshots_tenant_isolated(db_session, dao, make_project):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(owner=user, name_suffix="-B")
    await _mk_snap(db_session, projA.id, user.id)
    await _mk_snap(db_session, projA.id, user.id)
    await _mk_snap(db_session, projB.id, user.id)
    assert await dao.count_snapshots(db_session, projA.id) == 2
    assert await dao.count_snapshots(db_session, projB.id) == 1


async def test_get_snapshot_returns_none_cross_tenant(db_session, dao, make_project):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(owner=user, name_suffix="-B")
    snap = await _mk_snap(db_session, projA.id, user.id)
    assert await dao.get_snapshot(db_session, snap.id, projA.id) is not None
    # 跨租户 → None（M02 范式：不暴露存在）
    assert await dao.get_snapshot(db_session, snap.id, projB.id) is None


async def test_get_snapshot_returns_none_unknown_id(db_session, dao, make_project):
    _, proj = await make_project()
    assert await dao.get_snapshot(db_session, uuid4(), proj.id) is None


# ─────────────── M12-DAO-T2 get_snapshot_with_items eager load ───────────────


async def test_get_snapshot_with_items_loads_items(
    db_session, dao, make_project, make_node, make_dim_type
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    t1 = await make_dim_type(key="m12dao-t1")
    snap = await _mk_snap(db_session, proj.id, user.id)
    db_session.add(
        ComparisonSnapshotItem(
            snapshot_id=snap.id, node_id=node.id, dimension_type_id=t1, content={"v": "1"}
        )
    )
    await db_session.flush()

    fetched = await dao.get_snapshot_with_items(db_session, snap.id, proj.id)
    assert fetched is not None
    assert len(fetched.items) == 1
    assert fetched.items[0].content == {"v": "1"}


# ─────────────── M12-DAO-T3 list_items_by_snapshot 双重 tenant 过滤 ───────────────


async def test_list_items_blocks_cross_tenant_via_join(
    db_session, dao, make_project, make_node, make_dim_type
):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(owner=user, name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    t1 = await make_dim_type(key="m12dao-cross")
    snap = await _mk_snap(db_session, projA.id, user.id)
    db_session.add(
        ComparisonSnapshotItem(
            snapshot_id=snap.id, node_id=nA.id, dimension_type_id=t1, content={"v": "x"}
        )
    )
    await db_session.flush()

    items_correct = await dao.list_items_by_snapshot(db_session, snap.id, projA.id)
    assert len(items_correct) == 1
    items_cross = await dao.list_items_by_snapshot(db_session, snap.id, projB.id)
    assert items_cross == []


# ─────────────── M12-DAO-T4 update_snapshot_with_version 乐观锁 ───────────────


async def test_update_with_version_increments_version(db_session, dao, make_project):
    user, proj = await make_project()
    snap = await _mk_snap(db_session, proj.id, user.id, name="old")

    rows = await dao.update_snapshot_with_version(
        db_session,
        snap.id,
        proj.id,
        expected_version=1,
        name="new",
    )
    assert rows == 1
    await db_session.refresh(snap)
    assert snap.name == "new"
    assert snap.version == 2


async def test_update_with_version_conflict_returns_zero(db_session, dao, make_project):
    user, proj = await make_project()
    snap = await _mk_snap(db_session, proj.id, user.id)
    # 错误的 expected_version
    rows = await dao.update_snapshot_with_version(
        db_session, snap.id, proj.id, expected_version=99, name="new"
    )
    assert rows == 0


async def test_update_with_version_cross_tenant_returns_zero(db_session, dao, make_project):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(owner=user, name_suffix="-B")
    snap = await _mk_snap(db_session, projA.id, user.id)
    rows = await dao.update_snapshot_with_version(
        db_session, snap.id, projB.id, expected_version=1, name="new"
    )
    assert rows == 0


async def test_update_with_version_empty_fields_raises(db_session, dao, make_project):
    user, proj = await make_project()
    snap = await _mk_snap(db_session, proj.id, user.id)
    with pytest.raises(ValueError):
        await dao.update_snapshot_with_version(db_session, snap.id, proj.id, expected_version=1)


# ─────────────── M12-DAO-T5 delete_snapshot tenant 过滤 ───────────────


async def test_delete_snapshot_returns_one(db_session, dao, make_project):
    user, proj = await make_project()
    snap = await _mk_snap(db_session, proj.id, user.id)
    rows = await dao.delete_snapshot(db_session, snap.id, proj.id)
    assert rows == 1
    assert await dao.get_snapshot(db_session, snap.id, proj.id) is None


async def test_delete_snapshot_cross_tenant_returns_zero(db_session, dao, make_project):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(owner=user, name_suffix="-B")
    snap = await _mk_snap(db_session, projA.id, user.id)
    rows = await dao.delete_snapshot(db_session, snap.id, projB.id)
    assert rows == 0
    # 仍存在
    assert await dao.get_snapshot(db_session, snap.id, projA.id) is not None


async def test_delete_snapshot_unknown_returns_zero(db_session, dao, make_project):
    _, proj = await make_project()
    rows = await dao.delete_snapshot(db_session, uuid4(), proj.id)
    assert rows == 0


# ─────────────── M12-DAO-T6 bulk_insert_items ───────────────


async def test_bulk_insert_items_persists(db_session, dao, make_project, make_node, make_dim_type):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    t1 = await make_dim_type(key="m12dao-bulk-1")
    t2 = await make_dim_type(key="m12dao-bulk-2")
    snap = await _mk_snap(db_session, proj.id, user.id)

    items = [
        ComparisonSnapshotItem(
            snapshot_id=snap.id, node_id=node.id, dimension_type_id=t1, content={"v": "1"}
        ),
        ComparisonSnapshotItem(
            snapshot_id=snap.id, node_id=node.id, dimension_type_id=t2, content={"v": "2"}
        ),
    ]
    await dao.bulk_insert_items(db_session, items)
    out = await dao.list_items_by_snapshot(db_session, snap.id, proj.id)
    assert len(out) == 2


async def test_bulk_insert_items_empty_noop(db_session, dao):
    """空 list 应早返回不报错。"""
    await dao.bulk_insert_items(db_session, [])
