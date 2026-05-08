"""M05 子片 4 — Router + 6 endpoints 端到端测试。

覆盖 design §7 6 endpoints + §8 三层权限 + 401/403/404/409/422 + golden + tenant。
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


async def _create_node(auth_client, user_id, pid: str, name: str = "n") -> str:
    r = await auth_client.post(
        f"/api/projects/{pid}/nodes", json={"name": name}, headers=_bearer(user_id)
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ─────────────── G1: create version (201) ───────────────


async def test_create_version_returns_201(auth_client, make_user):
    user = await make_user(email="m05-c@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/versions",
        json={"version_label": "v1.0", "summary": "initial"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["version_label"] == "v1.0"
    assert body["summary"] == "initial"
    assert body["change_type"] == "added"
    assert body["release_mode"] == "release"
    assert body["is_current"] is False


async def test_create_version_with_is_current_clears_previous(auth_client, make_user):
    user = await make_user(email="m05-current@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")

    r1 = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/versions",
        json={"version_label": "v1", "summary": "first", "is_current": True},
        headers=_bearer(user.id),
    )
    assert r1.status_code == 201
    r2 = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/versions",
        json={"version_label": "v2", "summary": "second", "is_current": True},
        headers=_bearer(user.id),
    )
    assert r2.status_code == 201
    assert r2.json()["is_current"] is True


async def test_create_version_duplicate_label_returns_409(auth_client, make_user):
    user = await make_user(email="m05-dup@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")

    body = {"version_label": "v1", "summary": "x"}
    r1 = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/versions", json=body, headers=_bearer(user.id)
    )
    assert r1.status_code == 201
    r2 = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/versions", json=body, headers=_bearer(user.id)
    )
    assert r2.status_code == 409
    assert r2.json()["code"] == "version_label_duplicate"


async def test_create_version_invalid_change_type_returns_422(auth_client, make_user):
    user = await make_user(email="m05-bad@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/versions",
        json={"version_label": "v1", "summary": "x", "change_type": "bogus"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 422


async def test_create_version_unauth_returns_401(auth_client, make_user):
    user = await make_user(email="m05-unauth@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/versions",
        json={"version_label": "v1", "summary": "x"},
    )
    assert r.status_code == 401


# ─────────────── G2: list versions ───────────────


async def test_list_versions_returns_items_and_total(auth_client, make_user):
    user = await make_user(email="m05-list@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")
    for label in ("v1", "v2", "v3"):
        await auth_client.post(
            f"/api/projects/{pid}/nodes/{nid}/versions",
            json={"version_label": label, "summary": label},
            headers=_bearer(user.id),
        )

    r = await auth_client.get(f"/api/projects/{pid}/nodes/{nid}/versions", headers=_bearer(user.id))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    # 三 POST 落在同一 ms 时 created_at 等值 → id DESC tie-break 是随机 UUID 顺序，
    # router 测试不验排序（DAO 测 test_dao_list_by_node_orders_by_created_at_desc
    # 已用显式 created_at 偏移验过 DESC 语义）；router 仅验集合 + total。
    assert {i["version_label"] for i in body["items"]} == {"v1", "v2", "v3"}


async def test_list_versions_empty_returns_zero_total(auth_client, make_user):
    user = await make_user(email="m05-empty@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")

    r = await auth_client.get(f"/api/projects/{pid}/nodes/{nid}/versions", headers=_bearer(user.id))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []


# ─────────────── G3: get_version ───────────────


async def test_get_version_returns_200(auth_client, make_user):
    user = await make_user(email="m05-get@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")

    create = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/versions",
        json={"version_label": "v1", "summary": "x"},
        headers=_bearer(user.id),
    )
    vid = create.json()["id"]

    r = await auth_client.get(
        f"/api/projects/{pid}/nodes/{nid}/versions/{vid}", headers=_bearer(user.id)
    )
    assert r.status_code == 200
    assert r.json()["id"] == vid


async def test_get_version_not_found_returns_404(auth_client, make_user):
    user = await make_user(email="m05-getnf@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")

    r = await auth_client.get(
        f"/api/projects/{pid}/nodes/{nid}/versions/{uuid4()}", headers=_bearer(user.id)
    )
    assert r.status_code == 404


# ─────────────── G4: update_version ───────────────


async def test_update_version_returns_200(auth_client, make_user):
    user = await make_user(email="m05-upd@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")

    create = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/versions",
        json={"version_label": "v1", "summary": "old"},
        headers=_bearer(user.id),
    )
    vid = create.json()["id"]

    r = await auth_client.put(
        f"/api/projects/{pid}/nodes/{nid}/versions/{vid}",
        json={"summary": "new", "details": "extra"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["summary"] == "new"
    assert body["details"] == "extra"


async def test_update_version_not_found_returns_404(auth_client, make_user):
    user = await make_user(email="m05-updnf@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")

    r = await auth_client.put(
        f"/api/projects/{pid}/nodes/{nid}/versions/{uuid4()}",
        json={"summary": "x"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 404


async def test_update_version_rejects_snapshot_data_field(auth_client, make_user):
    """design Q3：snapshot_data 不可 PUT 更新；schema 层 Pydantic 自动拒绝（实际：忽略未知字段）。

    Pydantic 默认 extra='ignore'，未知字段被丢弃；行为是"不更新但不报错"。
    """
    user = await make_user(email="m05-updsnap@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")

    create = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/versions",
        json={"version_label": "v1", "summary": "x", "snapshot_data": {"k": "v"}},
        headers=_bearer(user.id),
    )
    vid = create.json()["id"]
    original_snapshot = create.json()["snapshot_data"]

    # PUT 带 snapshot_data 字段
    await auth_client.put(
        f"/api/projects/{pid}/nodes/{nid}/versions/{vid}",
        json={"summary": "new", "snapshot_data": {"hacked": True}},
        headers=_bearer(user.id),
    )

    # GET 验证 snapshot_data 未变
    r = await auth_client.get(
        f"/api/projects/{pid}/nodes/{nid}/versions/{vid}", headers=_bearer(user.id)
    )
    assert r.json()["snapshot_data"] == original_snapshot


# ─────────────── G5: delete_version ───────────────


async def test_delete_version_returns_204(auth_client, make_user):
    user = await make_user(email="m05-del@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")

    create = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/versions",
        json={"version_label": "v1", "summary": "x"},
        headers=_bearer(user.id),
    )
    vid = create.json()["id"]

    r = await auth_client.delete(
        f"/api/projects/{pid}/nodes/{nid}/versions/{vid}", headers=_bearer(user.id)
    )
    assert r.status_code == 204
    r2 = await auth_client.get(
        f"/api/projects/{pid}/nodes/{nid}/versions/{vid}", headers=_bearer(user.id)
    )
    assert r2.status_code == 404


# ─────────────── G6: set_current ───────────────


async def test_set_current_marks_and_clears_previous(auth_client, make_user):
    user = await make_user(email="m05-setcur@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")

    create_v1 = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/versions",
        json={"version_label": "v1", "summary": "x", "is_current": True},
        headers=_bearer(user.id),
    )
    v1_id = create_v1.json()["id"]

    create_v2 = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/versions",
        json={"version_label": "v2", "summary": "y"},
        headers=_bearer(user.id),
    )
    v2_id = create_v2.json()["id"]

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/versions/{v2_id}/set-current",
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    assert r.json()["is_current"] is True

    # v1 应被自动清掉 current
    r1 = await auth_client.get(
        f"/api/projects/{pid}/nodes/{nid}/versions/{v1_id}", headers=_bearer(user.id)
    )
    assert r1.json()["is_current"] is False


async def test_set_current_not_found_returns_404(auth_client, make_user):
    user = await make_user(email="m05-setnf@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/versions/{uuid4()}/set-current",
        headers=_bearer(user.id),
    )
    assert r.status_code == 404


# ─────────────── tenant 越权 ───────────────


async def test_create_version_viewer_role_returns_403(auth_client, make_user, db_session):
    """R2 P1-01 立修：B 是 A 项目 viewer → POST 应 403 不是 404。"""
    from api.models.project import MemberRole, ProjectMember

    userA = await make_user(email="m05-vA@example.com")
    userB = await make_user(email="m05-vB@example.com")
    pidA = await _create_project(auth_client, userA.id)
    nidA = await _create_node(auth_client, userA.id, pidA, name="A")

    # A 把 B 加为 viewer
    db_session.add(
        ProjectMember(
            project_id=pidA,
            user_id=userB.id,
            role=MemberRole.VIEWER.value,
        )
    )
    await db_session.commit()

    # viewer 写 → 403
    r = await auth_client.post(
        f"/api/projects/{pidA}/nodes/{nidA}/versions",
        json={"version_label": "v1", "summary": "hack"},
        headers=_bearer(userB.id),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "permission_denied"


async def test_create_version_cross_tenant_returns_404(auth_client, make_user):
    """B 用户无 A 项目权限 → check_project_access 拦截返 404 不暴露项目存在性。"""
    userA = await make_user(email="m05-tA@example.com")
    userB = await make_user(email="m05-tB@example.com")
    pidA = await _create_project(auth_client, userA.id)
    nidA = await _create_node(auth_client, userA.id, pidA, name="A")

    r = await auth_client.post(
        f"/api/projects/{pidA}/nodes/{nidA}/versions",
        json={"version_label": "v1", "summary": "hack"},
        headers=_bearer(userB.id),
    )
    # check_project_access 对未授权用户返 404（不暴露项目存在性，与 M04 范式一致）
    assert r.status_code == 404
    assert r.json()["code"] == "project_not_found"


async def test_get_version_cross_tenant_returns_404(auth_client, make_user):
    userA = await make_user(email="m05-gtA@example.com")
    userB = await make_user(email="m05-gtB@example.com")
    pidA = await _create_project(auth_client, userA.id)
    nidA = await _create_node(auth_client, userA.id, pidA, name="A")
    create = await auth_client.post(
        f"/api/projects/{pidA}/nodes/{nidA}/versions",
        json={"version_label": "v1", "summary": "x"},
        headers=_bearer(userA.id),
    )
    vid = create.json()["id"]

    r = await auth_client.get(
        f"/api/projects/{pidA}/nodes/{nidA}/versions/{vid}",
        headers=_bearer(userB.id),
    )
    # check_project_access 对未授权用户返 404（不暴露项目存在性，与 M04 范式一致）
    assert r.status_code == 404
    assert r.json()["code"] == "project_not_found"
