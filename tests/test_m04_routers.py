"""M04 子片 4 — Router + 6 endpoints 端到端测试。

覆盖 design §7 6 endpoints + §8 三层权限 + 401/403/404/409/422 + golden + tenant。

需 seed dimension_types + project_dimension_configs 直接走 DB（M02 sprint 期未暴露
M04 用到的"项目级启用"管理 endpoint，本期 router test 通过 fixture seed）。
"""

from __future__ import annotations

import pytest_asyncio

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


@pytest_asyncio.fixture(loop_scope="session")
async def seed_dim_type(db_session):
    """fixture: 直接 DB 建 dimension_types + 启用配置（M02 期无 API endpoint）。"""
    from api.models.project import DimensionType, ProjectDimensionConfig

    async def _make(*, project_id, key: str, enabled: bool = True, sort_order: int = 0) -> int:
        dt = DimensionType(key=key, name=f"DT-{key}", icon="FileText")
        db_session.add(dt)
        await db_session.flush()
        db_session.add(
            ProjectDimensionConfig(
                project_id=project_id,
                dimension_type_id=dt.id,
                enabled=enabled,
                sort_order=sort_order,
            )
        )
        await db_session.flush()
        return dt.id

    yield _make


# ─────────────── G1: create dimension (201) ───────────────


async def test_create_dimension_returns_201(auth_client, make_user, seed_dim_type):
    user = await make_user(email="m04-c@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")
    type_id = await seed_dim_type(project_id=pid, key="g1")

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/dimensions",
        json={"dimension_type_id": type_id, "content": {"description": "hello"}},
        headers=_bearer(user.id),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["dimension_type_id"] == type_id
    assert body["content"] == {"description": "hello"}
    assert body["version"] == 1


async def test_create_dimension_disabled_type_returns_422(auth_client, make_user, seed_dim_type):
    user = await make_user(email="m04-disabled@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")
    type_id = await seed_dim_type(project_id=pid, key="g1_off", enabled=False)

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/dimensions",
        json={"dimension_type_id": type_id, "content": {}},
        headers=_bearer(user.id),
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "dimension_type_disabled"


async def test_create_dimension_unconfigured_type_returns_422(auth_client, make_user, db_session):
    """pdc 不存在 → DimensionTypeDisabledError (pdc-existence-strict)."""
    from api.models.project import DimensionType

    user = await make_user(email="m04-noconfig@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")
    dt = DimensionType(key="g1_unc", name="DT-g1_unc")
    db_session.add(dt)
    await db_session.flush()

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/dimensions",
        json={"dimension_type_id": dt.id, "content": {}},
        headers=_bearer(user.id),
    )
    assert r.status_code == 422
    assert r.json()["code"] == "dimension_type_disabled"


async def test_create_dimension_unknown_type_returns_404(auth_client, make_user):
    user = await make_user(email="m04-unktype@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/dimensions",
        json={"dimension_type_id": 999999, "content": {}},
        headers=_bearer(user.id),
    )
    assert r.status_code == 404
    assert r.json()["code"] == "dimension_type_not_found"


async def test_create_dimension_duplicate_returns_409(auth_client, make_user, seed_dim_type):
    user = await make_user(email="m04-dup@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")
    type_id = await seed_dim_type(project_id=pid, key="g1_dup")

    body = {"dimension_type_id": type_id, "content": {"a": 1}}
    r1 = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/dimensions",
        json=body,
        headers=_bearer(user.id),
    )
    assert r1.status_code == 201
    r2 = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/dimensions",
        json=body,
        headers=_bearer(user.id),
    )
    assert r2.status_code == 409
    assert r2.json()["code"] == "dimension_duplicate"


# ─────────────── G2: list_by_node + enabled types ───────────────


