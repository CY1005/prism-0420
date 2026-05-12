"""M03 子片 4 — Router + 8 endpoints + check_project_access Depends.

覆盖 design §7 8 endpoints + §8 权限三层（401/403/404/422 + happy）+
golden path (G1-G9) + 边界 (E1-E9) + tenant + 权限。
"""

from __future__ import annotations

from uuid import uuid4

from api.auth.jwt_utils import encode_jwt


def _bearer(user_id) -> dict:
    return {"Authorization": f"Bearer {encode_jwt(user_id, extra_claims={'type': 'access'})}"}


async def _create_project(auth_client, user_id, name: str = "P1") -> str:
    r = await auth_client.post("/api/projects", json={"name": name}, headers=_bearer(user_id))
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _create_node(
    auth_client, user_id, pid: str, name: str = "n", parent_id: str | None = None, **extra
) -> dict:
    body = {"name": name}
    if parent_id is not None:
        body["parent_id"] = parent_id
    body.update(extra)
    r = await auth_client.post(f"/api/projects/{pid}/nodes", json=body, headers=_bearer(user_id))
    assert r.status_code == 201, r.text
    return r.json()


async def _invite(auth_client, owner_id, pid: str, member_user_id, role: str) -> None:
    r = await auth_client.post(
        f"/api/projects/{pid}/members",
        json={"user_id": str(member_user_id), "role": role},
        headers=_bearer(owner_id),
    )
    assert r.status_code == 201, r.text


# ─────────────── G1-G2: create root + child ───────────────


async def test_create_root_node_returns_201(auth_client, make_user):
    user = await make_user(email="m03-root@example.com")
    pid = await _create_project(auth_client, user.id)

    body = await _create_node(auth_client, user.id, pid, name="功能A")
    assert body["name"] == "功能A"
    assert body["depth"] == 0
    assert body["parent_id"] is None
    assert body["sort_order"] == 0
    assert body["path"] == f"/{body['id']}/"
    assert body["type"] == "folder"


async def test_create_child_node_inherits_path(auth_client, make_user):
    user = await make_user(email="m03-child@example.com")
    pid = await _create_project(auth_client, user.id)
    root = await _create_node(auth_client, user.id, pid, name="root")
    child = await _create_node(auth_client, user.id, pid, name="子A1", parent_id=root["id"])
    assert child["depth"] == 1
    assert child["path"] == f"{root['path']}{child['id']}/"


# ─────────────── G3: list_tree ───────────────


async def test_list_tree_returns_nested_structure(auth_client, make_user):
    user = await make_user(email="m03-tree@example.com")
    pid = await _create_project(auth_client, user.id)
    root = await _create_node(auth_client, user.id, pid, name="root")
    await _create_node(auth_client, user.id, pid, name="c1", parent_id=root["id"])

    r = await auth_client.get(f"/api/projects/{pid}/nodes", headers=_bearer(user.id))
    assert r.status_code == 200
    body = r.json()
    assert "roots" in body
    assert len(body["roots"]) == 1
    assert body["roots"][0]["name"] == "root"
    assert len(body["roots"][0]["children"]) == 1
    assert body["roots"][0]["children"][0]["name"] == "c1"


# ─────────────── G4: update name ───────────────


