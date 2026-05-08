"""M06 子片 4 — Router + 8 endpoints 端到端测试。

覆盖 design §7 8 endpoints + §8 三层权限 + 401/403/404/409/422 + golden + tenant。
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


async def _create_competitor(auth_client, user_id, pid: str, name: str = "Notion") -> str:
    r = await auth_client.post(
        f"/api/projects/{pid}/competitors",
        json={"display_name": name, "website_url": "https://notion.so", "description": "x"},
        headers=_bearer(user_id),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ─────────────── G1: Competitor 全局 CRUD ───────────────


async def test_create_competitor_returns_201(auth_client, make_user):
    user = await make_user(email="m06-cc@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.post(
        f"/api/projects/{pid}/competitors",
        json={"display_name": "Notion", "description": "all-in-one"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["display_name"] == "Notion"
    assert body["description"] == "all-in-one"


async def test_list_competitors_returns_items(auth_client, make_user):
    user = await make_user(email="m06-list@example.com")
    pid = await _create_project(auth_client, user.id)
    await _create_competitor(auth_client, user.id, pid, name="A")
    await _create_competitor(auth_client, user.id, pid, name="B")

    r = await auth_client.get(f"/api/projects/{pid}/competitors", headers=_bearer(user.id))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert {c["display_name"] for c in body["items"]} == {"A", "B"}


async def test_update_competitor(auth_client, make_user):
    user = await make_user(email="m06-upd@example.com")
    pid = await _create_project(auth_client, user.id)
    cid = await _create_competitor(auth_client, user.id, pid)
    r = await auth_client.put(
        f"/api/projects/{pid}/competitors/{cid}",
        json={"display_name": "Renamed"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    assert r.json()["display_name"] == "Renamed"


async def test_update_competitor_not_found_returns_404(auth_client, make_user):
    user = await make_user(email="m06-updnf@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.put(
        f"/api/projects/{pid}/competitors/{uuid4()}",
        json={"display_name": "X"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 404
    assert r.json()["code"] == "competitor_not_found"


async def test_delete_competitor_returns_204(auth_client, make_user):
    user = await make_user(email="m06-del@example.com")
    pid = await _create_project(auth_client, user.id)
    cid = await _create_competitor(auth_client, user.id, pid)
    r = await auth_client.delete(f"/api/projects/{pid}/competitors/{cid}", headers=_bearer(user.id))
    assert r.status_code == 204


# ─────────────── G2: CompetitorRef CRUD ───────────────


async def test_create_ref_returns_201(auth_client, make_user):
    user = await make_user(email="m06-rcc@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid)
    cid = await _create_competitor(auth_client, user.id, pid)

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/competitor-refs",
        json={
            "competitor_id": cid,
            "competitor_version": "v3",
            "feature_coverage": "覆盖",
            "tech_approach": "block-based",
            "pros_and_cons": {"pros": ["快"], "cons": ["贵"]},
        },
        headers=_bearer(user.id),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["competitor_id"] == cid
    assert body["pros_and_cons"] == {"pros": ["快"], "cons": ["贵"]}


async def test_create_ref_duplicate_returns_409(auth_client, make_user):
    user = await make_user(email="m06-rdup@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid)
    cid = await _create_competitor(auth_client, user.id, pid)

    body = {"competitor_id": cid}
    r1 = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/competitor-refs",
        json=body,
        headers=_bearer(user.id),
    )
    assert r1.status_code == 201
    r2 = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/competitor-refs",
        json=body,
        headers=_bearer(user.id),
    )
    assert r2.status_code == 409
    assert r2.json()["code"] == "competitor_ref_duplicate"


async def test_create_ref_cross_project_competitor_returns_422(auth_client, make_user):
    user = await make_user(email="m06-rxp@example.com")
    pidA = await _create_project(auth_client, user.id, "A")
    pidB = await _create_project(auth_client, user.id, "B")
    nidB = await _create_node(auth_client, user.id, pidB)
    cidA = await _create_competitor(auth_client, user.id, pidA, name="A1")

    r = await auth_client.post(
        f"/api/projects/{pidB}/nodes/{nidB}/competitor-refs",
        json={"competitor_id": cidA},  # A 项目竞品
        headers=_bearer(user.id),
    )
    assert r.status_code == 422
    assert r.json()["code"] == "competitor_cross_project"


async def test_list_refs(auth_client, make_user):
    user = await make_user(email="m06-rlist@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid)
    cid = await _create_competitor(auth_client, user.id, pid)
    await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/competitor-refs",
        json={"competitor_id": cid},
        headers=_bearer(user.id),
    )

    r = await auth_client.get(
        f"/api/projects/{pid}/nodes/{nid}/competitor-refs", headers=_bearer(user.id)
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1


async def test_update_ref(auth_client, make_user):
    user = await make_user(email="m06-rupd@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid)
    cid = await _create_competitor(auth_client, user.id, pid)
    create = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/competitor-refs",
        json={"competitor_id": cid},
        headers=_bearer(user.id),
    )
    rid = create.json()["id"]

    r = await auth_client.put(
        f"/api/projects/{pid}/nodes/{nid}/competitor-refs/{rid}",
        json={"feature_coverage": "新覆盖"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    assert r.json()["feature_coverage"] == "新覆盖"


async def test_delete_ref_returns_204(auth_client, make_user):
    user = await make_user(email="m06-rdel@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid)
    cid = await _create_competitor(auth_client, user.id, pid)
    create = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/competitor-refs",
        json={"competitor_id": cid},
        headers=_bearer(user.id),
    )
    rid = create.json()["id"]

    r = await auth_client.delete(
        f"/api/projects/{pid}/nodes/{nid}/competitor-refs/{rid}", headers=_bearer(user.id)
    )
    assert r.status_code == 204


# ─────────────── tenant 越权 + viewer 写 403 ───────────────


async def test_competitor_cross_tenant_returns_404(auth_client, make_user):
    """B 用户无 A 项目权限 → check_project_access 返 404 不暴露存在性。"""
    userA = await make_user(email="m06-xtA@example.com")
    userB = await make_user(email="m06-xtB@example.com")
    pidA = await _create_project(auth_client, userA.id)

    r = await auth_client.get(f"/api/projects/{pidA}/competitors", headers=_bearer(userB.id))
    assert r.status_code == 404
    assert r.json()["code"] == "project_not_found"


async def test_competitor_viewer_write_returns_403(auth_client, make_user, db_session):
    """R2 范式：B 是 A 项目 viewer → POST competitor 应 403。"""
    from api.models.project import MemberRole, ProjectMember

    userA = await make_user(email="m06-vA@example.com")
    userB = await make_user(email="m06-vB@example.com")
    pidA = await _create_project(auth_client, userA.id)

    db_session.add(ProjectMember(project_id=pidA, user_id=userB.id, role=MemberRole.VIEWER.value))
    await db_session.commit()

    r = await auth_client.post(
        f"/api/projects/{pidA}/competitors",
        json={"display_name": "hack"},
        headers=_bearer(userB.id),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "permission_denied"


async def test_unauthenticated_returns_401(auth_client, make_user):
    user = await make_user(email="m06-unauth@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.get(f"/api/projects/{pid}/competitors")
    assert r.status_code == 401
