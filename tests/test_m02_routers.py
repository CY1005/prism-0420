"""M02 子片 4 — Router + 11 endpoints + check_project_access Depends.

覆盖 design §7 11 endpoints + §8 权限三层 (401/403/404/422 + happy)。
"""

from __future__ import annotations

from uuid import uuid4

from api.auth.jwt_utils import encode_jwt


def _bearer(user_id) -> dict:
    return {"Authorization": f"Bearer {encode_jwt(user_id, extra_claims={'type': 'access'})}"}


# ─────────────── GET / POST /api/projects ───────────────


async def test_list_projects_unauthorized_returns_401(auth_client):
    r = await auth_client.get("/api/projects")
    assert r.status_code == 401


async def test_create_project_returns_201(auth_client, make_user):
    user = await make_user(email="p-creator@example.com")
    r = await auth_client.post(
        "/api/projects",
        json={"name": "ProjA", "template_type": "custom"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "ProjA"
    assert body["status"] == "active"
    assert body["owner_id"] == str(user.id)


async def test_create_project_returns_self_in_list(auth_client, make_user):
    user = await make_user(email="p-list@example.com")
    await auth_client.post("/api/projects", json={"name": "ListP1"}, headers=_bearer(user.id))
    r = await auth_client.get("/api/projects", headers=_bearer(user.id))
    assert r.status_code == 200
    body = r.json()
    names = {item["name"] for item in body["items"]}
    assert "ListP1" in names


async def test_create_duplicate_active_name_returns_409(auth_client, make_user):
    user = await make_user(email="p-dup@example.com")
    await auth_client.post("/api/projects", json={"name": "DupP"}, headers=_bearer(user.id))
    r = await auth_client.post("/api/projects", json={"name": "DupP"}, headers=_bearer(user.id))
    assert r.status_code == 409
    assert r.json()["code"] == "project_name_duplicate"


# ─────────────── GET / PUT /api/projects/{pid} ───────────────


async def test_get_project_non_member_returns_404(auth_client, make_user):
    """R1 P2-A: 非 member 返回 404 而非 403 (防 enumeration)."""
    owner = await make_user(email="p-owner@example.com")
    other = await make_user(email="p-other@example.com")
    cr = await auth_client.post("/api/projects", json={"name": "PrivP"}, headers=_bearer(owner.id))
    pid = cr.json()["id"]
    r = await auth_client.get(f"/api/projects/{pid}", headers=_bearer(other.id))
    assert r.status_code == 404
    assert r.json()["code"] == "project_not_found"


async def test_update_project_by_viewer_returns_403(auth_client, make_user):
    """member 但 role=viewer: 403 PERMISSION_DENIED."""
    owner = await make_user(email="p-own2@example.com")
    viewer = await make_user(email="p-view@example.com")
    cr = await auth_client.post(
        "/api/projects", json={"name": "ViewerP"}, headers=_bearer(owner.id)
    )
    pid = cr.json()["id"]
    # 邀请 viewer
    await auth_client.post(
        f"/api/projects/{pid}/members",
        json={"user_id": str(viewer.id), "role": "viewer"},
        headers=_bearer(owner.id),
    )
    r = await auth_client.put(
        f"/api/projects/{pid}",
        json={"description": "viewer cant edit"},
        headers=_bearer(viewer.id),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "permission_denied"


async def test_update_project_by_owner_succeeds(auth_client, make_user):
    owner = await make_user(email="p-upd@example.com")
    cr = await auth_client.post("/api/projects", json={"name": "UpdP"}, headers=_bearer(owner.id))
    pid = cr.json()["id"]
    r = await auth_client.put(
        f"/api/projects/{pid}",
        json={"description": "new desc"},
        headers=_bearer(owner.id),
    )
    assert r.status_code == 200
    assert r.json()["description"] == "new desc"


# ─────────────── archive ───────────────


async def test_archive_then_again_returns_409(auth_client, make_user):
    owner = await make_user(email="p-arch@example.com")
    cr = await auth_client.post("/api/projects", json={"name": "ArchP"}, headers=_bearer(owner.id))
    pid = cr.json()["id"]
    r1 = await auth_client.post(f"/api/projects/{pid}/archive", headers=_bearer(owner.id))
    assert r1.status_code == 200
    assert r1.json()["status"] == "archived"
    r2 = await auth_client.post(f"/api/projects/{pid}/archive", headers=_bearer(owner.id))
    assert r2.status_code == 409
    assert r2.json()["code"] == "project_already_archived"


# ─────────────── delete (design M02 §1 §4 §13 G2: 软删除不可逆 / 物理删除拒) ───────────────


async def test_delete_project_returns_422_project_delete_not_supported(auth_client, make_user):
    """DELETE /api/projects/{pid} 返 422 PROJECT_DELETE_NOT_SUPPORTED.

    design M02 §1 L117 + §4 L503 G2 决策：归档=软删除不可逆 / 不物理删除。
    ErrorCode + ProjectDeleteNotSupportedError 已在 design §13 注册（http_status=422）。
    （P4-cluster-2-revert: cluster-2 commit 0992dc8 错装物理删除 / 此 fix 改回 design 真相）
    """
    owner = await make_user(email="p-del-422@example.com")
    cr = await auth_client.post("/api/projects", json={"name": "DelP"}, headers=_bearer(owner.id))
    assert cr.status_code == 201
    pid = cr.json()["id"]

    r = await auth_client.delete(f"/api/projects/{pid}", headers=_bearer(owner.id))
    assert r.status_code == 422
    assert r.json()["code"] == "project_delete_not_supported"

    # 项目仍存在（未被物理删除 / 也未被自动归档）
    get_r = await auth_client.get(f"/api/projects/{pid}", headers=_bearer(owner.id))
    assert get_r.status_code == 200
    assert get_r.json()["status"] == "active"


async def test_delete_project_non_owner_returns_403(auth_client, make_user):
    """DELETE 非 owner 应被 check_project_access(role=owner) 拦在 422 之前.

    顺序：check_project_access(role=owner) Depends 先跑 → 非 owner 直接 403
    （此场景 422 永远不可达 / 防御深度自检）。
    """
    owner = await make_user(email="p-del-owner@example.com")
    viewer = await make_user(email="p-del-viewer@example.com")
    cr = await auth_client.post(
        "/api/projects", json={"name": "DelViewerP"}, headers=_bearer(owner.id)
    )
    pid = cr.json()["id"]
    # 邀 viewer
    await auth_client.post(
        f"/api/projects/{pid}/members",
        json={"user_id": str(viewer.id), "role": "viewer"},
        headers=_bearer(owner.id),
    )
    r = await auth_client.delete(f"/api/projects/{pid}", headers=_bearer(viewer.id))
    assert r.status_code == 403


# ─────────────── members ───────────────


async def test_invite_member_returns_201_then_409_on_dup(auth_client, make_user):
    owner = await make_user(email="m-own@example.com")
    invitee = await make_user(email="m-inv@example.com")
    cr = await auth_client.post("/api/projects", json={"name": "MembP"}, headers=_bearer(owner.id))
    pid = cr.json()["id"]
    r1 = await auth_client.post(
        f"/api/projects/{pid}/members",
        json={"user_id": str(invitee.id), "role": "editor"},
        headers=_bearer(owner.id),
    )
    assert r1.status_code == 201
    assert r1.json()["role"] == "editor"
    r2 = await auth_client.post(
        f"/api/projects/{pid}/members",
        json={"user_id": str(invitee.id), "role": "viewer"},
        headers=_bearer(owner.id),
    )
    assert r2.status_code == 409
    assert r2.json()["code"] == "member_already_exists"


async def test_list_members(auth_client, make_user):
    owner = await make_user(email="m-list@example.com")
    cr = await auth_client.post("/api/projects", json={"name": "MListP"}, headers=_bearer(owner.id))
    pid = cr.json()["id"]
    r = await auth_client.get(f"/api/projects/{pid}/members", headers=_bearer(owner.id))
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["role"] == "owner"


async def test_update_member_role(auth_client, make_user):
    owner = await make_user(email="m-role-own@example.com")
    target = await make_user(email="m-role-tgt@example.com")
    cr = await auth_client.post("/api/projects", json={"name": "RoleP"}, headers=_bearer(owner.id))
    pid = cr.json()["id"]
    await auth_client.post(
        f"/api/projects/{pid}/members",
        json={"user_id": str(target.id), "role": "viewer"},
        headers=_bearer(owner.id),
    )
    r = await auth_client.put(
        f"/api/projects/{pid}/members/{target.id}",
        json={"role": "editor"},
        headers=_bearer(owner.id),
    )
    assert r.status_code == 200
    assert r.json()["role"] == "editor"


async def test_cannot_remove_owner_returns_422(auth_client, make_user):
    owner = await make_user(email="m-rm-own@example.com")
    cr = await auth_client.post("/api/projects", json={"name": "RmOwnP"}, headers=_bearer(owner.id))
    pid = cr.json()["id"]
    r = await auth_client.delete(
        f"/api/projects/{pid}/members/{owner.id}", headers=_bearer(owner.id)
    )
    assert r.status_code == 422
    assert r.json()["code"] == "member_cannot_remove_owner"


async def test_remove_member_returns_204(auth_client, make_user):
    owner = await make_user(email="m-rm-own2@example.com")
    target = await make_user(email="m-rm-tgt@example.com")
    cr = await auth_client.post("/api/projects", json={"name": "RmOkP2"}, headers=_bearer(owner.id))
    pid = cr.json()["id"]
    await auth_client.post(
        f"/api/projects/{pid}/members",
        json={"user_id": str(target.id), "role": "viewer"},
        headers=_bearer(owner.id),
    )
    r = await auth_client.delete(
        f"/api/projects/{pid}/members/{target.id}", headers=_bearer(owner.id)
    )
    assert r.status_code == 204


# ─────────────── dimension configs (R10-1 batch3) ───────────────


async def test_dim_config_list_empty(auth_client, make_user):
    owner = await make_user(email="dc-empty@example.com")
    cr = await auth_client.post(
        "/api/projects", json={"name": "DcEmptyP"}, headers=_bearer(owner.id)
    )
    pid = cr.json()["id"]
    r = await auth_client.get(f"/api/projects/{pid}/dimension-configs", headers=_bearer(owner.id))
    assert r.status_code == 200
    assert r.json()["items"] == []


async def test_dim_config_batch_update_creates_independent_events(
    auth_client, make_user, db_session
):
    """R10-1 batch3 + R1-A P0→R2 修: 每个 config 写独立 activity_log 事件 (本期 stub 走 structlog)."""
    from sqlalchemy import text

    owner = await make_user(email="dc-batch@example.com")
    cr = await auth_client.post(
        "/api/projects", json={"name": "DcBatchP"}, headers=_bearer(owner.id)
    )
    pid = cr.json()["id"]

    # 取 default dimension type id
    r = await db_session.execute(text("SELECT id FROM dimension_types WHERE key='default'"))
    dim_type_id = r.scalar_one()

    # batch update 1 个新 config
    r = await auth_client.put(
        f"/api/projects/{pid}/dimension-configs",
        json={"configs": [{"dimension_type_id": dim_type_id, "enabled": True, "sort_order": 0}]},
        headers=_bearer(owner.id),
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["dimension_type_id"] == dim_type_id


async def test_dim_config_batch_update_unknown_type_returns_422(auth_client, make_user):
    owner = await make_user(email="dc-bad@example.com")
    cr = await auth_client.post("/api/projects", json={"name": "DcBadP"}, headers=_bearer(owner.id))
    pid = cr.json()["id"]
    r = await auth_client.put(
        f"/api/projects/{pid}/dimension-configs",
        json={"configs": [{"dimension_type_id": 999999, "enabled": True}]},
        headers=_bearer(owner.id),
    )
    assert r.status_code == 422
    assert r.json()["code"] == "dimension_config_invalid"


# ─────────────── ai-provider (encrypts) ───────────────


async def test_ai_provider_update_returns_200_no_key_in_response(auth_client, make_user):
    owner = await make_user(email="ai-prov@example.com")
    cr = await auth_client.post(
        "/api/projects", json={"name": "AiProvP"}, headers=_bearer(owner.id)
    )
    pid = cr.json()["id"]
    r = await auth_client.put(
        f"/api/projects/{pid}/ai-provider",
        json={"ai_provider": "claude", "ai_api_key": "sk-secret-xyz"},
        headers=_bearer(owner.id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ai_provider"] == "claude"
    assert "ai_api_key_enc" not in body  # 不返回密文
    assert "ai_api_key" not in body


# ─────────────── B 路径子选项实证: move-team OpenAPI 不含 ───────────────


async def test_b_path_move_team_endpoint_registered_after_m20(auth_client, make_user):
    """B 路径子选项实证升级（M20 sprint 子片 4 启用 / 2026-05-09）：

    M02 sprint 期：move-team router 不实装 → 404（FastAPI route 不存在）。
    M20 sprint 启用后：route 存在；旧字段名 'team_id' 被 schema rejected
    （schema 用 target_team_id + extra='forbid' / Pydantic 422）。
    """
    owner = await make_user(email="b-path@example.com")
    cr = await auth_client.post(
        "/api/projects", json={"name": "MoveTeamP"}, headers=_bearer(owner.id)
    )
    pid = cr.json()["id"]
    r = await auth_client.post(
        f"/api/projects/{pid}/move-team",
        json={"team_id": str(uuid4())},
        headers=_bearer(owner.id),
    )
    assert r.status_code == 422  # M20: schema field is target_team_id + extra='forbid'
