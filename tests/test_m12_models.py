"""M12 子片 1 — ComparisonSnapshot + ComparisonSnapshotItem model 单元测试。

覆盖 design §3 SQLAlchemy block：
- 持久化 + 默认值（version=1 / nodes_ref=[] / dimensions_ref=[] / G2 无 status 字段）
- ON DELETE CASCADE on projects.id（snapshots）+ comparison_snapshots.id（items 级联）
- ON DELETE SET NULL on nodes.id（items.node_id；G4=B 不降级保留快照原值）
- JSONB 字段 nodes_ref / dimensions_ref / content
- relationship cascade='all, delete-orphan' + back_populates
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import delete, select

from api.models.comparison_snapshot import ComparisonSnapshot, ComparisonSnapshotItem
from api.models.node import Node

# ─────────────── M12-MODEL-T1 持久化基础 + 默认值 ───────────────


async def test_snapshot_persists_with_defaults(db_session, make_project):
    user, proj = await make_project()
    snap = ComparisonSnapshot(
        project_id=proj.id,
        user_id=user.id,
        name="Q4 对比",
    )
    db_session.add(snap)
    await db_session.flush()
    await db_session.refresh(snap)

    assert snap.id is not None
    assert snap.name == "Q4 对比"
    assert snap.nodes_ref == []
    assert snap.dimensions_ref == []
    assert snap.description is None
    assert snap.version == 1
    assert snap.created_at is not None
    assert snap.updated_at is not None


async def test_snapshot_stores_jsonb_refs(db_session, make_project):
    """nodes_ref / dimensions_ref JSONB 数组持久化。"""
    user, proj = await make_project()
    n_uuid = str(uuid4())
    snap = ComparisonSnapshot(
        project_id=proj.id,
        user_id=user.id,
        name="m",
        nodes_ref=[n_uuid],
        dimensions_ref=[1, 2, 3],
        description="desc",
    )
    db_session.add(snap)
    await db_session.flush()

    fetched = (
        await db_session.execute(select(ComparisonSnapshot).where(ComparisonSnapshot.id == snap.id))
    ).scalar_one()
    assert fetched.nodes_ref == [n_uuid]
    assert fetched.dimensions_ref == [1, 2, 3]
    assert fetched.description == "desc"


# ─────────────── M12-MODEL-T2 SnapshotItem 持久化 + 默认值 ───────────────


async def test_snapshot_item_persists(db_session, make_project, make_node, make_dim_type):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await make_dim_type(key="m12mod-t2")
    snap = ComparisonSnapshot(project_id=proj.id, user_id=user.id, name="x")
    db_session.add(snap)
    await db_session.flush()

    item = ComparisonSnapshotItem(
        snapshot_id=snap.id,
        node_id=node.id,
        dimension_type_id=type_id,
        content={"v": "hello"},
    )
    db_session.add(item)
    await db_session.flush()
    await db_session.refresh(item)
    assert item.id is not None
    assert item.snapshot_version == 1
    assert item.content == {"v": "hello"}


async def test_snapshot_item_content_nullable(db_session, make_project, make_node, make_dim_type):
    """content=None 表示当时该格未填写。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await make_dim_type(key="m12mod-null")
    snap = ComparisonSnapshot(project_id=proj.id, user_id=user.id, name="x")
    db_session.add(snap)
    await db_session.flush()

    item = ComparisonSnapshotItem(
        snapshot_id=snap.id,
        node_id=node.id,
        dimension_type_id=type_id,
        content=None,
    )
    db_session.add(item)
    await db_session.flush()


# ─────────────── M12-MODEL-T3 ON DELETE CASCADE on projects ───────────────


async def test_snapshot_cascades_with_project(db_session, make_project):
    """projects.id 删除 → comparison_snapshots 级联（同 M02-M11 范式）。"""
    user, proj = await make_project()
    snap = ComparisonSnapshot(project_id=proj.id, user_id=user.id, name="x")
    db_session.add(snap)
    await db_session.flush()
    snap_id = snap.id

    from api.models.project import Project

    await db_session.execute(delete(Project).where(Project.id == proj.id))
    await db_session.flush()

    fetched = (
        await db_session.execute(select(ComparisonSnapshot).where(ComparisonSnapshot.id == snap_id))
    ).scalar_one_or_none()
    assert fetched is None


