"""M14 子片 4 — Router 8 endpoints + 端到端测试。

覆盖 design §7 8 endpoints + §8 三层权限 + 401/403/404/409/422 + golden + 全局豁免 +
tags 验证 + cross-project node link 允许（design §1 灰区 2）+ owner-vs-other 403 +
platform_admin 豁免 + IntegrityError 区分约束名（M05 P1-01 复用）。

⚠️ M14 全局豁免特化：
- viewer 写 403 元教训 N/A（design §8 已锁全局豁免无 project role）
- cross-tenant 404 元教训 N/A（M14 无 tenant）
- 用 owner-or-admin 403 + 已登录 401 替代覆盖跨用户写防御
"""

from __future__ import annotations

from uuid import uuid4

from api.auth.jwt_utils import encode_jwt
from api.models.user import UserRole


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


# ─────────────── M14-G1 创建动态 ───────────────


async def test_create_news_golden(auth_client, make_user):
    user = await make_user()
    r = await auth_client.post(
        "/api/news",
        json={"title": "AI 监管新规", "tags": ["AI", "监管"]},
        headers=_bearer(user.id),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["title"] == "AI 监管新规"
    assert body["source_type"] == "manual"
    assert body["tags"] == ["AI", "监管"]
    assert body["created_by"] == str(user.id)
    assert body["created_by_name"]
    assert body["linked_nodes"] == []


# ─────────────── M14-G2 列表读取（全局豁免）───────────────


async def test_list_news_returns_global_no_tenant_filter(auth_client, make_user):
    """T1+T2：跨 project / 无 project 用户均可读全局列表。"""
    user_a = await make_user()
    user_b = await make_user()
    await auth_client.post("/api/news", json={"title": "A"}, headers=_bearer(user_a.id))
    await auth_client.post("/api/news", json={"title": "B"}, headers=_bearer(user_b.id))
    r = await auth_client.get("/api/news", headers=_bearer(user_a.id))
    assert r.status_code == 200
    titles = {item["title"] for item in r.json()["items"]}
    assert {"A", "B"} <= titles


async def test_list_news_pagination(auth_client, make_user):
    user = await make_user()
    for i in range(3):
        await auth_client.post("/api/news", json={"title": f"n{i}"}, headers=_bearer(user.id))
    r = await auth_client.get("/api/news?page=1&page_size=2", headers=_bearer(user.id))
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["page_size"] == 2


async def test_list_news_pagination_invalid_returns_422(auth_client, make_user):
    """R1-C P1-2 立修：page/page_size <= 0 → FastAPI Query ge=1 拦截 → 422。"""
    user = await make_user()
    r = await auth_client.get("/api/news?page=0", headers=_bearer(user.id))
    assert r.status_code == 422
    r = await auth_client.get("/api/news?page_size=0", headers=_bearer(user.id))
    assert r.status_code == 422


# ─────────────── M14-G3 详情 ───────────────


async def test_get_news_detail_with_linked_nodes(auth_client, make_user):
    """R1-A P1-1 立修：linked_nodes 链通（NodeRef 含 node_name + project_id）。"""
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="auth-flow")
    r = await auth_client.post("/api/news", json={"title": "auth update"}, headers=_bearer(user.id))
    news_id = r.json()["id"]
    await auth_client.post(
        f"/api/news/{news_id}/links",
        json={"node_id": nid},
        headers=_bearer(user.id),
    )
    r = await auth_client.get(f"/api/news/{news_id}", headers=_bearer(user.id))
    assert r.status_code == 200
    body = r.json()
    assert len(body["linked_nodes"]) == 1
    nr = body["linked_nodes"][0]
    assert nr["node_id"] == nid
    assert nr["node_name"] == "auth-flow"
    assert nr["project_id"] == pid


# ─────────────── M14-G4 update ───────────────


