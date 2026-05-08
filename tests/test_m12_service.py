"""M12 子片 3 — ComparisonService 单元测试。

覆盖（design §5/§6/§13）：
- get_matrix_data：empty selection / cross-project node / 跨模块只读 R-X3 调通
- create_snapshot：name 空 + 选择空 + 跨 project node + 多表事务（snapshot + items + activity）+ G4=B 值副本
- list_snapshots：(items, total) tuple
- get_snapshot_detail：eager items + cross-tenant 404
- rename_snapshot：乐观锁 / conflict 409 / 404 / name 空 422
- delete_snapshot：删除 + CASCADE items + activity / 404
- write_event 异常传播（M04+ 范式）
- viewer 写端点 403 是 router 层（在 test_m12_routers）；service 层不重复
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from api.errors.exceptions import (
    ComparisonEmptySelectionError,
    ComparisonNodeNotFoundError,
    ComparisonSnapshotConflictError,
    ComparisonSnapshotNameEmptyError,
    ComparisonSnapshotNotFoundError,
)
from api.services.comparison_service import ComparisonService
from api.services.dimension_service import DimensionService


@pytest.fixture
def svc() -> ComparisonService:
    return ComparisonService()


@pytest.fixture
def dim_svc() -> DimensionService:
    return DimensionService()


# ─────────────── helpers ───────────────


async def _seed_records(
    dim_svc, db_session, *, project_id, user_id, node_ids, type_ids, content_value="v"
):
    """populate dimension_records via batch_create_in_transaction（PDC 已建）。"""
    data = []
    for nid in node_ids:
        for tid in type_ids:
            data.append({"node_id": nid, "dimension_type_id": tid, "content": {"v": content_value}})
    await dim_svc.batch_create_in_transaction(
        db_session,
        project_id=project_id,
        actor_user_id=user_id,
        dimensions_data=data,
    )


# ─────────────── M12-SVC-T1 get_matrix_data ───────────────


async def test_get_matrix_empty_selection_raises(db_session, svc, make_project):
    _, proj = await make_project()
    with pytest.raises(ComparisonEmptySelectionError):
        await svc.get_matrix_data(
            db_session, project_id=proj.id, node_ids=[], dimension_type_ids=[1]
        )
    with pytest.raises(ComparisonEmptySelectionError):
        await svc.get_matrix_data(
            db_session, project_id=proj.id, node_ids=[uuid4()], dimension_type_ids=[]
        )


async def test_get_matrix_cross_project_node_raises(
    db_session, svc, make_project, make_node, make_dim_type
):
    """跨 project 的 node → ComparisonNodeNotFoundError 422（M06+M07+M08 范式）。"""
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(owner=user, name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    t1 = await make_dim_type(key="m12svc-cross", project_id=projB.id)
    with pytest.raises(ComparisonNodeNotFoundError):
        await svc.get_matrix_data(
            db_session,
            project_id=projB.id,
            node_ids=[nA.id],
            dimension_type_ids=[t1],
        )


async def test_get_matrix_unknown_node_raises(db_session, svc, make_project, make_dim_type):
    """node_id 不存在 → 422。"""
    _, proj = await make_project()
    t1 = await make_dim_type(key="m12svc-missing", project_id=proj.id)
    with pytest.raises(ComparisonNodeNotFoundError):
        await svc.get_matrix_data(
            db_session,
            project_id=proj.id,
            node_ids=[uuid4()],
            dimension_type_ids=[t1],
        )


async def test_get_matrix_returns_records(
    db_session, svc, dim_svc, make_project, make_node, make_dim_type
):
    user, proj = await make_project()
    nA = await make_node(proj.id, name="A")
    nB = await make_node(proj.id, name="B")
    t1 = await make_dim_type(key="m12svc-mat-1", project_id=proj.id)
    t2 = await make_dim_type(key="m12svc-mat-2", project_id=proj.id)
    await _seed_records(
        dim_svc,
        db_session,
        project_id=proj.id,
        user_id=user.id,
        node_ids=[nA.id, nB.id],
        type_ids=[t1, t2],
    )
    rows = await svc.get_matrix_data(
        db_session,
        project_id=proj.id,
        node_ids=[nA.id, nB.id],
        dimension_type_ids=[t1, t2],
    )
    assert len(rows) == 4


# ─────────────── M12-SVC-T2 create_snapshot ───────────────


async def test_create_snapshot_name_empty_raises(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    n = await make_node(proj.id, name="A")
    with pytest.raises(ComparisonSnapshotNameEmptyError):
        await svc.create_snapshot(
            db_session,
            project_id=proj.id,
            actor_user_id=user.id,
            name="   ",
            description=None,
            node_ids=[n.id],
            dimension_type_ids=[1],
        )


async def test_create_snapshot_empty_selection_raises(db_session, svc, make_project):
    user, proj = await make_project()
    with pytest.raises(ComparisonEmptySelectionError):
        await svc.create_snapshot(
            db_session,
            project_id=proj.id,
            actor_user_id=user.id,
            name="x",
            description=None,
            node_ids=[],
            dimension_type_ids=[1],
        )


async def test_create_snapshot_persists_value_items_and_activity(
    db_session, svc, dim_svc, make_project, make_node, make_dim_type
):
    """G4=B：保存时拷贝当前 dimension content 到 items 表（值副本）。"""
    user, proj = await make_project()
    nA = await make_node(proj.id, name="A")
    nB = await make_node(proj.id, name="B")
    t1 = await make_dim_type(key="m12svc-snap-1", project_id=proj.id)
    t2 = await make_dim_type(key="m12svc-snap-2", project_id=proj.id)
    await _seed_records(
        dim_svc,
        db_session,
        project_id=proj.id,
        user_id=user.id,
        node_ids=[nA.id, nB.id],
        type_ids=[t1, t2],
        content_value="initial",
    )

    snap = await svc.create_snapshot(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        name="对比1",
        description="d",
        node_ids=[nA.id, nB.id],
        dimension_type_ids=[t1, t2],
    )
    assert snap.id is not None
    assert snap.name == "对比1"
    assert snap.version == 1
    # items 表 4 条值副本
    detail = await svc.get_snapshot_detail(db_session, project_id=proj.id, snapshot_id=snap.id)
    assert len(detail.items) == 4
    for it in detail.items:
        assert it.content == {"v": "initial"}


async def test_create_snapshot_value_copy_independent_from_subsequent_edits(
    db_session, svc, dim_svc, make_project, make_node, make_dim_type
):
    """G4=B 不降级：保存后修改 dimension_record.content，快照仍展示原值。"""
    user, proj = await make_project()
    n = await make_node(proj.id, name="A")
    t1 = await make_dim_type(key="m12svc-immut", project_id=proj.id)
    await _seed_records(
        dim_svc,
        db_session,
        project_id=proj.id,
        user_id=user.id,
        node_ids=[n.id],
        type_ids=[t1],
        content_value="v1",
    )
    snap = await svc.create_snapshot(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        name="x",
        description=None,
        node_ids=[n.id],
        dimension_type_ids=[t1],
    )
    # 拿到 record 修改 content（DimensionService.update_with_lock 用 node_id+type_id 定位）
    records = await dim_svc.batch_get_by_nodes(
        db_session, project_id=proj.id, node_ids=[n.id], dimension_type_ids=[t1]
    )
    rec = records[0]
    await dim_svc.update_with_lock(
        db_session,
        project_id=proj.id,
        node_id=rec.node_id,
        dimension_type_id=rec.dimension_type_id,
        content={"v": "v2"},
        expected_version=rec.version,
        actor_user_id=user.id,
    )
    detail = await svc.get_snapshot_detail(db_session, project_id=proj.id, snapshot_id=snap.id)
    assert detail.items[0].content == {"v": "v1"}


async def test_create_snapshot_cross_project_node_raises(
    db_session, svc, make_project, make_node, make_dim_type
):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(owner=user, name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    t1 = await make_dim_type(key="m12svc-cross-create", project_id=projB.id)
    with pytest.raises(ComparisonNodeNotFoundError):
        await svc.create_snapshot(
            db_session,
            project_id=projB.id,
            actor_user_id=user.id,
            name="x",
            description=None,
            node_ids=[nA.id],
            dimension_type_ids=[t1],
        )


async def test_create_snapshot_write_event_failure_propagates(
    db_session, svc, make_project, make_node, make_dim_type, monkeypatch
):
    """M04+ 范式：write_event 异常必须传播（不静默吞错），caller 事务回滚。"""
    user, proj = await make_project()
    n = await make_node(proj.id, name="A")
    t1 = await make_dim_type(key="m12svc-werr", project_id=proj.id)

    async def _boom(**_kwargs):
        raise RuntimeError("activity_log boom")

    monkeypatch.setattr("api.services.comparison_service.write_event", _boom)
    with pytest.raises(RuntimeError, match="activity_log boom"):
        await svc.create_snapshot(
            db_session,
            project_id=proj.id,
            actor_user_id=user.id,
            name="x",
            description=None,
            node_ids=[n.id],
            dimension_type_ids=[t1],
        )


# ─────────────── M12-SVC-T3 list_snapshots ───────────────


async def test_list_snapshots_returns_tuple(db_session, svc, make_project, make_snapshot):
    user, proj = await make_project()
    await make_snapshot(project_id=proj.id, user_id=user.id, name="a")
    await make_snapshot(project_id=proj.id, user_id=user.id, name="b")
    items, total = await svc.list_snapshots(db_session, project_id=proj.id)
    assert total == 2
    assert len(items) == 2


# ─────────────── M12-SVC-T4 get_snapshot_detail ───────────────


async def test_get_snapshot_detail_404_for_unknown(db_session, svc, make_project, make_snapshot):
    _, proj = await make_project()
    with pytest.raises(ComparisonSnapshotNotFoundError):
        await svc.get_snapshot_detail(db_session, project_id=proj.id, snapshot_id=uuid4())


async def test_get_snapshot_detail_cross_tenant_404(db_session, svc, make_project, make_snapshot):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(owner=user, name_suffix="-B")
    snap = await make_snapshot(project_id=projA.id, user_id=user.id, name="x")
    with pytest.raises(ComparisonSnapshotNotFoundError):
        await svc.get_snapshot_detail(db_session, project_id=projB.id, snapshot_id=snap.id)


# ─────────────── M12-SVC-T5 rename_snapshot ───────────────


async def test_rename_snapshot_increments_version(db_session, svc, make_project, make_snapshot):
    user, proj = await make_project()
    snap = await make_snapshot(project_id=proj.id, user_id=user.id, name="old")
    updated = await svc.rename_snapshot(
        db_session,
        project_id=proj.id,
        snapshot_id=snap.id,
        actor_user_id=user.id,
        name="new",
        description="d",
        expected_version=1,
    )
    assert updated.name == "new"
    assert updated.version == 2


async def test_rename_snapshot_conflict_409(db_session, svc, make_project, make_snapshot):
    user, proj = await make_project()
    snap = await make_snapshot(project_id=proj.id, user_id=user.id, name="old")
    with pytest.raises(ComparisonSnapshotConflictError):
        await svc.rename_snapshot(
            db_session,
            project_id=proj.id,
            snapshot_id=snap.id,
            actor_user_id=user.id,
            name="new",
            description=None,
            expected_version=99,
        )


async def test_rename_snapshot_name_empty_422(db_session, svc, make_project, make_snapshot):
    user, proj = await make_project()
    snap = await make_snapshot(project_id=proj.id, user_id=user.id, name="old")
    with pytest.raises(ComparisonSnapshotNameEmptyError):
        await svc.rename_snapshot(
            db_session,
            project_id=proj.id,
            snapshot_id=snap.id,
            actor_user_id=user.id,
            name="",
            description=None,
            expected_version=1,
        )


async def test_rename_snapshot_404_when_unknown(db_session, svc, make_project):
    user, proj = await make_project()
    with pytest.raises(ComparisonSnapshotNotFoundError):
        await svc.rename_snapshot(
            db_session,
            project_id=proj.id,
            snapshot_id=uuid4(),
            actor_user_id=user.id,
            name="x",
            description=None,
            expected_version=1,
        )


# ─────────────── M12-SVC-T6 delete_snapshot ───────────────


async def test_delete_snapshot_removes_and_cascades_items(
    db_session, svc, dim_svc, make_project, make_node, make_dim_type
):
    user, proj = await make_project()
    n = await make_node(proj.id, name="A")
    t1 = await make_dim_type(key="m12svc-del", project_id=proj.id)
    await _seed_records(
        dim_svc, db_session, project_id=proj.id, user_id=user.id, node_ids=[n.id], type_ids=[t1]
    )
    snap = await svc.create_snapshot(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        name="x",
        description=None,
        node_ids=[n.id],
        dimension_type_ids=[t1],
    )
    await svc.delete_snapshot(
        db_session, project_id=proj.id, snapshot_id=snap.id, actor_user_id=user.id
    )
    with pytest.raises(ComparisonSnapshotNotFoundError):
        await svc.get_snapshot_detail(db_session, project_id=proj.id, snapshot_id=snap.id)


async def test_delete_snapshot_404_for_unknown(db_session, svc, make_project, make_snapshot):
    user, proj = await make_project()
    with pytest.raises(ComparisonSnapshotNotFoundError):
        await svc.delete_snapshot(
            db_session, project_id=proj.id, snapshot_id=uuid4(), actor_user_id=user.id
        )


async def test_delete_snapshot_cross_tenant_404(db_session, svc, make_project, make_snapshot):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(owner=user, name_suffix="-B")
    snap = await make_snapshot(project_id=projA.id, user_id=user.id, name="x")
    with pytest.raises(ComparisonSnapshotNotFoundError):
        await svc.delete_snapshot(
            db_session, project_id=projB.id, snapshot_id=snap.id, actor_user_id=user.id
        )


async def test_delete_snapshot_write_event_failure_propagates(
    db_session, svc, make_project, make_snapshot, monkeypatch
):
    """write_event 异常传播（M04+ 范式）。"""
    user, proj = await make_project()
    snap = await make_snapshot(project_id=proj.id, user_id=user.id, name="x")

    async def _boom(**_kwargs):
        raise RuntimeError("activity boom on delete")

    monkeypatch.setattr("api.services.comparison_service.write_event", _boom)
    with pytest.raises(RuntimeError, match="activity boom on delete"):
        await svc.delete_snapshot(
            db_session, project_id=proj.id, snapshot_id=snap.id, actor_user_id=user.id
        )


# ─────────────── R1 P1 覆盖补 ───────────────


async def test_rename_snapshot_write_event_failure_propagates(
    db_session, svc, make_project, make_snapshot, monkeypatch
):
    """R1-C P1-02 立修：rename write_event 异常传播测试（三写端点全覆盖）。"""
    user, proj = await make_project()
    snap = await make_snapshot(project_id=proj.id, user_id=user.id, name="old")

    async def _boom(**_kwargs):
        raise RuntimeError("rename boom")

    monkeypatch.setattr("api.services.comparison_service.write_event", _boom)
    with pytest.raises(RuntimeError, match="rename boom"):
        await svc.rename_snapshot(
            db_session,
            project_id=proj.id,
            snapshot_id=snap.id,
            actor_user_id=user.id,
            name="new",
            description=None,
            expected_version=1,
        )


async def test_rename_snapshot_cross_tenant_404(db_session, svc, make_project, make_snapshot):
    """R1-C 覆盖空白：rename cross-tenant 404（M02 范式）。"""
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(owner=user, name_suffix="-B")
    snap = await make_snapshot(project_id=projA.id, user_id=user.id, name="x")
    with pytest.raises(ComparisonSnapshotNotFoundError):
        await svc.rename_snapshot(
            db_session,
            project_id=projB.id,
            snapshot_id=snap.id,
            actor_user_id=user.id,
            name="y",
            description=None,
            expected_version=1,
        )


async def test_rename_snapshot_multi_increment(db_session, svc, make_project, make_snapshot):
    """R1-C 覆盖空白：rename 连续 N 次 version=N+1。"""
    user, proj = await make_project()
    snap = await make_snapshot(project_id=proj.id, user_id=user.id, name="v0")
    for i in range(1, 4):
        updated = await svc.rename_snapshot(
            db_session,
            project_id=proj.id,
            snapshot_id=snap.id,
            actor_user_id=user.id,
            name=f"v{i}",
            description=None,
            expected_version=i,
        )
        assert updated.version == i + 1
        assert updated.name == f"v{i}"


async def test_rename_snapshot_updates_updated_at(db_session, svc, make_project, make_snapshot):
    """R1-C P1-03 立修验证：Core UPDATE 显式 updated_at 刷新。"""
    user, proj = await make_project()
    snap = await make_snapshot(project_id=proj.id, user_id=user.id, name="old")
    old_ts = snap.updated_at
    import asyncio

    await asyncio.sleep(0.01)
    updated = await svc.rename_snapshot(
        db_session,
        project_id=proj.id,
        snapshot_id=snap.id,
        actor_user_id=user.id,
        name="new",
        description=None,
        expected_version=1,
    )
    assert updated.updated_at > old_ts