# ─────────────── M12-MODEL-T4 ON DELETE CASCADE snapshot → items ───────────────


async def test_items_cascade_with_snapshot(db_session, make_project, make_node, make_dim_type):
    """删除 snapshot 时 items 级联（cascade='all, delete-orphan'）。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await make_dim_type(key="m12mod-cascade")
    snap = ComparisonSnapshot(project_id=proj.id, user_id=user.id, name="x")
    db_session.add(snap)
    await db_session.flush()
    item = ComparisonSnapshotItem(
        snapshot_id=snap.id,
        node_id=node.id,
        dimension_type_id=type_id,
        content={"v": "1"},
    )
    db_session.add(item)
    await db_session.flush()
    item_id = item.id

    await db_session.execute(delete(ComparisonSnapshot).where(ComparisonSnapshot.id == snap.id))
    await db_session.flush()

    fetched = (
        await db_session.execute(
            select(ComparisonSnapshotItem).where(ComparisonSnapshotItem.id == item_id)
        )
    ).scalar_one_or_none()
    assert fetched is None


# ─────────────── M12-MODEL-T5 ON DELETE SET NULL nodes → items.node_id（G4=B 不降级） ───────────────


async def test_node_delete_sets_item_node_id_null(
    db_session, make_project, make_node, make_dim_type
):
    """G4=B：节点被删后 items.node_id 设为 NULL，content 仍保留（快照不降级）。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await make_dim_type(key="m12mod-null-fk")
    snap = ComparisonSnapshot(project_id=proj.id, user_id=user.id, name="x")
    db_session.add(snap)
    await db_session.flush()
    item = ComparisonSnapshotItem(
        snapshot_id=snap.id,
        node_id=node.id,
        dimension_type_id=type_id,
        content={"v": "preserved"},
    )
    db_session.add(item)
    await db_session.flush()
    item_id = item.id

    await db_session.execute(delete(Node).where(Node.id == node.id))
    await db_session.flush()
    db_session.expire_all()

    fetched = (
        await db_session.execute(
            select(ComparisonSnapshotItem).where(ComparisonSnapshotItem.id == item_id)
        )
    ).scalar_one()
    assert fetched.node_id is None
    assert fetched.content == {"v": "preserved"}


# ─────────────── M12-MODEL-T6 relationship back_populates ───────────────


async def test_snapshot_items_relationship(db_session, make_project, make_node, make_dim_type):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    t1 = await make_dim_type(key="m12mod-rel-1")
    t2 = await make_dim_type(key="m12mod-rel-2")
    snap = ComparisonSnapshot(project_id=proj.id, user_id=user.id, name="x")
    db_session.add(snap)
    await db_session.flush()
    db_session.add_all(
        [
            ComparisonSnapshotItem(
                snapshot_id=snap.id, node_id=node.id, dimension_type_id=t1, content={"v": "1"}
            ),
            ComparisonSnapshotItem(
                snapshot_id=snap.id, node_id=node.id, dimension_type_id=t2, content={"v": "2"}
            ),
        ]
    )
    await db_session.flush()
    await db_session.refresh(snap, attribute_names=["items"])

    assert len(snap.items) == 2
    assert {it.dimension_type_id for it in snap.items} == {t1, t2}
    for it in snap.items:
        assert it.snapshot is snap


# ─────────────── M12-MODEL-T7 同名快照允许（无唯一约束） ───────────────


async def test_same_name_snapshots_allowed(db_session, make_project):
    user, proj = await make_project()
    s1 = ComparisonSnapshot(project_id=proj.id, user_id=user.id, name="dup")
    s2 = ComparisonSnapshot(project_id=proj.id, user_id=user.id, name="dup")
    db_session.add_all([s1, s2])
    await db_session.flush()
    assert s1.id != s2.id