async def test_update_news_by_owner(auth_client, make_user):
    user = await make_user()
    r = await auth_client.post("/api/news", json={"title": "old"}, headers=_bearer(user.id))
    news_id = r.json()["id"]
    r = await auth_client.put(
        f"/api/news/{news_id}",
        json={"title": "new", "summary": "added"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    assert r.json()["title"] == "new"
    assert r.json()["summary"] == "added"


async def test_update_news_clears_tags_with_empty_list(auth_client, make_user):
    """R1-A P1-3 + R1-C P1-1 立修：tags=[] 不再被 v is not None 滤掉。"""
    user = await make_user()
    r = await auth_client.post(
        "/api/news", json={"title": "t", "tags": ["AI"]}, headers=_bearer(user.id)
    )
    news_id = r.json()["id"]
    r = await auth_client.put(f"/api/news/{news_id}", json={"tags": []}, headers=_bearer(user.id))
    assert r.status_code == 200
    assert r.json()["tags"] == []


async def test_update_news_by_non_owner_returns_403(auth_client, make_user):
    """元教训：非本人 update 拒（用 owner-or-admin 403 替代 viewer 写 403 元教训覆盖）。"""
    owner = await make_user()
    other = await make_user()
    r = await auth_client.post("/api/news", json={"title": "x"}, headers=_bearer(owner.id))
    news_id = r.json()["id"]
    r = await auth_client.put(
        f"/api/news/{news_id}", json={"title": "hijack"}, headers=_bearer(other.id)
    )
    assert r.status_code == 403
    assert r.json()["code"] == "news_forbidden"


async def test_update_news_by_platform_admin_bypasses_owner_check(auth_client, make_user):
    owner = await make_user()
    admin = await make_user(role=UserRole.PLATFORM_ADMIN.value)
    r = await auth_client.post("/api/news", json={"title": "x"}, headers=_bearer(owner.id))
    news_id = r.json()["id"]
    r = await auth_client.put(
        f"/api/news/{news_id}",
        json={"title": "moderated"},
        headers=_bearer(admin.id),
    )
    assert r.status_code == 200


# ─────────────── M14-G5 link / unlink ───────────────


async def test_link_node_golden(auth_client, make_user):
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="x")
    r = await auth_client.post("/api/news", json={"title": "t"}, headers=_bearer(user.id))
    news_id = r.json()["id"]
    r = await auth_client.post(
        f"/api/news/{news_id}/links",
        json={"node_id": nid},
        headers=_bearer(user.id),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["news_id"] == news_id
    assert body["node_id"] == nid
    assert body["node_name"] == "x"
    assert body["linked_by"] == str(user.id)


async def test_link_node_duplicate_returns_409(auth_client, make_user):
    """M05 P1-01 范式延续：UNIQUE(news_id, node_id) → 409 NEWS_LINK_DUPLICATE 区分约束名。"""
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="x")
    r = await auth_client.post("/api/news", json={"title": "t"}, headers=_bearer(user.id))
    news_id = r.json()["id"]
    await auth_client.post(
        f"/api/news/{news_id}/links",
        json={"node_id": nid},
        headers=_bearer(user.id),
    )
    r = await auth_client.post(
        f"/api/news/{news_id}/links",
        json={"node_id": nid},
        headers=_bearer(user.id),
    )
    assert r.status_code == 409
    assert r.json()["code"] == "news_link_duplicate"


async def test_link_node_missing_returns_404(auth_client, make_user):
    """E3：node_id 不存在 → 404 NOT_FOUND（design §14 ER1）。"""
    user = await make_user()
    r = await auth_client.post("/api/news", json={"title": "t"}, headers=_bearer(user.id))
    news_id = r.json()["id"]
    r = await auth_client.post(
        f"/api/news/{news_id}/links",
        json={"node_id": str(uuid4())},
        headers=_bearer(user.id),
    )
    assert r.status_code == 404


async def test_link_cross_project_node_allowed(auth_client, make_user):
    """design §1 灰区 2：全局动态可关联跨项目 node（不应被拦）。"""
    user_a = await make_user()
    user_b = await make_user()
    pid_b = await _create_project(auth_client, user_b.id, name="P-B")
    nid_b = await _create_node(auth_client, user_b.id, pid_b, name="b-node")
    r = await auth_client.post("/api/news", json={"title": "t"}, headers=_bearer(user_a.id))
    news_id = r.json()["id"]
    r = await auth_client.post(
        f"/api/news/{news_id}/links",
        json={"node_id": nid_b},
        headers=_bearer(user_a.id),
    )
    assert r.status_code == 201, r.text


async def test_unlink_node_golden(auth_client, make_user):
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="x")
    r = await auth_client.post("/api/news", json={"title": "t"}, headers=_bearer(user.id))
    news_id = r.json()["id"]
    await auth_client.post(
        f"/api/news/{news_id}/links",
        json={"node_id": nid},
        headers=_bearer(user.id),
    )
    r = await auth_client.delete(f"/api/news/{news_id}/links/{nid}", headers=_bearer(user.id))
    assert r.status_code == 204


async def test_unlink_missing_link_returns_404(auth_client, make_user):
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="x")
    r = await auth_client.post("/api/news", json={"title": "t"}, headers=_bearer(user.id))
    news_id = r.json()["id"]
    r = await auth_client.delete(f"/api/news/{news_id}/links/{nid}", headers=_bearer(user.id))
    assert r.status_code == 404
    assert r.json()["code"] == "news_link_not_found"


