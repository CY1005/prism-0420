"""M07 子片 4 — Router + 7 endpoints 端到端测试。

覆盖 design §7 7 endpoints + §8 三层权限 + 401/403/404/422 + golden + 状态机 +
tenant + viewer 写。
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


async def _create_issue(auth_client, user_id, pid: str, **kw) -> str:
    body = {"category": "bug", "title": "t", "description": "d", **kw}
    r = await auth_client.post(f"/api/projects/{pid}/issues", json=body, headers=_bearer(user_id))
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ─────────────── G1: golden CRUD ───────────────


async def test_create_issue_returns_201(auth_client, make_user):
    user = await make_user(email="m07-cc@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.post(
        f"/api/projects/{pid}/issues",
        json={"category": "bug", "title": "x", "description": "d", "tags": ["p0"]},
        headers=_bearer(user.id),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["category"] == "bug"
    assert body["status"] == "open"
    assert body["tags"] == ["p0"]


async def test_list_issues_filter_category(auth_client, make_user):
    user = await make_user(email="m07-list@example.com")
    pid = await _create_project(auth_client, user.id)
    await _create_issue(auth_client, user.id, pid, category="bug", title="b1")
    await _create_issue(auth_client, user.id, pid, category="tech_debt", title="t1")

    r = await auth_client.get(f"/api/projects/{pid}/issues?category=bug", headers=_bearer(user.id))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1


async def test_list_issues_by_node(auth_client, make_user):
    user = await make_user(email="m07-listn@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid)
    await _create_issue(auth_client, user.id, pid, node_id=nid, title="n1")
    await _create_issue(auth_client, user.id, pid, title="floating")

    r = await auth_client.get(f"/api/projects/{pid}/nodes/{nid}/issues", headers=_bearer(user.id))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["node_id"] == nid


async def test_get_issue(auth_client, make_user):
    user = await make_user(email="m07-get@example.com")
    pid = await _create_project(auth_client, user.id)
    iid = await _create_issue(auth_client, user.id, pid)
    r = await auth_client.get(f"/api/projects/{pid}/issues/{iid}", headers=_bearer(user.id))
    assert r.status_code == 200
    assert r.json()["id"] == iid


async def test_get_issue_not_found(auth_client, make_user):
    user = await make_user(email="m07-getnf@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.get(f"/api/projects/{pid}/issues/{uuid4()}", headers=_bearer(user.id))
    assert r.status_code == 404
    assert r.json()["code"] == "issue_not_found"


async def test_update_issue(auth_client, make_user):
    user = await make_user(email="m07-upd@example.com")
    pid = await _create_project(auth_client, user.id)
    iid = await _create_issue(auth_client, user.id, pid)
    r = await auth_client.put(
        f"/api/projects/{pid}/issues/{iid}",
        json={"title": "renamed"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    assert r.json()["title"] == "renamed"


async def test_delete_issue_returns_204(auth_client, make_user):
    user = await make_user(email="m07-del@example.com")
    pid = await _create_project(auth_client, user.id)
    iid = await _create_issue(auth_client, user.id, pid)
    r = await auth_client.delete(f"/api/projects/{pid}/issues/{iid}", headers=_bearer(user.id))
    assert r.status_code == 204


# ─────────────── G2: 状态机 transition ───────────────


async def test_transition_open_to_in_progress(auth_client, make_user):
    user = await make_user(email="m07-tr1@example.com")
    pid = await _create_project(auth_client, user.id)
    iid = await _create_issue(auth_client, user.id, pid)
    r = await auth_client.post(
        f"/api/projects/{pid}/issues/{iid}/transition",
        json={"target_status": "in_progress", "assigned_to": str(user.id)},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"


async def test_transition_open_to_in_progress_requires_assignee_returns_422(auth_client, make_user):
    user = await make_user(email="m07-tr2@example.com")
    pid = await _create_project(auth_client, user.id)
    iid = await _create_issue(auth_client, user.id, pid)
    r = await auth_client.post(
        f"/api/projects/{pid}/issues/{iid}/transition",
        json={"target_status": "in_progress"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 422
    assert r.json()["code"] == "issue_assignee_required"


async def test_transition_open_to_closed_returns_422(auth_client, make_user):
    user = await make_user(email="m07-tr3@example.com")
    pid = await _create_project(auth_client, user.id)
    iid = await _create_issue(auth_client, user.id, pid)
    r = await auth_client.post(
        f"/api/projects/{pid}/issues/{iid}/transition",
        json={"target_status": "closed"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "issue_transition_invalid"
    # dogfooding cluster-3 fix: design §13 + tests.md ER2 要求 details.current + details.target
    assert body["details"]["current"] == "open"
    assert body["details"]["target"] == "closed"


async def test_transition_closed_cannot_reopen_returns_422(auth_client, make_user):
    user = await make_user(email="m07-tr4@example.com")
    pid = await _create_project(auth_client, user.id)
    iid = await _create_issue(auth_client, user.id, pid)
    # open → resolved → closed
    await auth_client.post(
        f"/api/projects/{pid}/issues/{iid}/transition",
        json={"target_status": "resolved"},
        headers=_bearer(user.id),
    )
    await auth_client.post(
        f"/api/projects/{pid}/issues/{iid}/transition",
        json={"target_status": "closed"},
        headers=_bearer(user.id),
    )
    r = await auth_client.post(
        f"/api/projects/{pid}/issues/{iid}/transition",
        json={"target_status": "open"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 422
    assert r.json()["code"] == "issue_closed_error"


# ─────────────── G3: cross-project node + tenant + viewer ───────────────


async def test_create_issue_cross_project_node_returns_422(auth_client, make_user):
    user = await make_user(email="m07-xp@example.com")
    pidA = await _create_project(auth_client, user.id, name="A")
    pidB = await _create_project(auth_client, user.id, name="B")
    nidA = await _create_node(auth_client, user.id, pidA)

    r = await auth_client.post(
        f"/api/projects/{pidB}/issues",
        json={"category": "bug", "title": "x", "description": "d", "node_id": nidA},
        headers=_bearer(user.id),
    )
    assert r.status_code == 422
    assert r.json()["code"] == "issue_node_cross_project"


async def test_issue_cross_tenant_returns_404(auth_client, make_user):
    """B 用户无 A 项目权限 → 404 不暴露存在性。"""
    userA = await make_user(email="m07-xtA@example.com")
    userB = await make_user(email="m07-xtB@example.com")
    pidA = await _create_project(auth_client, userA.id)
    r = await auth_client.get(f"/api/projects/{pidA}/issues", headers=_bearer(userB.id))
    assert r.status_code == 404
    assert r.json()["code"] == "project_not_found"


async def test_issue_viewer_write_returns_403_full_coverage(auth_client, make_user, db_session):
    """R2 P1-01 立修（M06 元教训复发立修）：B 是 A 项目 viewer → 4 写端点全 403。

    对照 M06 R2 P1-02 立修范式：每个写端点单独抄写
    Depends(check_project_access(role="editor")) 是抄漏单点静默失效区域，必须 4
    端点全测。M07 sprint 是该元教训"复发 + 应用立修"的第一次实证。
    """
    from api.models.project import MemberRole, ProjectMember

    userA = await make_user(email="m07-vA@example.com")
    userB = await make_user(email="m07-vB@example.com")
    pidA = await _create_project(auth_client, userA.id)
    iidA = await _create_issue(auth_client, userA.id, pidA)

    db_session.add(ProjectMember(project_id=pidA, user_id=userB.id, role=MemberRole.VIEWER.value))
    await db_session.commit()

    cases = [
        (
            "POST create",
            "post",
            f"/api/projects/{pidA}/issues",
            {"category": "bug", "title": "hack", "description": "d"},
        ),
        (
            "PUT update",
            "put",
            f"/api/projects/{pidA}/issues/{iidA}",
            {"title": "hack"},
        ),
        (
            "POST transition",
            "post",
            f"/api/projects/{pidA}/issues/{iidA}/transition",
            {"target_status": "resolved"},
        ),
        (
            "DELETE",
            "delete",
            f"/api/projects/{pidA}/issues/{iidA}",
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
        assert r.json()["code"] == "permission_denied", f"{label}: wrong code"


async def test_unauthenticated_returns_401(auth_client, make_user):
    user = await make_user(email="m07-401@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.get(f"/api/projects/{pid}/issues")
    assert r.status_code == 401


# ─────────────── G4: Phase 2.2 子片 5 — D 类 #3 join 字段装配 ───────────────
# SR-CLEANUP-3 防假覆盖：字面断言响应 JSON 含 node_name / created_by_name /
# assigned_to_name 非 None；selectinload + lazy="raise" 链路真通。


async def test_list_issues_join_fields_populated(auth_client, make_user):
    """D 类 #3 装配实证：list 返回 node_name / created_by_name / assigned_to_name 真值。"""
    user = await make_user(email="m07-join-list@example.com", name="Alice Joiner")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="JoinNode")
    await _create_issue(
        auth_client,
        user.id,
        pid,
        node_id=nid,
        title="join-issue",
        assigned_to=str(user.id),
    )

    r = await auth_client.get(f"/api/projects/{pid}/issues", headers=_bearer(user.id))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["node_name"] == "JoinNode"
    assert item["created_by_name"] == "Alice Joiner"
    assert item["assigned_to_name"] == "Alice Joiner"


async def test_get_issue_join_fields_populated(auth_client, make_user):
    user = await make_user(email="m07-join-get@example.com", name="Bob Reader")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="GetNode")
    iid = await _create_issue(auth_client, user.id, pid, node_id=nid, title="g")

    r = await auth_client.get(f"/api/projects/{pid}/issues/{iid}", headers=_bearer(user.id))
    assert r.status_code == 200
    body = r.json()
    assert body["node_name"] == "GetNode"
    assert body["created_by_name"] == "Bob Reader"
    assert body["assigned_to_name"] is None  # 未指派


async def test_floating_issue_node_name_is_none(auth_client, make_user):
    """游离 issue（node_id=None）→ node_name 必须 None，不能误填。"""
    user = await make_user(email="m07-float@example.com", name="Carol")
    pid = await _create_project(auth_client, user.id)
    iid = await _create_issue(auth_client, user.id, pid, title="floating")  # node_id 未传

    r = await auth_client.get(f"/api/projects/{pid}/issues/{iid}", headers=_bearer(user.id))
    assert r.status_code == 200
    assert r.json()["node_name"] is None
    assert r.json()["created_by_name"] == "Carol"