async def test_list_dimensions_returns_items_and_enabled_types(
    auth_client, make_user, seed_dim_type
):
    user = await make_user(email="m04-list@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")
    t1 = await seed_dim_type(project_id=pid, key="lst1", sort_order=1)
    await seed_dim_type(project_id=pid, key="lst2", sort_order=2)

    # 创建一条记录但不创建第二条
    await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/dimensions",
        json={"dimension_type_id": t1, "content": {"x": 1}},
        headers=_bearer(user.id),
    )

    r = await auth_client.get(
        f"/api/projects/{pid}/nodes/{nid}/dimensions", headers=_bearer(user.id)
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["dimension_type_id"] == t1
    keys = [t["key"] for t in body["enabled_dimension_types"]]
    # 项目 seed 还有 default（M02 sprint placeholder）+ lst1 + lst2
    assert "lst1" in keys and "lst2" in keys


# ─────────────── G3: get_one + 404 ───────────────


async def test_get_one_returns_record(auth_client, make_user, seed_dim_type):
    user = await make_user(email="m04-getone@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")
    type_id = await seed_dim_type(project_id=pid, key="getone")
    await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/dimensions",
        json={"dimension_type_id": type_id, "content": {"a": 1}},
        headers=_bearer(user.id),
    )
    r = await auth_client.get(
        f"/api/projects/{pid}/nodes/{nid}/dimensions/{type_id}", headers=_bearer(user.id)
    )
    assert r.status_code == 200
    assert r.json()["dimension_type_id"] == type_id


async def test_get_one_not_found_returns_404(auth_client, make_user):
    user = await make_user(email="m04-getnf@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")
    r = await auth_client.get(
        f"/api/projects/{pid}/nodes/{nid}/dimensions/99999", headers=_bearer(user.id)
    )
    assert r.status_code == 404


# ─────────────── G4: update with optimistic lock ───────────────


async def test_update_dimension_increments_version(auth_client, make_user, seed_dim_type):
    user = await make_user(email="m04-upd@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")
    type_id = await seed_dim_type(project_id=pid, key="upd")
    create = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/dimensions",
        json={"dimension_type_id": type_id, "content": {}},
        headers=_bearer(user.id),
    )
    assert create.json()["version"] == 1

    r = await auth_client.put(
        f"/api/projects/{pid}/nodes/{nid}/dimensions/{type_id}",
        json={"content": {"x": 2}, "expected_version": 1},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    assert r.json()["version"] == 2
    assert r.json()["content"] == {"x": 2}


async def test_update_dimension_version_conflict_returns_409(auth_client, make_user, seed_dim_type):
    user = await make_user(email="m04-upd-conf@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")
    type_id = await seed_dim_type(project_id=pid, key="updc")
    await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/dimensions",
        json={"dimension_type_id": type_id, "content": {}},
        headers=_bearer(user.id),
    )
    r = await auth_client.put(
        f"/api/projects/{pid}/nodes/{nid}/dimensions/{type_id}",
        json={"content": {"x": 1}, "expected_version": 999},
        headers=_bearer(user.id),
    )
    assert r.status_code == 409


async def test_update_dimension_not_found_returns_404(auth_client, make_user, seed_dim_type):
    user = await make_user(email="m04-upd-nf@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")
    type_id = await seed_dim_type(project_id=pid, key="upd_nf")

    r = await auth_client.put(
        f"/api/projects/{pid}/nodes/{nid}/dimensions/{type_id}",
        json={"content": {}, "expected_version": 1},
        headers=_bearer(user.id),
    )
    assert r.status_code == 404


# ─────────────── G5: delete (204) ───────────────


async def test_delete_dimension_returns_204(auth_client, make_user, seed_dim_type):
    user = await make_user(email="m04-del@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")
    type_id = await seed_dim_type(project_id=pid, key="del")
    await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/dimensions",
        json={"dimension_type_id": type_id, "content": {}},
        headers=_bearer(user.id),
    )
    r = await auth_client.delete(
        f"/api/projects/{pid}/nodes/{nid}/dimensions/{type_id}", headers=_bearer(user.id)
    )
    assert r.status_code == 204
    # 再查应 404
    r2 = await auth_client.get(
        f"/api/projects/{pid}/nodes/{nid}/dimensions/{type_id}", headers=_bearer(user.id)
    )
    assert r2.status_code == 404


# ─────────────── G6: completion ───────────────