async def test_unlink_by_non_owner_allowed(auth_client, make_user):
    """R1-A P1-2 立修 design §8 disambiguation：unlink 已登录即可（与 link 对称，不要求 owner）。"""
    owner = await make_user()
    other = await make_user()
    pid = await _create_project(auth_client, owner.id)
    nid = await _create_node(auth_client, owner.id, pid, name="x")
    r = await auth_client.post("/api/news", json={"title": "t"}, headers=_bearer(owner.id))
    news_id = r.json()["id"]
    await auth_client.post(
        f"/api/news/{news_id}/links",
        json={"node_id": nid},
        headers=_bearer(owner.id),
    )
    r = await auth_client.delete(f"/api/news/{news_id}/links/{nid}", headers=_bearer(other.id))
    assert r.status_code == 204  # 非 owner 也可解除


# ─────────────── M14-G6 delete ───────────────


async def test_delete_news_by_owner(auth_client, make_user):
    user = await make_user()
    r = await auth_client.post("/api/news", json={"title": "t"}, headers=_bearer(user.id))
    news_id = r.json()["id"]
    r = await auth_client.delete(f"/api/news/{news_id}", headers=_bearer(user.id))
    assert r.status_code == 204
    r = await auth_client.get(f"/api/news/{news_id}", headers=_bearer(user.id))
    assert r.status_code == 404


async def test_delete_news_by_non_owner_returns_403(auth_client, make_user):
    owner = await make_user()
    other = await make_user()
    r = await auth_client.post("/api/news", json={"title": "t"}, headers=_bearer(owner.id))
    news_id = r.json()["id"]
    r = await auth_client.delete(f"/api/news/{news_id}", headers=_bearer(other.id))
    assert r.status_code == 403


async def test_delete_news_by_platform_admin(auth_client, make_user):
    owner = await make_user()
    admin = await make_user(role=UserRole.PLATFORM_ADMIN.value)
    r = await auth_client.post("/api/news", json={"title": "t"}, headers=_bearer(owner.id))
    news_id = r.json()["id"]
    r = await auth_client.delete(f"/api/news/{news_id}", headers=_bearer(admin.id))
    assert r.status_code == 204


async def test_delete_missing_returns_404(auth_client, make_user):
    user = await make_user()
    r = await auth_client.delete(f"/api/news/{uuid4()}", headers=_bearer(user.id))
    assert r.status_code == 404


# ─────────────── M14-E 边界 ───────────────


async def test_create_title_too_long_returns_422(auth_client, make_user):
    user = await make_user()
    r = await auth_client.post("/api/news", json={"title": "x" * 201}, headers=_bearer(user.id))
    assert r.status_code == 422


async def test_create_empty_title_returns_422(auth_client, make_user):
    user = await make_user()
    r = await auth_client.post("/api/news", json={"title": ""}, headers=_bearer(user.id))
    assert r.status_code == 422


async def test_create_invalid_url_returns_422(auth_client, make_user):
    user = await make_user()
    r = await auth_client.post(
        "/api/news",
        json={"title": "t", "source_url": "not-a-url"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 422


async def test_create_tag_too_long_returns_422(auth_client, make_user):
    """R1-C P1-3 立修：tags 单元素 max_length=50。"""
    user = await make_user()
    r = await auth_client.post(
        "/api/news",
        json={"title": "t", "tags": ["x" * 51]},
        headers=_bearer(user.id),
    )
    assert r.status_code == 422


# ─────────────── M14-P 权限 ───────────────


async def test_unauthenticated_read_returns_401(auth_client):
    r = await auth_client.get("/api/news")
    assert r.status_code == 401


async def test_unauthenticated_write_returns_401(auth_client):
    r = await auth_client.post("/api/news", json={"title": "t"})
    assert r.status_code == 401


# ─────────────── M14-NodeReverse 节点级反查 ───────────────


async def test_list_news_by_node_empty_returns_zero_page_size(auth_client, make_user):
    """R2 P1-3 立修 design §7 disambiguation：空列表 page_size=0（不再 ``or 1`` fallback）。"""
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="x")
    r = await auth_client.get(f"/api/nodes/{nid}/news", headers=_bearer(user.id))
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["page_size"] == 0


async def test_create_news_propagates_write_event_failure_e2e(auth_client, make_user, monkeypatch):
    """R2 P1-1 立修 元教训 e2e：write_event raise → 端点 500（M04+ 范式 5 写路径首条）。"""
    import api.services.industry_news_service as mod

    async def boom(**kwargs):
        raise RuntimeError("activity log failed")

    monkeypatch.setattr(mod, "write_event", boom)
    user = await make_user()
    r = await auth_client.post("/api/news", json={"title": "t"}, headers=_bearer(user.id))
    assert r.status_code == 500


async def test_link_node_propagates_write_event_failure_e2e(auth_client, make_user, monkeypatch):
    """R2 P1-1 立修：link 端点 write_event raise → 500（M04+ 范式 5 写路径覆盖第 2 条）。"""
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="x")
    r = await auth_client.post("/api/news", json={"title": "t"}, headers=_bearer(user.id))
    news_id = r.json()["id"]
    import api.services.industry_news_service as mod

    async def boom(**kwargs):
        if kwargs.get("action_type") == "link":
            raise RuntimeError("activity log failed")

    monkeypatch.setattr(mod, "write_event", boom)
    r = await auth_client.post(
        f"/api/news/{news_id}/links",
        json={"node_id": nid},
        headers=_bearer(user.id),
    )
    assert r.status_code == 500


