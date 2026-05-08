"""M15 子片 4 — activity_stream_router e2e 端到端测试。

覆盖 design §7 1 endpoint + §8 三层权限：
- 401 unauth / 403 viewer 读（**首发"读权限 403"测试** / M02-M14 写 403 同思想横切到读）
- 404 non-member / cross-project member 读（cross-tenant 404 范式 / M02 元教训）
- 422 from_dt > to_dt → ActivityStreamInvalidFilterError 业务 code
- 200 owner / editor 读
- filter 各维度 + 分页 has_more + 全局事件不召回（M14 baseline-patch project_id=None）

M14 NEW "形态特殊不免除契约纪律"应用：list_for_team helper 形态特殊（无 project_id /
target_type 路径）design §3 已字面 disambiguation；本 sprint Router 不暴露端点（M20
sprint own）—— design §14.5 字面声明。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from api.auth.jwt_utils import encode_jwt
from api.models.project import ProjectMember


def _bearer(user_id) -> dict:
    return {"Authorization": f"Bearer {encode_jwt(user_id, extra_claims={'type': 'access'})}"}


async def _create_project(auth_client, user_id, name: str = "P1") -> str:
    r = await auth_client.post("/api/projects", json={"name": name}, headers=_bearer(user_id))
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ─────────────── M15-E2E-T1 owner 读成功 200 ───────────────


async def test_get_stream_owner_200(auth_client, make_user, db_session):
    user = await make_user()
    pid = await _create_project(auth_client, user.id)

    # 这条 activity_log 由 M02 创建项目时写入（M03+ service 调 write_event 当前 stub
    # 不入库；故 list_stream 真实只返回 0 行 — 我们直插一行测 endpoint 通路）
    from api.models.activity_log import ActivityLog

    db_session.add(
        ActivityLog(
            project_id=pid,
            user_id=user.id,
            action_type="project_created",
            target_type="project",
            target_id=str(pid),
            summary="创建了项目",
        )
    )
    await db_session.flush()

    r = await auth_client.get(f"/api/projects/{pid}/activity-stream", headers=_bearer(user.id))
    assert r.status_code == 200
    data = r.json()
    assert data["project_id"] == pid
    assert data["page"] == 1
    assert data["page_size"] == 50
    assert data["has_more"] is False
    assert len(data["items"]) == 1
    assert data["items"][0]["user_name"] == user.name
    assert data["items"][0]["action_type"] == "project_created"


# ─────────────── M15-E2E-T2 editor 读成功 200 ───────────────


async def test_get_stream_editor_200(auth_client, make_user, db_session):
    owner = await make_user()
    editor = await make_user()
    pid = await _create_project(auth_client, owner.id)
    db_session.add(ProjectMember(project_id=pid, user_id=editor.id, role="editor"))
    await db_session.flush()

    r = await auth_client.get(f"/api/projects/{pid}/activity-stream", headers=_bearer(editor.id))
    assert r.status_code == 200


# ─────────────── M15-E2E-T3 viewer 读 403（首发"读权限 403"测试）───────────────


async def test_get_stream_viewer_returns_403(auth_client, make_user, db_session):
    """C-5 候选 β：viewer 不可审计；M02-M14 11 模块写 403 思想横切到读 403。"""
    owner = await make_user()
    viewer = await make_user()
    pid = await _create_project(auth_client, owner.id)
    db_session.add(ProjectMember(project_id=pid, user_id=viewer.id, role="viewer"))
    await db_session.flush()

    r = await auth_client.get(f"/api/projects/{pid}/activity-stream", headers=_bearer(viewer.id))
    assert r.status_code == 403


# ─────────────── M15-E2E-T4 non-member 404（cross-tenant 范式 / M02 元教训）───────────────


async def test_get_stream_non_member_returns_404(auth_client, make_user):
    owner = await make_user()
    other = await make_user()
    pid = await _create_project(auth_client, owner.id)

    r = await auth_client.get(f"/api/projects/{pid}/activity-stream", headers=_bearer(other.id))
    assert r.status_code == 404


# ─────────────── M15-E2E-T5 unauthenticated 401 ───────────────


async def test_get_stream_unauth_returns_401(auth_client, make_user):
    user = await make_user()
    pid = await _create_project(auth_client, user.id)

    r = await auth_client.get(f"/api/projects/{pid}/activity-stream")
    assert r.status_code == 401


# ─────────────── M15-E2E-T6 cross-project member（M02 cross-tenant 主动复制）───────────────


async def test_get_stream_member_of_a_cannot_read_b(auth_client, make_user):
    user_a = await make_user()
    user_b = await make_user()
    _ = await _create_project(auth_client, user_a.id, name="A")
    pid_b = await _create_project(auth_client, user_b.id, name="B")

    # user_a 是 A 的 owner / 不是 B 的成员 → 读 B 的 stream → 404
    r = await auth_client.get(f"/api/projects/{pid_b}/activity-stream", headers=_bearer(user_a.id))
    assert r.status_code == 404


# ─────────────── M15-E2E-T7 from_dt > to_dt → 422 业务 code ───────────────


async def test_get_stream_invalid_filter_returns_422_business_code(auth_client, make_user):
    """R1 P1-1 立修 e2e 验证：响应 code = activity_stream_invalid_filter（非通用 422）。"""
    user = await make_user()
    pid = await _create_project(auth_client, user.id)

    now = datetime.now(UTC)
    earlier = now - timedelta(days=1)
    r = await auth_client.get(
        f"/api/projects/{pid}/activity-stream",
        params={"from_dt": now.isoformat(), "to_dt": earlier.isoformat()},
        headers=_bearer(user.id),
    )
    assert r.status_code == 422
    body = r.json()
    assert body.get("code") == "activity_stream_invalid_filter"


# ─────────────── M15-E2E-T8 filter action_type Enum ───────────────


async def test_get_stream_filter_action_type(auth_client, make_user, db_session):
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    from api.models.activity_log import ActivityLog

    db_session.add_all(
        [
            ActivityLog(
                project_id=pid,
                user_id=user.id,
                action_type="project_created",
                target_type="project",
                target_id=str(pid),
                summary="x",
            ),
            ActivityLog(
                project_id=pid,
                user_id=user.id,
                action_type="node_created",
                target_type="node",
                target_id=str(uuid4()),
                summary="y",
            ),
        ]
    )
    await db_session.flush()

    r = await auth_client.get(
        f"/api/projects/{pid}/activity-stream",
        params={"action_type": "node_created"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["action_type"] == "node_created"


# ─────────────── M15-E2E-T9 filter target_type Enum ───────────────


async def test_get_stream_filter_target_type(auth_client, make_user, db_session):
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    from api.models.activity_log import ActivityLog

    db_session.add_all(
        [
            ActivityLog(
                project_id=pid,
                user_id=user.id,
                action_type="project_created",
                target_type="project",
                target_id=str(pid),
                summary="x",
            ),
            ActivityLog(
                project_id=pid,
                user_id=user.id,
                action_type="node_created",
                target_type="node",
                target_id=str(uuid4()),
                summary="y",
            ),
        ]
    )
    await db_session.flush()

    r = await auth_client.get(
        f"/api/projects/{pid}/activity-stream",
        params={"target_type": "node"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["target_type"] == "node"


# ─────────────── M15-E2E-T10 filter user_id ───────────────


async def test_get_stream_filter_user_id(auth_client, make_user, db_session):
    owner = await make_user()
    editor = await make_user()
    pid = await _create_project(auth_client, owner.id)
    db_session.add(ProjectMember(project_id=pid, user_id=editor.id, role="editor"))
    from api.models.activity_log import ActivityLog

    db_session.add_all(
        [
            ActivityLog(
                project_id=pid,
                user_id=owner.id,
                action_type="project_created",
                target_type="project",
                target_id=str(pid),
                summary="o",
            ),
            ActivityLog(
                project_id=pid,
                user_id=editor.id,
                action_type="node_created",
                target_type="node",
                target_id=str(uuid4()),
                summary="e",
            ),
        ]
    )
    await db_session.flush()

    r = await auth_client.get(
        f"/api/projects/{pid}/activity-stream",
        params={"user_id": str(editor.id)},
        headers=_bearer(owner.id),
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["user_id"] == str(editor.id)


# ─────────────── M15-E2E-T11 分页 page=1 has_more=True ───────────────


async def test_get_stream_pagination_first_page_has_more(auth_client, make_user, db_session):
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    from api.models.activity_log import ActivityLog

    for _ in range(3):
        db_session.add(
            ActivityLog(
                project_id=pid,
                user_id=user.id,
                action_type="node_created",
                target_type="node",
                target_id=str(uuid4()),
                summary="x",
            )
        )
    await db_session.flush()

    r = await auth_client.get(
        f"/api/projects/{pid}/activity-stream",
        params={"page": 1, "page_size": 2},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert data["has_more"] is True
    assert len(data["items"]) == 2


async def test_get_stream_pagination_second_page_no_total(auth_client, make_user, db_session):
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    from api.models.activity_log import ActivityLog

    for _ in range(3):
        db_session.add(
            ActivityLog(
                project_id=pid,
                user_id=user.id,
                action_type="node_created",
                target_type="node",
                target_id=str(uuid4()),
                summary="x",
            )
        )
    await db_session.flush()

    r = await auth_client.get(
        f"/api/projects/{pid}/activity-stream",
        params={"page": 2, "page_size": 2},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] is None  # D-2: 后续 page total=None
    assert data["has_more"] is False  # 3 items total / page 2 returns 1 < 2 → no more


# ─────────────── M15-E2E-T12 全局事件不召回（M14 baseline-patch project_id=None）───────────────


async def test_get_stream_does_not_return_global_events(auth_client, make_user, db_session):
    """M14 baseline-patch 实证：news_* 事件 project_id=None；list_stream 强 project_id 过滤
    天然不召回（design §3 + §9 字面）。"""
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    from api.models.activity_log import ActivityLog

    db_session.add_all(
        [
            ActivityLog(
                project_id=pid,
                user_id=user.id,
                action_type="project_created",
                target_type="project",
                target_id=str(pid),
                summary="proj",
            ),
            ActivityLog(
                project_id=None,  # M14 全局
                user_id=user.id,
                action_type="news_created",
                target_type="industry_news",
                target_id=str(uuid4()),
                summary="news",
            ),
        ]
    )
    await db_session.flush()

    r = await auth_client.get(f"/api/projects/{pid}/activity-stream", headers=_bearer(user.id))
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["target_type"] == "project"