async def test_completion_returns_filled_and_enabled_count(auth_client, make_user, seed_dim_type):
    user = await make_user(email="m04-comp@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")
    t1 = await seed_dim_type(project_id=pid, key="comp1")
    await seed_dim_type(project_id=pid, key="comp2")
    await seed_dim_type(project_id=pid, key="comp3", enabled=False)

    # 填一条
    await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/dimensions",
        json={"dimension_type_id": t1, "content": {}},
        headers=_bearer(user.id),
    )

    r = await auth_client.get(
        f"/api/projects/{pid}/nodes/{nid}/completion", headers=_bearer(user.id)
    )
    assert r.status_code == 200
    body = r.json()
    # M02 seed 1 个 default 无 pdc; comp1+comp2 enabled, comp3 disabled
    assert body["enabled_count"] == 2
    assert body["filled_count"] == 1
    assert body["completion_rate"] == 0.5


# ─────────────── 权限：401 / 403 / cross-tenant ───────────────


async def test_create_dimension_without_token_returns_401(auth_client, make_user):
    user = await make_user(email="m04-401@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/dimensions",
        json={"dimension_type_id": 1, "content": {}},
    )
    assert r.status_code == 401


async def test_create_dimension_non_member_returns_404(auth_client, make_user, seed_dim_type):
    """非 member 不应能拿到 project 信息 → 404 (design §8 不暴露 forbidden)."""
    owner = await make_user(email="m04-owner@example.com")
    intruder = await make_user(email="m04-intruder@example.com")
    pid = await _create_project(auth_client, owner.id)
    nid = await _create_node(auth_client, owner.id, pid, name="A")
    type_id = await seed_dim_type(project_id=pid, key="intr")

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/dimensions",
        json={"dimension_type_id": type_id, "content": {}},
        headers=_bearer(intruder.id),
    )
    assert r.status_code == 404
    assert r.json()["code"] == "project_not_found"


async def test_update_dimension_blocks_cross_tenant_node_id(auth_client, make_user, seed_dim_type):
    """C9.2 端到端：cross-tenant node_id 攻击通过 router 也应被 service 层拒。"""
    user = await make_user(email="m04-x@example.com")
    pidA = await _create_project(auth_client, user.id, "A")
    pidB = await _create_project(auth_client, user.id, "B")
    nid_A = await _create_node(auth_client, user.id, pidA, name="A")
    type_id_B = await seed_dim_type(project_id=pidB, key="x")

    # 在 pidB 路径下用 pidA 的 node_id：service _check_node_belongs_to_project 拦
    r = await auth_client.put(
        f"/api/projects/{pidB}/nodes/{nid_A}/dimensions/{type_id_B}",
        json={"content": {}, "expected_version": 1},
        headers=_bearer(user.id),
    )
    assert r.status_code == 404
    assert r.json()["code"] == "dimension_not_found"


async def test_get_one_invalid_uuid_returns_422(auth_client, make_user):
    user = await make_user(email="m04-422@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.get(
        f"/api/projects/{pid}/nodes/not-a-uuid/dimensions/1", headers=_bearer(user.id)
    )
    assert r.status_code == 422


# ─────────────── R2 立修配套：B6.x enabled_dimension_types 含义自洽 ───────────────


async def test_list_dimensions_excludes_disabled_types(auth_client, make_user, seed_dim_type):
    """R2 P1 立修 B6.x：``enabled_dimension_types`` 字段必须仅含 enabled=True 的 pdc。

    禁用配置不应通过 M04 list endpoint 暴露（design §7 字面 + 字段名语义自洽）。
    """
    user = await make_user(email="m04-listoff@example.com")
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid, name="A")
    await seed_dim_type(project_id=pid, key="enabled_t")
    await seed_dim_type(project_id=pid, key="disabled_t", enabled=False)

    r = await auth_client.get(
        f"/api/projects/{pid}/nodes/{nid}/dimensions", headers=_bearer(user.id)
    )
    assert r.status_code == 200
    keys = [t["key"] for t in r.json()["enabled_dimension_types"]]
    assert "enabled_t" in keys
    assert "disabled_t" not in keys, "禁用的 pdc 配置不应出现在 enabled_dimension_types 中"
    # 同时验证返回的 type 全部 enabled=True
    assert all(t["enabled"] is True for t in r.json()["enabled_dimension_types"])
