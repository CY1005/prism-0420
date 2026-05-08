"""M08 子片 4 — Router + 5 endpoints 端到端测试。

覆盖 design §7 5 endpoints + §8 三层权限 + 401/403/404/409/422 + golden +
**M07 元教训防御 actionable**：viewer 写**所有**写端点 403 全覆盖（POST/PATCH/DELETE）。
"""

from __future__ import annotations

from uuid import uuid4

from api.auth.jwt_utils import encode_jwt


def _bearer(user_id) -> dict:
    return {"Authorization": f"Bearer {encode_jwt(user_id, extra_claims={'type': 'access'})}"}


async def _create_project(auth_client, user_id, name: str = "P1") -> str:
    r = await auth_client.post("/api/projects", json={"name": name}, headers=_bearer(user_id))
    assert r.status_code == 201
    return r.json()["id"]


async def _create_node(auth_client, user_id, pid: str, name: str = "n") -> str:
    r = await auth_client.post(
        f"/api/projects/{pid}/nodes", json={"name": name}, headers=_bearer(user_id)
    )
    assert r.status_code == 201
    return r.json()["id"]


async def _create_relation(
    auth_client,
    user_id,
    pid: str,
    src: str,
    tgt: str,
    rtype: str = "depends_on",
    notes: str | None = None,
) -> str:
    body = {
        "source_node_id": src,
        "target_node_id": tgt,
        "relation_type": rtype,
        "notes": notes,
    }
    r = await auth_client.post(
        f"/api/projects/{pid}/relations", json=body, headers=_bearer(user_id)
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ─────────────── G1: golden CRUD ───────────────


async def test_create_relation_returns_201(auth_client, make_user):
    user = await make_user(email="m08-cc@example.com")
    pid = await _create_project(auth_client, user.id)
    n1 = await _create_node(auth_client, user.id, pid, name="A")
    n2 = await _create_node(auth_client, user.id, pid, name="B")
    r = await auth_client.post(
        f"/api/projects/{pid}/relations",
        json={
            "source_node_id": n1,
            "target_node_id": n2,
            "relation_type": "depends_on",
            "notes": "x",
        },
        headers=_bearer(user.id),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["source_node_id"] == n1
    assert body["target_node_id"] == n2


async def test_list_relations(auth_client, make_user):
    user = await make_user(email="m08-list@example.com")
    pid = await _create_project(auth_client, user.id)
    n1 = await _create_node(auth_client, user.id, pid, name="A")
    n2 = await _create_node(auth_client, user.id, pid, name="B")
    await _create_relation(auth_client, user.id, pid, n1, n2)

    r = await auth_client.get(f"/api/projects/{pid}/relations", headers=_bearer(user.id))
    assert r.status_code == 200
    assert r.json()["total"] == 1


async def test_list_relations_by_node_bidirectional(auth_client, make_user):
    user = await make_user(email="m08-listn@example.com")
    pid = await _create_project(auth_client, user.id)
    n1 = await _create_node(auth_client, user.id, pid, name="A")
    n2 = await _create_node(auth_client, user.id, pid, name="B")
    n3 = await _create_node(auth_client, user.id, pid, name="C")
    await _create_relation(auth_client, user.id, pid, n1, n2)
    await _create_relation(auth_client, user.id, pid, n3, n1)
    await _create_relation(auth_client, user.id, pid, n2, n3)

    r = await auth_client.get(f"/api/projects/{pid}/nodes/{n1}/relations", headers=_bearer(user.id))
    assert r.status_code == 200
    assert r.json()["total"] == 2, "n1 出向 + 入向 = 2 条"


async def test_update_relation_notes(auth_client, make_user):
    user = await make_user(email="m08-upd@example.com")
    pid = await _create_project(auth_client, user.id)
    n1 = await _create_node(auth_client, user.id, pid, name="A")
    n2 = await _create_node(auth_client, user.id, pid, name="B")
    rid = await _create_relation(auth_client, user.id, pid, n1, n2, notes="orig")
    r = await auth_client.patch(
        f"/api/projects/{pid}/relations/{rid}",
        json={"notes": "updated"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    assert r.json()["notes"] == "updated"


async def test_delete_relation_returns_204(auth_client, make_user):
    user = await make_user(email="m08-del@example.com")
    pid = await _create_project(auth_client, user.id)
    n1 = await _create_node(auth_client, user.id, pid, name="A")
    n2 = await _create_node(auth_client, user.id, pid, name="B")
    rid = await _create_relation(auth_client, user.id, pid, n1, n2)
    r = await auth_client.delete(f"/api/projects/{pid}/relations/{rid}", headers=_bearer(user.id))
    assert r.status_code == 204


# ─────────────── G2: 错误码 ───────────────


async def test_create_relation_self_loop_returns_422(auth_client, make_user):
    user = await make_user(email="m08-loop@example.com")
    pid = await _create_project(auth_client, user.id)
    n1 = await _create_node(auth_client, user.id, pid, name="A")
    r = await auth_client.post(
        f"/api/projects/{pid}/relations",
        json={
            "source_node_id": n1,
            "target_node_id": n1,
            "relation_type": "depends_on",
        },
        headers=_bearer(user.id),
    )
    assert r.status_code == 422


async def test_create_relation_cross_project_node_returns_404(auth_client, make_user):
    """节点不属于该 project → RelationNodeNotInProjectError (404)。"""
    user = await make_user(email="m08-xpn@example.com")
    pidA = await _create_project(auth_client, user.id, name="A")
    pidB = await _create_project(auth_client, user.id, name="B")
    nA = await _create_node(auth_client, user.id, pidA, name="A")
    nB = await _create_node(auth_client, user.id, pidB, name="B")

    r = await auth_client.post(
        f"/api/projects/{pidA}/relations",
        json={
            "source_node_id": nA,
            "target_node_id": nB,  # B 项目节点
            "relation_type": "depends_on",
        },
        headers=_bearer(user.id),
    )
    assert r.status_code == 404
    assert r.json()["code"] == "relation_node_not_in_project"


async def test_create_relation_duplicate_returns_409(auth_client, make_user):
    user = await make_user(email="m08-dup@example.com")
    pid = await _create_project(auth_client, user.id)
    n1 = await _create_node(auth_client, user.id, pid, name="A")
    n2 = await _create_node(auth_client, user.id, pid, name="B")

    body = {"source_node_id": n1, "target_node_id": n2, "relation_type": "depends_on"}
    r1 = await auth_client.post(
        f"/api/projects/{pid}/relations", json=body, headers=_bearer(user.id)
    )
    assert r1.status_code == 201
    r2 = await auth_client.post(
        f"/api/projects/{pid}/relations", json=body, headers=_bearer(user.id)
    )
    assert r2.status_code == 409
    assert r2.json()["code"] == "relation_duplicate"


async def test_get_relation_not_found_via_patch_returns_404(auth_client, make_user):
    user = await make_user(email="m08-nf@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.patch(
        f"/api/projects/{pid}/relations/{uuid4()}",
        json={"notes": "x"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 404
    assert r.json()["code"] == "relation_not_found"


# ─────────────── G3: tenant + viewer 写全覆盖 + 401 ───────────────


async def test_relation_cross_tenant_returns_404(auth_client, make_user):
    userA = await make_user(email="m08-xtA@example.com")
    userB = await make_user(email="m08-xtB@example.com")
    pidA = await _create_project(auth_client, userA.id)

    r = await auth_client.get(f"/api/projects/{pidA}/relations", headers=_bearer(userB.id))
    assert r.status_code == 404
    assert r.json()["code"] == "project_not_found"


async def test_relation_viewer_write_403_full_coverage(auth_client, make_user, db_session):
    """**M07 元教训防御 actionable** 主动写不等 R2 抓：viewer 写**所有** 3 端点全 403。"""
    from api.models.project import MemberRole, ProjectMember

    userA = await make_user(email="m08-vA@example.com")
    userB = await make_user(email="m08-vB@example.com")
    pidA = await _create_project(auth_client, userA.id)
    n1 = await _create_node(auth_client, userA.id, pidA, name="A")
    n2 = await _create_node(auth_client, userA.id, pidA, name="B")
    rid = await _create_relation(auth_client, userA.id, pidA, n1, n2)

    db_session.add(ProjectMember(project_id=pidA, user_id=userB.id, role=MemberRole.VIEWER.value))
    await db_session.commit()

    cases = [
        (
            "POST create",
            "post",
            f"/api/projects/{pidA}/relations",
            {"source_node_id": n1, "target_node_id": n2, "relation_type": "related_to"},
        ),
        (
            "PATCH update",
            "patch",
            f"/api/projects/{pidA}/relations/{rid}",
            {"notes": "hack"},
        ),
        ("DELETE", "delete", f"/api/projects/{pidA}/relations/{rid}", None),
    ]
    for label, method, url, body in cases:
        if method == "delete":
            r = await auth_client.delete(url, headers=_bearer(userB.id))
        elif method == "patch":
            r = await auth_client.patch(url, json=body, headers=_bearer(userB.id))
        else:
            r = await auth_client.post(url, json=body, headers=_bearer(userB.id))
        assert r.status_code == 403, f"{label}: expected 403 got {r.status_code}"
        assert r.json()["code"] == "permission_denied"


async def test_unauthenticated_returns_401(auth_client, make_user):
    user = await make_user(email="m08-401@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.get(f"/api/projects/{pid}/relations")
    assert r.status_code == 401
