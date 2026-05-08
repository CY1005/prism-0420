"""M10 子片 3 — Router + 3 endpoints 端到端测试（纯读 viewer-only）。

覆盖 design §7 3 endpoints + §8 三层权限 + 401/404/422 + golden +
**M07 元教训防御 actionable**：cross-tenant 404 + 401 unauth + viewer 读 200
（M10 无写端点 → viewer 写测试不适用；M02-M07 范式）。
"""

from __future__ import annotations

from api.auth.jwt_utils import encode_jwt
from api.models.dimension_record import DimensionRecord


def _bearer(user_id) -> dict:
    return {"Authorization": f"Bearer {encode_jwt(user_id, extra_claims={'type': 'access'})}"}


async def _create_project(auth_client, user_id, name: str = "P1") -> str:
    r = await auth_client.post("/api/projects", json={"name": name}, headers=_bearer(user_id))
    assert r.status_code == 201
    return r.json()["id"]


async def _create_node(
    auth_client, user_id, pid: str, name: str = "n", node_type: str = "file"
) -> str:
    r = await auth_client.post(
        f"/api/projects/{pid}/nodes",
        json={"name": name, "type": node_type},
        headers=_bearer(user_id),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ─────────────── G1: golden read ───────────────


async def test_overview_returns_tree_and_stats(auth_client, make_user, db_session, make_dim_type):
    user = await make_user(email="m10-cc@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid)
    t1 = await make_dim_type(key="t1", project_id=pid, enabled=True)
    db_session.add(
        DimensionRecord(
            node_id=nid,
            project_id=pid,
            dimension_type_id=t1,
            content={"x": "y"},
            created_by=user.id,
            updated_by=user.id,
        )
    )
    await db_session.commit()

    r = await auth_client.get(f"/api/projects/{pid}/overview", headers=_bearer(user.id))
    assert r.status_code == 200
    body = r.json()
    assert body["project_id"] == pid
    assert len(body["tree"]) == 1
    assert body["tree"][0]["completion_rate"] == 1.0
    assert body["stats"]["total_nodes"] == 1
    assert body["stats"]["fully_complete_nodes"] == 1


async def test_overview_stats_lightweight(auth_client, make_user, make_dim_type):
    user = await make_user(email="m10-stats@example.com")
    pid = await _create_project(auth_client, user.id)
    await _create_node(auth_client, user.id, pid)
    await make_dim_type(key="t1", project_id=pid, enabled=True)

    r = await auth_client.get(f"/api/projects/{pid}/overview/stats", headers=_bearer(user.id))
    assert r.status_code == 200
    body = r.json()
    assert "stats" in body
    assert "tree" not in body  # lightweight 不返 tree


# M10 节点级 completion endpoint 走 M04 dimension_router 的 /completion 路径
# （避免双注册路径冲突；M10 service.get_node_completion 保留作内部接口）。
# 详 design §7 子片 5 audit 回写。


# ─────────────── G2: 错误码 ───────────────


async def test_overview_no_dimensions_returns_422(auth_client, make_user):
    """分母=0 → OVERVIEW_NO_DIMENSIONS 422。"""
    user = await make_user(email="m10-nodim@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.get(f"/api/projects/{pid}/overview", headers=_bearer(user.id))
    assert r.status_code == 422
    assert r.json()["code"] == "overview_no_dimensions"


# ─────────────── G3: tenant + viewer + 401（M10 无写端点 → viewer 写测试不适用）───────────────


async def test_overview_cross_tenant_returns_404(auth_client, make_user):
    """B 用户无 A 项目权限 → 404 不暴露存在性（M02 范式）。"""
    userA = await make_user(email="m10-xtA@example.com")
    userB = await make_user(email="m10-xtB@example.com")
    pidA = await _create_project(auth_client, userA.id)

    r = await auth_client.get(f"/api/projects/{pidA}/overview", headers=_bearer(userB.id))
    assert r.status_code == 404
    assert r.json()["code"] == "project_not_found"


async def test_overview_viewer_read_succeeds(auth_client, make_user, db_session, make_dim_type):
    """**M10 viewer-only 模块**：viewer 读全景图属正常权限（与 M02-M08 写端点 viewer 403 对照）。"""
    from api.models.project import MemberRole, ProjectMember

    userA = await make_user(email="m10-vA@example.com")
    userB = await make_user(email="m10-vB@example.com")
    pidA = await _create_project(auth_client, userA.id)
    await _create_node(auth_client, userA.id, pidA)
    await make_dim_type(key="t1", project_id=pidA, enabled=True)

    db_session.add(ProjectMember(project_id=pidA, user_id=userB.id, role=MemberRole.VIEWER.value))
    await db_session.commit()

    r = await auth_client.get(f"/api/projects/{pidA}/overview", headers=_bearer(userB.id))
    assert r.status_code == 200, "viewer 读全景图应正常 200"


async def test_overview_unauthenticated_returns_401(auth_client, make_user):
    user = await make_user(email="m10-401@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.get(f"/api/projects/{pid}/overview")
    assert r.status_code == 401