async def test_update_node_name(auth_client, make_user):
    user = await make_user(email="m03-upd@example.com")
    pid = await _create_project(auth_client, user.id)
    n = await _create_node(auth_client, user.id, pid, name="old")
    r = await auth_client.put(
        f"/api/projects/{pid}/nodes/{n['id']}",
        json={"name": "new"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    assert r.json()["name"] == "new"


# ─────────────── G5: reorder ───────────────


async def test_reorder_siblings_returns_list(auth_client, make_user):
    """R2-1 修后: response NodeListResponse (design §7 字面)."""
    user = await make_user(email="m03-reord@example.com")
    pid = await _create_project(auth_client, user.id)
    a = await _create_node(auth_client, user.id, pid, name="a")
    b = await _create_node(auth_client, user.id, pid, name="b")
    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/reorder",
        json={
            "parent_id": None,
            "items": [{"node_id": a["id"], "sort_order": 5}, {"node_id": b["id"], "sort_order": 0}],
        },
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    body = r.json()
    assert "items" in body, f"R2-1 修: 应返回 NodeListResponse 而非 NodeTreeResponse, got={body}"
    by_name = {n["name"]: n for n in body["items"]}
    assert by_name["a"]["sort_order"] == 5
    assert by_name["b"]["sort_order"] == 0


# ─────────────── G6: delete leaf ───────────────


async def test_delete_leaf_returns_204(auth_client, make_user):
    user = await make_user(email="m03-del@example.com")
    pid = await _create_project(auth_client, user.id)
    n = await _create_node(auth_client, user.id, pid, name="del-me")
    r = await auth_client.delete(f"/api/projects/{pid}/nodes/{n['id']}", headers=_bearer(user.id))
    assert r.status_code == 204


# ─────────────── G7: breadcrumb ───────────────


async def test_breadcrumb_returns_chain(auth_client, make_user):
    user = await make_user(email="m03-crumb@example.com")
    pid = await _create_project(auth_client, user.id)
    root = await _create_node(auth_client, user.id, pid, name="r")
    sub = await _create_node(auth_client, user.id, pid, name="s", parent_id=root["id"])
    leaf = await _create_node(auth_client, user.id, pid, name="l", parent_id=sub["id"])
    r = await auth_client.get(
        f"/api/projects/{pid}/nodes/{leaf['id']}/breadcrumb", headers=_bearer(user.id)
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert [it["name"] for it in items] == ["r", "s", "l"]
    assert [it["depth"] for it in items] == [0, 1, 2]


# ─────────────── G8: move subtree ───────────────


async def test_move_subtree_updates_path(auth_client, make_user):
    user = await make_user(email="m03-move@example.com")
    pid = await _create_project(auth_client, user.id)
    rA = await _create_node(auth_client, user.id, pid, name="A")
    sub = await _create_node(auth_client, user.id, pid, name="sub", parent_id=rA["id"])
    rB = await _create_node(auth_client, user.id, pid, name="B")

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{sub['id']}/move",
        json={"new_parent_id": rB["id"]},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["parent_id"] == rB["id"]
    assert body["path"].startswith(rB["path"])


# ─────────────── G9: delete with subtree (CASCADE) ───────────────


async def test_delete_subtree_cascades(auth_client, make_user):
    user = await make_user(email="m03-cascade@example.com")
    pid = await _create_project(auth_client, user.id)
    root = await _create_node(auth_client, user.id, pid, name="r")
    await _create_node(auth_client, user.id, pid, name="c1", parent_id=root["id"])
    await _create_node(auth_client, user.id, pid, name="c2", parent_id=root["id"])

    r = await auth_client.delete(
        f"/api/projects/{pid}/nodes/{root['id']}", headers=_bearer(user.id)
    )
    assert r.status_code == 204
    # 树空
    tr = await auth_client.get(f"/api/projects/{pid}/nodes", headers=_bearer(user.id))
    assert tr.json()["roots"] == []


# ─────────────── 边界 E1: 名空 (Pydantic min_length) ───────────────


async def test_create_empty_name_returns_422(auth_client, make_user):
    user = await make_user(email="m03-empty@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.post(
        f"/api/projects/{pid}/nodes", json={"name": ""}, headers=_bearer(user.id)
    )
    assert r.status_code == 422


# ─────────────── 边界 E3: parent_id 不存在 ───────────────


async def test_create_with_unknown_parent_returns_404(auth_client, make_user):
    user = await make_user(email="m03-noparent@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.post(
        f"/api/projects/{pid}/nodes",
        json={"name": "x", "parent_id": str(uuid4())},
        headers=_bearer(user.id),
    )
    assert r.status_code == 404
    assert r.json()["code"] == "node_parent_not_found"


# ─────────────── 边界 E5: type immutable (B-P2-M03-node-type-immutable-not-enforced fix) ───────────────
# NodeUpdate schema 现在显式声明 type 字段，service 层捕获变更抛 NODE_TYPE_IMMUTABLE 422。
# 原方案：schema 排除法 → Pydantic 静默忽略 → 返 200，design §4 NODE_TYPE_IMMUTABLE 未实装。


async def test_update_node_type_returns_422_node_type_immutable(auth_client, make_user):
    """PUT 改 type 返 422 NODE_TYPE_IMMUTABLE (B-P2-M03 fix / design §4 字面)。"""
    user = await make_user(email="m03-typeimm@example.com")
    pid = await _create_project(auth_client, user.id)
    node = await _create_node(auth_client, user.id, pid, name="root", type="folder")
    r = await auth_client.put(
        f"/api/projects/{pid}/nodes/{node['id']}",
        json={"name": "root", "type": "file"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 422
    assert r.json()["code"] == "node_type_immutable"


async def test_update_node_same_type_succeeds(auth_client, make_user):
    """PUT 传相同 type 视为 no-op (无变更不触发 NODE_TYPE_IMMUTABLE / 服务对齐)。"""
    user = await make_user(email="m03-typesame@example.com")
    pid = await _create_project(auth_client, user.id)
    node = await _create_node(auth_client, user.id, pid, name="root", type="folder")
    r = await auth_client.put(
        f"/api/projects/{pid}/nodes/{node['id']}",
        json={"name": "renamed", "type": "folder"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "folder"
    assert body["name"] == "renamed"


# ─────────────── 边界 E6: reorder 跨 parent ───────────────


async def test_reorder_with_cross_parent_returns_422(auth_client, make_user):
    user = await make_user(email="m03-reord-bad@example.com")
    pid = await _create_project(auth_client, user.id)
    rA = await _create_node(auth_client, user.id, pid, name="A")
    rB = await _create_node(auth_client, user.id, pid, name="B")
    cA = await _create_node(auth_client, user.id, pid, name="cA", parent_id=rA["id"])
    cB = await _create_node(auth_client, user.id, pid, name="cB", parent_id=rB["id"])
    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/reorder",
        json={
            "parent_id": rA["id"],
            "items": [
                {"node_id": cA["id"], "sort_order": 0},
                {"node_id": cB["id"], "sort_order": 1},
            ],
        },
        headers=_bearer(user.id),
    )
    assert r.status_code == 422
    assert r.json()["code"] == "node_reorder_invalid"


# ─────────────── 边界 E8: move cycle ───────────────


async def test_move_to_descendant_returns_422(auth_client, make_user):
    user = await make_user(email="m03-cycle@example.com")
    pid = await _create_project(auth_client, user.id)
    root = await _create_node(auth_client, user.id, pid, name="root")
    child = await _create_node(auth_client, user.id, pid, name="c", parent_id=root["id"])
    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{root['id']}/move",
        json={"new_parent_id": child["id"]},
        headers=_bearer(user.id),
    )
    assert r.status_code == 422
    assert r.json()["code"] == "node_move_cycle_detected"


# ─────────────── Tenant T1: 非成员读取 ───────────────


async def test_non_member_list_tree_returns_404(auth_client, make_user):
    """非 member 返回 404 (防 enumeration, 与 M02 R1 P2-A 一致)."""
    owner = await make_user(email="m03-own@example.com")
    other = await make_user(email="m03-stranger@example.com")
    pid = await _create_project(auth_client, owner.id)
    r = await auth_client.get(f"/api/projects/{pid}/nodes", headers=_bearer(other.id))
    assert r.status_code == 404
    assert r.json()["code"] == "project_not_found"


# ─────────────── Tenant T2: 跨项目越权写 ───────────────


async def test_cross_project_create_returns_404(auth_client, make_user):
    ownerA = await make_user(email="m03-ownA@example.com")
    ownerB = await make_user(email="m03-ownB@example.com")
    pidA = await _create_project(auth_client, ownerA.id, name="PA")
    await _create_project(auth_client, ownerB.id, name="PB")
    # ownerB 试图在 pidA 下建节点
    r = await auth_client.post(
        f"/api/projects/{pidA}/nodes",
        json={"name": "ownerB-trespass"},
        headers=_bearer(ownerB.id),
    )
    assert r.status_code == 404


# ─────────────── 权限 P1: 未登录 ───────────────


async def test_unauthenticated_returns_401(auth_client):
    r = await auth_client.get(f"/api/projects/{uuid4()}/nodes")
    assert r.status_code == 401


# ─────────────── 权限 P2: viewer 不能写 ───────────────


async def test_viewer_create_returns_403(auth_client, make_user):
    owner = await make_user(email="m03-pown@example.com")
    viewer = await make_user(email="m03-pview@example.com")
    pid = await _create_project(auth_client, owner.id)
    await _invite(auth_client, owner.id, pid, viewer.id, "viewer")
    r = await auth_client.post(
        f"/api/projects/{pid}/nodes",
        json={"name": "viewer-cant"},
        headers=_bearer(viewer.id),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "permission_denied"


async def test_viewer_can_read(auth_client, make_user):
    owner = await make_user(email="m03-rdown@example.com")
    viewer = await make_user(email="m03-rdview@example.com")
    pid = await _create_project(auth_client, owner.id)
    await _create_node(auth_client, owner.id, pid, name="readable")
    await _invite(auth_client, owner.id, pid, viewer.id, "viewer")
    r = await auth_client.get(f"/api/projects/{pid}/nodes", headers=_bearer(viewer.id))
    assert r.status_code == 200
    assert len(r.json()["roots"]) == 1


# ─────────────── 错误 ER1: 删除不存在节点 ───────────────


async def test_delete_unknown_node_returns_404(auth_client, make_user):
    user = await make_user(email="m03-delna@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.delete(f"/api/projects/{pid}/nodes/{uuid4()}", headers=_bearer(user.id))
    assert r.status_code == 404
    assert r.json()["code"] == "node_not_found"


async def test_get_unknown_node_returns_404(auth_client, make_user):
    user = await make_user(email="m03-getna@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.get(f"/api/projects/{pid}/nodes/{uuid4()}", headers=_bearer(user.id))
    assert r.status_code == 404
    assert r.json()["code"] == "node_not_found"
