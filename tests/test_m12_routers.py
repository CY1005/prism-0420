"""M12 子片 4 — Router 6 endpoints + 端到端测试。

覆盖 design §7 6 endpoints + §8 三层权限 + 401/403/404/422/409 + golden + tenant +
viewer 写 3 端点全 403（M07 立 / M08+M11 应用 / M12 主动复制）+ cross-project node 422 +
G4=B 值快照独立。
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


async def _enable_dim_type(auth_client, db_session, user_id, pid: str, key: str = "k") -> int:
    """Helper：建 dim_type + project_dimension_config(enabled=True)，使 dimension API 可写。"""
    from api.models.project import DimensionType, ProjectDimensionConfig

    dt = DimensionType(key=key, name=key)
    db_session.add(dt)
    await db_session.flush()
    db_session.add(
        ProjectDimensionConfig(project_id=pid, dimension_type_id=dt.id, enabled=True, sort_order=0)
    )
    await db_session.commit()
    return dt.id


async def _seed_dim_record(
    auth_client, db_session, user_id, pid: str, node_id: str, type_id: int, content: dict
):
    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{node_id}/dimensions",
        json={"dimension_type_id": type_id, "content": content},
        headers=_bearer(user_id),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _create_snapshot(auth_client, user_id, pid, node_ids, type_ids, name="S1"):
    r = await auth_client.post(
        f"/api/projects/{pid}/comparison/snapshots",
        json={
            "name": name,
            "description": None,
            "node_ids": node_ids,
            "dimension_type_ids": type_ids,
        },
        headers=_bearer(user_id),
    )
    assert r.status_code == 201, r.text
    return r.json()


# ─────────────── G1 matrix golden + 边界 ───────────────


async def test_matrix_golden(auth_client, make_user, db_session):
    user = await make_user(email="m12-mat@example.com")
    pid = await _create_project(auth_client, user.id)
    nA = await _create_node(auth_client, user.id, pid, name="A")
    nB = await _create_node(auth_client, user.id, pid, name="B")
    t1 = await _enable_dim_type(auth_client, db_session, user.id, pid, key="m12r-mat-1")
    t2 = await _enable_dim_type(auth_client, db_session, user.id, pid, key="m12r-mat-2")
    await _seed_dim_record(auth_client, db_session, user.id, pid, nA, t1, {"v": "a1"})
    await _seed_dim_record(auth_client, db_session, user.id, pid, nA, t2, {"v": "a2"})
    await _seed_dim_record(auth_client, db_session, user.id, pid, nB, t1, {"v": "b1"})

    r = await auth_client.get(
        f"/api/projects/{pid}/comparison/matrix",
        params=[
            ("node_ids", nA),
            ("node_ids", nB),
            ("dimension_type_ids", t1),
            ("dimension_type_ids", t2),
        ],
        headers=_bearer(user.id),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["cells"]) == 3


async def test_matrix_empty_node_ids_422(auth_client, make_user):
    user = await make_user(email="m12-mat-empty@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.get(
        f"/api/projects/{pid}/comparison/matrix",
        params=[("dimension_type_ids", 1)],
        headers=_bearer(user.id),
    )
    # FastAPI Query(min_length=1) → 422 fastapi 默认 validation error
    assert r.status_code == 422


async def test_matrix_cross_project_node_422(auth_client, make_user, db_session):
    """node_id 跨 project → ComparisonNodeNotFoundError 422（M06+M07+M08 范式）。"""
    user = await make_user(email="m12-mat-cross@example.com")
    pidA = await _create_project(auth_client, user.id, name="A")
    pidB = await _create_project(auth_client, user.id, name="B")
    nA = await _create_node(auth_client, user.id, pidA, name="A")
    t1 = await _enable_dim_type(auth_client, db_session, user.id, pidB, key="m12r-cross")
    r = await auth_client.get(
        f"/api/projects/{pidB}/comparison/matrix",
        params=[("node_ids", nA), ("dimension_type_ids", t1)],
        headers=_bearer(user.id),
    )
    assert r.status_code == 422
    assert r.json()["code"] == "comparison_node_not_found"


# ─────────────── G2 snapshots CRUD ───────────────


async def test_create_snapshot_201(auth_client, make_user, db_session):
    user = await make_user(email="m12-create@example.com")
    pid = await _create_project(auth_client, user.id)
    n = await _create_node(auth_client, user.id, pid)
    t = await _enable_dim_type(auth_client, db_session, user.id, pid, key="m12r-c1")
    await _seed_dim_record(auth_client, db_session, user.id, pid, n, t, {"v": "x"})
    body = await _create_snapshot(auth_client, user.id, pid, [n], [t], name="S1")
    assert body["name"] == "S1"
    assert body["version"] == 1
    assert body["nodes_ref"] == [n]
    assert body["dimensions_ref"] == [t]


async def test_create_snapshot_name_empty_422(auth_client, make_user, db_session):
    user = await make_user(email="m12-name-empty@example.com")
    pid = await _create_project(auth_client, user.id)
    n = await _create_node(auth_client, user.id, pid)
    t = await _enable_dim_type(auth_client, db_session, user.id, pid, key="m12r-name-empty")
    r = await auth_client.post(
        f"/api/projects/{pid}/comparison/snapshots",
        json={
            "name": "",
            "description": None,
            "node_ids": [n],
            "dimension_type_ids": [t],
        },
        headers=_bearer(user.id),
    )
    # name="" 触发 pydantic min_length=1 → 422
    assert r.status_code == 422


async def test_create_snapshot_empty_selection_422(auth_client, make_user):
    user = await make_user(email="m12-empty-sel@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.post(
        f"/api/projects/{pid}/comparison/snapshots",
        json={"name": "x", "description": None, "node_ids": [], "dimension_type_ids": [1]},
        headers=_bearer(user.id),
    )
    assert r.status_code == 422  # pydantic min_length=1


async def test_list_snapshots_returns_total(auth_client, make_user, db_session):
    user = await make_user(email="m12-list@example.com")
    pid = await _create_project(auth_client, user.id)
    n = await _create_node(auth_client, user.id, pid)
    t = await _enable_dim_type(auth_client, db_session, user.id, pid, key="m12r-list")
    await _seed_dim_record(auth_client, db_session, user.id, pid, n, t, {"v": "x"})
    await _create_snapshot(auth_client, user.id, pid, [n], [t], name="S1")
    await _create_snapshot(auth_client, user.id, pid, [n], [t], name="S2")
    r = await auth_client.get(f"/api/projects/{pid}/comparison/snapshots", headers=_bearer(user.id))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert {it["name"] for it in body["items"]} == {"S1", "S2"}


async def test_get_snapshot_detail_includes_items(auth_client, make_user, db_session):
    user = await make_user(email="m12-detail@example.com")
    pid = await _create_project(auth_client, user.id)
    n = await _create_node(auth_client, user.id, pid)
    t = await _enable_dim_type(auth_client, db_session, user.id, pid, key="m12r-detail")
    await _seed_dim_record(auth_client, db_session, user.id, pid, n, t, {"v": "snapped"})
    snap = await _create_snapshot(auth_client, user.id, pid, [n], [t], name="S")
    r = await auth_client.get(
        f"/api/projects/{pid}/comparison/snapshots/{snap['id']}", headers=_bearer(user.id)
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["content"] == {"v": "snapped"}


async def test_get_snapshot_404(auth_client, make_user):
    user = await make_user(email="m12-getnf@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.get(
        f"/api/projects/{pid}/comparison/snapshots/{uuid4()}", headers=_bearer(user.id)
    )
    assert r.status_code == 404
    assert r.json()["code"] == "comparison_snapshot_not_found"


async def test_rename_snapshot_increments_version(auth_client, make_user, db_session):
    user = await make_user(email="m12-rename@example.com")
    pid = await _create_project(auth_client, user.id)
    n = await _create_node(auth_client, user.id, pid)
    t = await _enable_dim_type(auth_client, db_session, user.id, pid, key="m12r-rename")
    await _seed_dim_record(auth_client, db_session, user.id, pid, n, t, {"v": "x"})
    snap = await _create_snapshot(auth_client, user.id, pid, [n], [t], name="old")
    r = await auth_client.put(
        f"/api/projects/{pid}/comparison/snapshots/{snap['id']}",
        json={"name": "new", "description": "d", "expected_version": 1},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "new"
    assert body["version"] == 2


async def test_rename_snapshot_conflict_409(auth_client, make_user, db_session):
    user = await make_user(email="m12-rename-conflict@example.com")
    pid = await _create_project(auth_client, user.id)
    n = await _create_node(auth_client, user.id, pid)
    t = await _enable_dim_type(auth_client, db_session, user.id, pid, key="m12r-conflict")
    await _seed_dim_record(auth_client, db_session, user.id, pid, n, t, {"v": "x"})
    snap = await _create_snapshot(auth_client, user.id, pid, [n], [t], name="old")
    r = await auth_client.put(
        f"/api/projects/{pid}/comparison/snapshots/{snap['id']}",
        json={"name": "x", "description": None, "expected_version": 99},
        headers=_bearer(user.id),
    )
    assert r.status_code == 409
    assert r.json()["code"] == "comparison_snapshot_conflict"


async def test_delete_snapshot_204(auth_client, make_user, db_session):
    user = await make_user(email="m12-del@example.com")
    pid = await _create_project(auth_client, user.id)
    n = await _create_node(auth_client, user.id, pid)
    t = await _enable_dim_type(auth_client, db_session, user.id, pid, key="m12r-del")
    await _seed_dim_record(auth_client, db_session, user.id, pid, n, t, {"v": "x"})
    snap = await _create_snapshot(auth_client, user.id, pid, [n], [t], name="x")
    r = await auth_client.delete(
        f"/api/projects/{pid}/comparison/snapshots/{snap['id']}", headers=_bearer(user.id)
    )
    assert r.status_code == 204
    # 重复 delete → 404
    r2 = await auth_client.delete(
        f"/api/projects/{pid}/comparison/snapshots/{snap['id']}", headers=_bearer(user.id)
    )
    assert r2.status_code == 404


# ─────────────── G3 tenant 隔离 ───────────────


async def test_cross_tenant_project_404(auth_client, make_user):
    """userB 访问 userA 的 project → 404 project_not_found（M02 范式）。"""
    userA = await make_user(email="m12-tA@example.com")
    userB = await make_user(email="m12-tB@example.com")
    pidA = await _create_project(auth_client, userA.id)
    r = await auth_client.get(
        f"/api/projects/{pidA}/comparison/snapshots", headers=_bearer(userB.id)
    )
    assert r.status_code == 404
    assert r.json()["code"] == "project_not_found"


# ─────────────── G4 viewer 写 3 端点全 403（M07 立 / M08+M11 应用 / M12 主动复制） ───────────────


async def test_viewer_write_returns_403_full_coverage(auth_client, make_user, db_session):
    """**元教训防御 actionable** 主动写不等 R2 抓：viewer 写**所有** 3 端点全 403。"""
    from api.models.project import MemberRole, ProjectMember

    userA = await make_user(email="m12-vA@example.com")
    userB = await make_user(email="m12-vB@example.com")
    pidA = await _create_project(auth_client, userA.id)
    n = await _create_node(auth_client, userA.id, pidA, name="A")
    t = await _enable_dim_type(auth_client, db_session, userA.id, pidA, key="m12r-viewer")
    await _seed_dim_record(auth_client, db_session, userA.id, pidA, n, t, {"v": "x"})
    snap = await _create_snapshot(auth_client, userA.id, pidA, [n], [t], name="vow")

    db_session.add(ProjectMember(project_id=pidA, user_id=userB.id, role=MemberRole.VIEWER.value))
    await db_session.commit()

    cases = [
        (
            "POST create",
            "post",
            f"/api/projects/{pidA}/comparison/snapshots",
            {"name": "x", "description": None, "node_ids": [n], "dimension_type_ids": [t]},
        ),
        (
            "PUT rename",
            "put",
            f"/api/projects/{pidA}/comparison/snapshots/{snap['id']}",
            {"name": "y", "description": None, "expected_version": 1},
        ),
        (
            "DELETE",
            "delete",
            f"/api/projects/{pidA}/comparison/snapshots/{snap['id']}",
            None,
        ),
    ]
    for label, method, url, body in cases:
        if method == "delete":
            r = await auth_client.delete(url, headers=_bearer(userB.id))
        elif method == "put":
            r = await auth_client.put(url, json=body, headers=_bearer(userB.id))
        else:
            r = await auth_client.post(url, json=body, headers=_bearer(userB.id))
        assert r.status_code == 403, f"{label}: expected 403 got {r.status_code}"
        assert r.json()["code"] == "permission_denied"


# ─────────────── G5 401 ───────────────


async def test_unauthenticated_returns_401(auth_client, make_user):
    user = await make_user(email="m12-401@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.get(f"/api/projects/{pid}/comparison/snapshots")
    assert r.status_code == 401
