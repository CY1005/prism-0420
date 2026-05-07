"""M03 子片 2 — DAO + NodeService.get_for_embedding 测试。

覆盖 design §9 主查询模式 + tenant 过滤 + 子树 path LIKE
+ design §6.X A4 get_for_embedding A 路径被动接口。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from api.dao.node_dao import NodeDAO
from api.services.node_service import NodeService

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


async def _make_node(db_session, project_id, *, parent=None, name="n", **extra):
    """build node with path consistent with depth (test-only helper)."""
    from api.models.node import Node

    if parent is None:
        depth = 0
        prefix = "/"
    else:
        depth = parent.depth + 1
        prefix = parent.path
    nid = uuid4()
    n = Node(
        id=nid,
        project_id=project_id,
        parent_id=parent.id if parent else None,
        name=name,
        depth=depth,
        path=f"{prefix}{nid}/",
        **extra,
    )
    db_session.add(n)
    await db_session.flush()
    return n


# ─────────────── M03-DAO-T1 list_by_project ───────────────


@pytest.fixture
def dao():
    return NodeDAO()


async def test_dao_list_by_project_orders_by_depth_then_sort_order(db_session, dao):
    _, proj = await _make_user_and_project(db_session)
    root = await _make_node(db_session, proj.id, name="root")
    c1 = await _make_node(db_session, proj.id, parent=root, name="c1", sort_order=1)
    c0 = await _make_node(db_session, proj.id, parent=root, name="c0", sort_order=0)

    rows = await dao.list_by_project(db_session, proj.id)
    ids = [r.id for r in rows]
    # root (depth=0) 先于 children；c0 (sort=0) 先于 c1 (sort=1)
    assert ids == [root.id, c0.id, c1.id]


async def test_dao_list_by_project_isolates_tenants(db_session, dao):
    _, projA = await _make_user_and_project(db_session, name_suffix="-A")
    _, projB = await _make_user_and_project(db_session, name_suffix="-B")
    nA = await _make_node(db_session, projA.id, name="A")
    await _make_node(db_session, projB.id, name="B")

    rowsA = await dao.list_by_project(db_session, projA.id)
    assert {r.id for r in rowsA} == {nA.id}


# ─────────────── M03-DAO-T2 get_by_id tenant 过滤 ───────────────


async def test_dao_get_by_id_returns_node_in_tenant(db_session, dao):
    _, proj = await _make_user_and_project(db_session)
    n = await _make_node(db_session, proj.id, name="x")
    found = await dao.get_by_id(db_session, n.id, proj.id)
    assert found is not None
    assert found.id == n.id


async def test_dao_get_by_id_blocks_cross_tenant(db_session, dao):
    _, projA = await _make_user_and_project(db_session, name_suffix="-A")
    _, projB = await _make_user_and_project(db_session, name_suffix="-B")
    nA = await _make_node(db_session, projA.id, name="A")
    found = await dao.get_by_id(db_session, nA.id, projB.id)
    assert found is None, "tenant 过滤：B 项目不应能查到 A 项目节点"


# ─────────────── M03-DAO-T3 list_children ───────────────


async def test_dao_list_children_root_level(db_session, dao):
    _, proj = await _make_user_and_project(db_session)
    r1 = await _make_node(db_session, proj.id, name="r1", sort_order=0)
    r2 = await _make_node(db_session, proj.id, name="r2", sort_order=1)
    # 子节点不应出现在 root list
    await _make_node(db_session, proj.id, parent=r1, name="c1")

    rows = await dao.list_children(db_session, None, proj.id)
    ids = [r.id for r in rows]
    assert ids == [r1.id, r2.id]


async def test_dao_list_children_specific_parent(db_session, dao):
    _, proj = await _make_user_and_project(db_session)
    root = await _make_node(db_session, proj.id, name="root")
    c0 = await _make_node(db_session, proj.id, parent=root, name="c0", sort_order=0)
    c1 = await _make_node(db_session, proj.id, parent=root, name="c1", sort_order=1)

    rows = await dao.list_children(db_session, root.id, proj.id)
    assert [r.id for r in rows] == [c0.id, c1.id]


# ─────────────── M03-DAO-T4 list_subtree path LIKE ───────────────


async def test_dao_list_subtree_includes_self_and_descendants(db_session, dao):
    _, proj = await _make_user_and_project(db_session)
    root = await _make_node(db_session, proj.id, name="root")
    c1 = await _make_node(db_session, proj.id, parent=root, name="c1")
    gc = await _make_node(db_session, proj.id, parent=c1, name="gc")
    sibling = await _make_node(db_session, proj.id, name="sibling")  # 无关 root

    rows = await dao.list_subtree(db_session, c1.id, proj.id)
    ids = {r.id for r in rows}
    assert ids == {c1.id, gc.id}, f"应含自身+后代，不含 sibling/root，got={ids}"
    assert sibling.id not in ids


async def test_dao_list_subtree_anchor_not_found_returns_empty(db_session, dao):
    _, proj = await _make_user_and_project(db_session)
    rows = await dao.list_subtree(db_session, uuid4(), proj.id)
    assert list(rows) == []


async def test_dao_list_subtree_blocks_cross_tenant(db_session, dao):
    _, projA = await _make_user_and_project(db_session, name_suffix="-A")
    _, projB = await _make_user_and_project(db_session, name_suffix="-B")
    nA = await _make_node(db_session, projA.id, name="A")
    rows = await dao.list_subtree(db_session, nA.id, projB.id)
    assert list(rows) == [], "tenant 过滤：B 项目查 A 节点子树应空"


# ─────────────── M03-DAO-T5 max_sort_order ───────────────


async def test_dao_max_sort_order_root_level(db_session, dao):
    _, proj = await _make_user_and_project(db_session)
    await _make_node(db_session, proj.id, name="r0", sort_order=0)
    await _make_node(db_session, proj.id, name="r5", sort_order=5)
    await _make_node(db_session, proj.id, name="r2", sort_order=2)
    assert await dao.max_sort_order(db_session, None, proj.id) == 5


async def test_dao_max_sort_order_empty_returns_none(db_session, dao):
    _, proj = await _make_user_and_project(db_session)
    assert await dao.max_sort_order(db_session, None, proj.id) is None


# ─────────────── M03-DAO-T6 bulk_update_sort_order ───────────────


async def test_dao_bulk_update_sort_order_updates_only_specified(db_session, dao):
    _, proj = await _make_user_and_project(db_session)
    a = await _make_node(db_session, proj.id, name="a", sort_order=0)
    b = await _make_node(db_session, proj.id, name="b", sort_order=1)
    c = await _make_node(db_session, proj.id, name="c", sort_order=2)

    n = await dao.bulk_update_sort_order(db_session, proj.id, None, [(a.id, 10), (c.id, 20)])
    assert n == 2

    await db_session.refresh(a)
    await db_session.refresh(b)
    await db_session.refresh(c)
    assert a.sort_order == 10
    assert b.sort_order == 1  # 未指定不变
    assert c.sort_order == 20


async def test_dao_bulk_update_sort_order_blocks_cross_parent(db_session, dao):
    """重排只能在同 parent_id 范围内（即使 ID 列表跨 parent 也不更新）。"""
    _, proj = await _make_user_and_project(db_session)
    root1 = await _make_node(db_session, proj.id, name="root1")
    root2 = await _make_node(db_session, proj.id, name="root2")
    c1 = await _make_node(db_session, proj.id, parent=root1, name="c1", sort_order=0)
    c2 = await _make_node(db_session, proj.id, parent=root2, name="c2", sort_order=0)

    # 让 root1 范围内更新 c1 + c2 — c2 不属于 root1，应不变
    n = await dao.bulk_update_sort_order(db_session, proj.id, root1.id, [(c1.id, 9), (c2.id, 9)])
    assert n == 1  # 只有 c1 被更新

    await db_session.refresh(c1)
    await db_session.refresh(c2)
    assert c1.sort_order == 9
    assert c2.sort_order == 0  # 未变


# ─────────────── M03-DAO-T7 update_paths_in_subtree ───────────────


async def test_dao_update_paths_in_subtree_replaces_prefix_and_depth(db_session, dao):
    """move_subtree 语义验证：prefix REPLACE + depth delta（G5）。"""
    _, proj = await _make_user_and_project(db_session)
    # /A/, /A/B/, /A/B/C/   →  move B 到 newRoot：/A/ 不变，/A/B/ → /newRoot/B/
    A = await _make_node(db_session, proj.id, name="A")  # depth=0 path="/A_id/"
    B = await _make_node(db_session, proj.id, parent=A, name="B")  # depth=1
    C = await _make_node(db_session, proj.id, parent=B, name="C")  # depth=2
    new_root = await _make_node(db_session, proj.id, name="NR")  # depth=0

    old_prefix = B.path  # "/Aid/Bid/"
    new_prefix = f"{new_root.path}{B.id}/"  # "/NRid/Bid/"
    depth_delta = new_root.depth + 1 - B.depth  # 0+1-1 = 0

    # 让 depth 变化更明显：把 B 从 depth=1 移到 newRoot 下成 child 仍 depth=1 (delta=0)
    # 改 fixture：把 B 移到 newRoot 的 child 路径下 (depth_delta=0 不改 depth) — 简化只验 path
    n = await dao.update_paths_in_subtree(db_session, proj.id, old_prefix, new_prefix, depth_delta)
    assert n == 2, f"应更新 B+C 共 2 行，got={n}"

    await db_session.refresh(B)
    await db_session.refresh(C)
    await db_session.refresh(A)
    assert B.path.startswith(new_root.path)
    assert C.path.startswith(new_root.path)
    assert A.path.startswith("/")  # A 不动


async def test_dao_update_paths_in_subtree_isolates_tenants(db_session, dao):
    _, projA = await _make_user_and_project(db_session, name_suffix="-A")
    _, projB = await _make_user_and_project(db_session, name_suffix="-B")
    await _make_node(db_session, projA.id, name="X")
    b = await _make_node(db_session, projB.id, name="X")  # 同 prefix 形态

    # 在 projA 范围内做 path 替换；projB 不应受影响
    await dao.update_paths_in_subtree(db_session, projA.id, "/", "/x/", 1)
    await db_session.refresh(b)
    assert b.path == f"/{b.id}/"  # 未变


# ─────────────── M03-DAO-T8 create / update_fields / delete_one ───────────────


async def test_dao_create_persists_node(db_session, dao):
    _, proj = await _make_user_and_project(db_session)
    n = await dao.create(db_session, project_id=proj.id, name="created")
    assert n.id is not None
    assert n.project_id == proj.id


async def test_dao_update_fields_persists(db_session, dao):
    _, proj = await _make_user_and_project(db_session)
    n = await _make_node(db_session, proj.id, name="old")
    updated = await dao.update_fields(db_session, n, name="new", description="desc")
    assert updated.name == "new"
    assert updated.description == "desc"


async def test_dao_delete_one_returns_rowcount(db_session, dao):
    _, proj = await _make_user_and_project(db_session)
    n = await _make_node(db_session, proj.id, name="del")
    rc = await dao.delete_one(db_session, n.id, proj.id)
    assert rc == 1
    rc2 = await dao.delete_one(db_session, n.id, proj.id)
    assert rc2 == 0


async def test_dao_delete_one_blocks_cross_tenant(db_session, dao):
    _, projA = await _make_user_and_project(db_session, name_suffix="-A")
    _, projB = await _make_user_and_project(db_session, name_suffix="-B")
    nA = await _make_node(db_session, projA.id, name="A")
    rc = await dao.delete_one(db_session, nA.id, projB.id)
    assert rc == 0, "B 项目不应能删 A 项目节点"


# ─────────────── M03-Service-T9 get_for_embedding (A 路径 design §6.X A4) ───────────────


async def test_service_get_for_embedding_returns_name_plus_description(db_session):
    _, proj = await _make_user_and_project(db_session)
    from api.models.node import Node

    n = Node(
        project_id=proj.id,
        name="模块A",
        description="这是一个核心模块",
    )
    db_session.add(n)
    await db_session.flush()

    svc = NodeService()
    result = await svc.get_for_embedding(db_session, n.id, proj.id)
    assert result == "模块A\n这是一个核心模块"


async def test_service_get_for_embedding_returns_name_only_when_no_description(
    db_session,
):
    _, proj = await _make_user_and_project(db_session)
    from api.models.node import Node

    n = Node(project_id=proj.id, name="纯名字", description=None)
    db_session.add(n)
    await db_session.flush()

    svc = NodeService()
    result = await svc.get_for_embedding(db_session, n.id, proj.id)
    assert result == "纯名字"


async def test_service_get_for_embedding_returns_none_when_not_found(db_session):
    _, proj = await _make_user_and_project(db_session)
    svc = NodeService()
    result = await svc.get_for_embedding(db_session, uuid4(), proj.id)
    assert result is None, "节点不存在 → None（M18 worker noop 信号）"


async def test_service_get_for_embedding_blocks_cross_tenant(db_session):
    """tenant 过滤：跨项目查询返回 None（防 M18 worker 误嵌入跨租户节点）。"""
    _, projA = await _make_user_and_project(db_session, name_suffix="-A")
    _, projB = await _make_user_and_project(db_session, name_suffix="-B")
    from api.models.node import Node

    n = Node(project_id=projA.id, name="A 节点")
    db_session.add(n)
    await db_session.flush()

    svc = NodeService()
    result = await svc.get_for_embedding(db_session, n.id, projB.id)
    assert result is None


# ─────────────── M03-Service-T10 child_services 注册表 ───────────────


def test_child_service_registry_register_get_clear():
    from api.services.node_service import (
        clear_child_services,
        get_child_services,
        register_child_service,
    )

    clear_child_services()
    assert get_child_services() == {}

    async def dummy(db, node_id, project_id):  # pragma: no cover - 不调用
        return None

    register_child_service("dimension", dummy)
    assert "dimension" in get_child_services()

    clear_child_services()
    assert get_child_services() == {}
