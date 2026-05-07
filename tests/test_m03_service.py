"""M03 子片 3 — NodeService CRUD + path 计算 + activity_log + R-X2 R10-1。

覆盖 design §6 + §10 activity_log 5 类事件 + §13 ErrorCode raise 路径
+ G5 path 计算策略 + G5 move 循环检查 + R10-1 batch3 per-node 事件。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from api.errors.exceptions import (
    NodeMoveCycleDetectedError,
    NodeNotFoundError,
    NodeParentNotFoundError,
    NodeReorderInvalidError,
    NodeTypeImmutableError,
)
from api.models.node import NodeType
from api.services.node_service import (
    NodeService,
    clear_child_services,
    register_child_service,
)

# ─────────────── helpers ───────────────


async def _make_user_and_project(db_session, *, name_suffix: str = ""):
    from api.auth.password import hash_password
    from api.models.project import Project
    from api.models.user import User

    user = User(
        email=f"u-{uuid4().hex[:8]}@example.com",
        name="X",
        password_hash=hash_password("Password123!"),
        role="user",
        status="active",
        failed_login_count=0,
        version=1,
    )
    db_session.add(user)
    await db_session.flush()

    proj = Project(name=f"P-{uuid4().hex[:6]}{name_suffix}", owner_id=user.id)
    db_session.add(proj)
    await db_session.flush()
    return user, proj


@pytest.fixture
def svc():
    return NodeService()


@pytest.fixture(autouse=True)
def _clean_child_services():
    clear_child_services()
    yield
    clear_child_services()


# ─────────────── M03-Svc-T1 create_node 路径计算 ───────────────


async def test_svc_create_root_path_format(db_session, svc):
    user, proj = await _make_user_and_project(db_session)
    node = await svc.create_node(db_session, project_id=proj.id, actor_user_id=user.id, name="root")
    assert node.path == f"/{node.id}/"
    assert node.depth == 0
    assert node.parent_id is None
    assert node.sort_order == 0
    assert node.type == NodeType.FOLDER.value


async def test_svc_create_child_path_format(db_session, svc):
    user, proj = await _make_user_and_project(db_session)
    root = await svc.create_node(db_session, project_id=proj.id, actor_user_id=user.id, name="root")
    child = await svc.create_node(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        name="child",
        parent_id=root.id,
    )
    assert child.path == f"{root.path}{child.id}/"
    assert child.depth == 1


async def test_svc_create_sort_order_auto_increment(db_session, svc):
    user, proj = await _make_user_and_project(db_session)
    a = await svc.create_node(db_session, project_id=proj.id, actor_user_id=user.id, name="a")
    b = await svc.create_node(db_session, project_id=proj.id, actor_user_id=user.id, name="b")
    c = await svc.create_node(db_session, project_id=proj.id, actor_user_id=user.id, name="c")
    assert a.sort_order == 0
    assert b.sort_order == 1
    assert c.sort_order == 2


async def test_svc_create_parent_not_found(db_session, svc):
    user, proj = await _make_user_and_project(db_session)
    with pytest.raises(NodeParentNotFoundError):
        await svc.create_node(
            db_session,
            project_id=proj.id,
            actor_user_id=user.id,
            name="x",
            parent_id=uuid4(),
        )


async def test_svc_create_parent_cross_tenant_blocks(db_session, svc):
    """parent_id 来自其他项目应抛 NodeParentNotFoundError（不暴露跨租户）。"""
    user, projA = await _make_user_and_project(db_session, name_suffix="-A")
    _, projB = await _make_user_and_project(db_session, name_suffix="-B")

    parentA = await svc.create_node(
        db_session, project_id=projA.id, actor_user_id=user.id, name="A-root"
    )
    with pytest.raises(NodeParentNotFoundError):
        await svc.create_node(
            db_session,
            project_id=projB.id,
            actor_user_id=user.id,
            name="x",
            parent_id=parentA.id,  # 跨租户 parent
        )


# ─────────────── M03-Svc-T2 update_node ───────────────


async def test_svc_update_changes_name(db_session, svc):
    user, proj = await _make_user_and_project(db_session)
    n = await svc.create_node(db_session, project_id=proj.id, actor_user_id=user.id, name="old")
    updated = await svc.update_node(
        db_session,
        project_id=proj.id,
        node_id=n.id,
        actor_user_id=user.id,
        name="new",
    )
    assert updated.name == "new"


async def test_svc_update_type_immutable_raises(db_session, svc):
    user, proj = await _make_user_and_project(db_session)
    n = await svc.create_node(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        name="x",
        type=NodeType.FOLDER.value,
    )
    with pytest.raises(NodeTypeImmutableError):
        await svc.update_node(
            db_session,
            project_id=proj.id,
            node_id=n.id,
            actor_user_id=user.id,
            type=NodeType.FILE.value,
        )


async def test_svc_update_node_not_found(db_session, svc):
    user, proj = await _make_user_and_project(db_session)
    with pytest.raises(NodeNotFoundError):
        await svc.update_node(
            db_session,
            project_id=proj.id,
            node_id=uuid4(),
            actor_user_id=user.id,
            name="x",
        )


# ─────────────── M03-Svc-T3 delete_node R-X2 + R10-1 ───────────────


async def test_svc_delete_subtree_cascades_and_writes_per_node_events(db_session, svc, monkeypatch):
    """R10-1 batch3：每节点独立 delete 事件 + DB CASCADE 删子树。"""
    user, proj = await _make_user_and_project(db_session)
    root = await svc.create_node(db_session, project_id=proj.id, actor_user_id=user.id, name="root")
    child = await svc.create_node(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        name="c",
        parent_id=root.id,
    )
    grandchild = await svc.create_node(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        name="gc",
        parent_id=child.id,
    )

    captured: list[dict] = []

    async def fake_write_event(**kwargs):
        captured.append(kwargs)

    # M15 stub 替换为 list collector（注意 service 模块 import 的命名空间）
    monkeypatch.setattr("api.services.node_service.write_event", fake_write_event)

    await svc.delete_node(
        db_session,
        project_id=proj.id,
        node_id=root.id,
        actor_user_id=user.id,
    )

    # DB 全删
    from sqlalchemy import select

    from api.models.node import Node

    rows = await db_session.execute(select(Node).where(Node.project_id == proj.id))
    assert rows.scalars().all() == []

    # R10-1 batch3: 子树每节点独立 delete 事件
    delete_targets = {ev["target_id"] for ev in captured if ev.get("action_type") == "delete"}
    assert delete_targets == {str(root.id), str(child.id), str(grandchild.id)}


async def test_svc_delete_calls_registered_child_services(db_session, svc):
    """R-X2: 子树每节点都调注册的 child_services（M04/M06/M07 sprint 期注入）。"""
    user, proj = await _make_user_and_project(db_session)
    root = await svc.create_node(db_session, project_id=proj.id, actor_user_id=user.id, name="root")
    child = await svc.create_node(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        name="c",
        parent_id=root.id,
    )

    called: list[tuple[str, str]] = []

    async def fake_dimension_svc(db, node_id, project_id):
        called.append(("dimension", str(node_id)))

    async def fake_competitor_svc(db, node_id, project_id):
        called.append(("competitor", str(node_id)))

    register_child_service("dimension", fake_dimension_svc)
    register_child_service("competitor", fake_competitor_svc)

    await svc.delete_node(db_session, project_id=proj.id, node_id=root.id, actor_user_id=user.id)

    # 子树 2 节点 × 2 service = 4 调用
    assert len(called) == 4
    target_ids_called = {nid for _, nid in called}
    assert {str(root.id), str(child.id)} == target_ids_called


async def test_svc_delete_node_not_found(db_session, svc):
    user, proj = await _make_user_and_project(db_session)
    with pytest.raises(NodeNotFoundError):
        await svc.delete_node(
            db_session,
            project_id=proj.id,
            node_id=uuid4(),
            actor_user_id=user.id,
        )


# ─────────────── M03-Svc-T4 reorder_siblings ───────────────


async def test_svc_reorder_updates_sort_order(db_session, svc):
    user, proj = await _make_user_and_project(db_session)
    a = await svc.create_node(db_session, project_id=proj.id, actor_user_id=user.id, name="a")
    b = await svc.create_node(db_session, project_id=proj.id, actor_user_id=user.id, name="b")

    rows = await svc.reorder_siblings(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        parent_id=None,
        items=[(a.id, 5), (b.id, 0)],
    )
    by_id = {r.id: r for r in rows}
    assert by_id[a.id].sort_order == 5
    assert by_id[b.id].sort_order == 0


async def test_svc_reorder_rejects_cross_parent(db_session, svc):
    """E6: items 含非同 parent 节点 → NODE_REORDER_INVALID。"""
    user, proj = await _make_user_and_project(db_session)
    root1 = await svc.create_node(db_session, project_id=proj.id, actor_user_id=user.id, name="r1")
    root2 = await svc.create_node(db_session, project_id=proj.id, actor_user_id=user.id, name="r2")
    c1 = await svc.create_node(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        name="c1",
        parent_id=root1.id,
    )
    c2 = await svc.create_node(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        name="c2",
        parent_id=root2.id,
    )
    with pytest.raises(NodeReorderInvalidError):
        await svc.reorder_siblings(
            db_session,
            project_id=proj.id,
            actor_user_id=user.id,
            parent_id=root1.id,
            items=[(c1.id, 0), (c2.id, 1)],
        )


# ─────────────── M03-Svc-T5 move_subtree G5 ───────────────


async def test_svc_move_subtree_updates_path_and_depth(db_session, svc):
    user, proj = await _make_user_and_project(db_session)
    rootA = await svc.create_node(db_session, project_id=proj.id, actor_user_id=user.id, name="A")
    sub = await svc.create_node(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        name="sub",
        parent_id=rootA.id,
    )
    leaf = await svc.create_node(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        name="leaf",
        parent_id=sub.id,
    )
    rootB = await svc.create_node(db_session, project_id=proj.id, actor_user_id=user.id, name="B")

    moved = await svc.move_subtree(
        db_session,
        project_id=proj.id,
        node_id=sub.id,
        actor_user_id=user.id,
        new_parent_id=rootB.id,
    )

    assert moved.parent_id == rootB.id
    assert moved.path == f"{rootB.path}{sub.id}/"
    assert moved.depth == 1

    # leaf 子节点 path 同步重写
    await db_session.refresh(leaf)
    assert leaf.path.startswith(rootB.path)
    assert leaf.depth == 2


async def test_svc_move_to_descendant_raises_cycle(db_session, svc):
    """E8: move 到自己的子孙 → NODE_MOVE_CYCLE_DETECTED。"""
    user, proj = await _make_user_and_project(db_session)
    root = await svc.create_node(db_session, project_id=proj.id, actor_user_id=user.id, name="root")
    child = await svc.create_node(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        name="child",
        parent_id=root.id,
    )
    with pytest.raises(NodeMoveCycleDetectedError):
        await svc.move_subtree(
            db_session,
            project_id=proj.id,
            node_id=root.id,
            actor_user_id=user.id,
            new_parent_id=child.id,
        )


async def test_svc_move_to_same_parent_is_noop(db_session, svc):
    """E9: 移到当前同一父节点 → NOOP（path/depth 不变，不报错）。"""
    user, proj = await _make_user_and_project(db_session)
    root = await svc.create_node(db_session, project_id=proj.id, actor_user_id=user.id, name="root")
    child = await svc.create_node(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        name="child",
        parent_id=root.id,
    )
    old_path = child.path
    moved = await svc.move_subtree(
        db_session,
        project_id=proj.id,
        node_id=child.id,
        actor_user_id=user.id,
        new_parent_id=root.id,
    )
    assert moved.path == old_path


async def test_svc_move_to_root_level(db_session, svc):
    """G8: 移到根层级（new_parent_id=None）。"""
    user, proj = await _make_user_and_project(db_session)
    root = await svc.create_node(db_session, project_id=proj.id, actor_user_id=user.id, name="root")
    child = await svc.create_node(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        name="child",
        parent_id=root.id,
    )
    moved = await svc.move_subtree(
        db_session,
        project_id=proj.id,
        node_id=child.id,
        actor_user_id=user.id,
        new_parent_id=None,
    )
    assert moved.parent_id is None
    assert moved.depth == 0


# ─────────────── M03-Svc-T6 breadcrumb ───────────────


async def test_svc_breadcrumb_returns_chain_from_root(db_session, svc):
    user, proj = await _make_user_and_project(db_session)
    root = await svc.create_node(db_session, project_id=proj.id, actor_user_id=user.id, name="root")
    sub = await svc.create_node(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        name="sub",
        parent_id=root.id,
    )
    leaf = await svc.create_node(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        name="leaf",
        parent_id=sub.id,
    )
    crumbs = await svc.breadcrumb(db_session, leaf.id, proj.id)
    assert [c.id for c in crumbs] == [root.id, sub.id, leaf.id]


# ─────────────── M03-Svc-T7 batch_create_in_transaction (M11/M17 接口) ───────────────


async def test_svc_batch_create_topo_sorted(db_session, svc):
    user, proj = await _make_user_and_project(db_session)
    nodes = await svc.batch_create_in_transaction(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        nodes_data=[
            {"name": "root", "temp_id": "t1"},
            {"name": "child1", "temp_id": "t2", "parent_temp_id": "t1"},
            {"name": "grand", "temp_id": "t3", "parent_temp_id": "t2"},
        ],
    )
    assert len(nodes) == 3
    assert nodes[0].depth == 0
    assert nodes[1].parent_id == nodes[0].id
    assert nodes[2].parent_id == nodes[1].id
    assert nodes[2].depth == 2


async def test_svc_batch_create_unknown_parent_temp_id_raises(db_session, svc):
    user, proj = await _make_user_and_project(db_session)
    with pytest.raises(NodeParentNotFoundError):
        await svc.batch_create_in_transaction(
            db_session,
            project_id=proj.id,
            actor_user_id=user.id,
            nodes_data=[
                {"name": "x", "parent_temp_id": "nonexistent"},
            ],
        )


# ─────────────── M03-Svc-T8 get_node 错误路径 ───────────────


async def test_svc_get_node_not_found_raises(db_session, svc):
    user, proj = await _make_user_and_project(db_session)
    with pytest.raises(NodeNotFoundError):
        await svc.get_node(db_session, uuid4(), proj.id)


async def test_svc_get_node_cross_tenant_raises_not_found(db_session, svc):
    user, projA = await _make_user_and_project(db_session, name_suffix="-A")
    _, projB = await _make_user_and_project(db_session, name_suffix="-B")
    nA = await svc.create_node(db_session, project_id=projA.id, actor_user_id=user.id, name="A")
    with pytest.raises(NodeNotFoundError):
        await svc.get_node(db_session, nA.id, projB.id)