async def test_create_news_activity_log_metadata_matches_design(
    auth_client, make_user, monkeypatch
):
    """R2 P1-2 立修 元教训：design §10 字面 metadata 字段集 e2e 验
    （M13 NEW 失效信号 design metadata 字段集每条都必须实装）。"""
    import api.services.industry_news_service as mod

    captured: list[dict] = []

    async def fake(**kwargs):
        captured.append(kwargs)

    monkeypatch.setattr(mod, "write_event", fake)
    user = await make_user()
    r = await auth_client.post(
        "/api/news",
        json={"title": "AI 监管", "tags": ["AI", "监管"]},
        headers=_bearer(user.id),
    )
    assert r.status_code == 201
    assert len(captured) == 1
    ev = captured[0]
    assert ev["action_type"] == "create"
    # design §10 字面 metadata = {source_type, tags_count}
    assert set(ev["metadata"].keys()) == {"source_type", "tags_count"}
    assert ev["metadata"]["source_type"] == "manual"
    assert ev["metadata"]["tags_count"] == 2
    assert ev["target_type"] == "industry_news"
    assert ev["project_id"] is None  # M14 全局豁免


async def test_link_node_activity_log_metadata_matches_design(auth_client, make_user, monkeypatch):
    """R2 P1-2 立修：design §10 link metadata 必须含 node_id 字面（实装额外含 news_title）。"""
    from api.services import industry_news_service as mod
    from api.services.activity_log_service import write_event as real_write_event

    captured: list[dict] = []

    async def fake(**kwargs):
        if kwargs.get("action_type") == "link":
            captured.append(kwargs)
        else:
            await real_write_event(**kwargs)

    monkeypatch.setattr(mod, "write_event", fake)
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="x")
    r = await auth_client.post("/api/news", json={"title": "t"}, headers=_bearer(user.id))
    news_id = r.json()["id"]
    r = await auth_client.post(
        f"/api/news/{news_id}/links",
        json={"node_id": nid},
        headers=_bearer(user.id),
    )
    assert r.status_code == 201
    assert len(captured) == 1
    ev = captured[0]
    assert ev["action_type"] == "link"
    assert ev["target_type"] == "news_node_link"
    assert "node_id" in ev["metadata"]
    assert ev["metadata"]["node_id"] == nid


# ─────────────── M14-source_type 服务端强制（R2 P1-4）───────────────


async def test_create_news_ignores_user_supplied_source_type(auth_client, make_user):
    """R2 P1-4 立修 design §3 灰区 1 字面：service 层拒绝非 manual；用户传 source_type='rss' 被静默 fallback 到 manual。"""
    user = await make_user()
    r = await auth_client.post(
        "/api/news", json={"title": "t", "source_type": "rss"}, headers=_bearer(user.id)
    )
    assert r.status_code == 201
    assert r.json()["source_type"] == "manual"


async def test_update_news_silently_drops_source_type(auth_client, make_user):
    """R2 P1-4 立修：update 路径用户传 source_type='rss' 被 service 层 sanitize 滤掉。"""
    user = await make_user()
    r = await auth_client.post("/api/news", json={"title": "t"}, headers=_bearer(user.id))
    news_id = r.json()["id"]
    r = await auth_client.put(
        f"/api/news/{news_id}",
        json={"source_type": "rss", "title": "t2"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    assert r.json()["source_type"] == "manual"
    assert r.json()["title"] == "t2"


# ─────────────── 原 list_news_by_node 测试（保留）───────────────


async def test_list_news_by_node(auth_client, make_user):
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="x")
    r = await auth_client.post("/api/news", json={"title": "linked-news"}, headers=_bearer(user.id))
    news_id = r.json()["id"]
    await auth_client.post(
        f"/api/news/{news_id}/links",
        json={"node_id": nid},
        headers=_bearer(user.id),
    )
    await auth_client.post("/api/news", json={"title": "other"}, headers=_bearer(user.id))
    r = await auth_client.get(f"/api/nodes/{nid}/news", headers=_bearer(user.id))
    assert r.status_code == 200
    titles = [item["title"] for item in r.json()["items"]]
    assert titles == ["linked-news"]
