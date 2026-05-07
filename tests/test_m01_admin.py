"""M01 子片 3 — admin endpoints (G7-G11 / B3-B7 / P5-P8 / I1 / L8-L10)."""

from __future__ import annotations

import hashlib
from uuid import uuid4

from sqlalchemy import select

from api.auth.jwt_utils import encode_jwt
from api.models.user import AuthAuditLog, RefreshToken


def _h(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _bearer(user_id) -> dict:
    return {"Authorization": f"Bearer {encode_jwt(user_id, extra_claims={'type': 'access'})}"}


# ───────────── POST /auth/users ─────────────


async def test_admin_create_user_returns_201_and_writes_audit(auth_client, make_user, db_session):
    admin = await make_user(role="platform_admin", email="a1@example.com")

    r = await auth_client.post(
        "/auth/users",
        json={
            "email": "newbie@example.com",
            "name": "Newbie",
            "password": "newbiepass123",
            "role": "user",
        },
        headers=_bearer(admin.id),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == "newbie@example.com"
    assert body["role"] == "user"

    logs = (
        (
            await db_session.execute(
                select(AuthAuditLog).where(AuthAuditLog.action_type == "user.admin_create")
            )
        )
        .scalars()
        .all()
    )
    assert any(log.metadata_.get("created_by") == str(admin.id) for log in logs)


async def test_admin_create_user_duplicate_email_returns_409(auth_client, make_user):
    admin = await make_user(role="platform_admin")
    await make_user(email="taken@example.com")

    r = await auth_client.post(
        "/auth/users",
        json={
            "email": "taken@example.com",
            "name": "Dup",
            "password": "duppass123",
            "role": "user",
        },
        headers=_bearer(admin.id),
    )
    assert r.status_code == 409
    assert r.json()["code"] == "email_already_exists"


async def test_admin_create_user_weak_password_returns_422(auth_client, make_user):
    admin = await make_user(role="platform_admin")
    r = await auth_client.post(
        "/auth/users",
        json={"email": "weak@example.com", "name": "W", "password": "short", "role": "user"},
        headers=_bearer(admin.id),
    )
    assert r.status_code == 422


async def test_admin_create_user_invalid_role_returns_422(auth_client, make_user):
    admin = await make_user(role="platform_admin")
    r = await auth_client.post(
        "/auth/users",
        json={
            "email": "x@example.com",
            "name": "X",
            "password": "okpass123",
            "role": "super_admin",
        },
        headers=_bearer(admin.id),
    )
    assert r.status_code == 422


async def test_non_admin_cannot_create_user_returns_403(auth_client, make_user):
    user = await make_user(role="user")
    r = await auth_client.post(
        "/auth/users",
        json={"email": "x@example.com", "name": "X", "password": "okpass123", "role": "user"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "permission_denied"


# ───────────── GET /auth/users ─────────────


async def test_admin_list_users_returns_all(auth_client, make_user):
    admin = await make_user(role="platform_admin")
    await make_user(email="u1@example.com")
    await make_user(email="u2@example.com")

    r = await auth_client.get("/auth/users", headers=_bearer(admin.id))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 3
    emails = {u["email"] for u in body["users"]}
    assert {"u1@example.com", "u2@example.com"} <= emails


async def test_non_admin_cannot_list_users_returns_403(auth_client, make_user):
    user = await make_user(role="user")
    r = await auth_client.get("/auth/users", headers=_bearer(user.id))
    assert r.status_code == 403


# ───────────── PATCH /auth/users/{id} ─────────────


async def test_admin_update_role_writes_audit_and_bumps_version(auth_client, make_user, db_session):
    admin = await make_user(role="platform_admin")
    target = await make_user(email="t1@example.com", role="user")

    r = await auth_client.patch(
        f"/auth/users/{target.id}",
        json={"expected_version": 1, "role": "platform_admin"},
        headers=_bearer(admin.id),
    )
    assert r.status_code == 200
    assert r.json()["role"] == "platform_admin"
    assert r.json()["version"] == 2

    logs = (
        (
            await db_session.execute(
                select(AuthAuditLog).where(
                    AuthAuditLog.user_id == target.id,
                    AuthAuditLog.action_type == "user.admin_update_role",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(logs) == 1
    assert logs[0].metadata_["old_role"] == "user"
    assert logs[0].metadata_["new_role"] == "platform_admin"


async def test_admin_disable_target_revokes_tokens_and_writes_2_audits(
    auth_client, make_user, db_session
):
    """G10 + I1 + L10: 禁用 → token_invalidated_at + 撤销 + admin_update_status + all_tokens_revoked。"""
    admin = await make_user(role="platform_admin", email="adm@example.com")
    target = await make_user(email="dis@example.com", password="hunter2hunter")
    # 给 target 登录创建 refresh_token
    login = await auth_client.post(
        "/auth/login",
        json={"email": "dis@example.com", "password": "hunter2hunter"},
    )
    refresh_raw = login.json()["refresh_token"]

    r = await auth_client.patch(
        f"/auth/users/{target.id}",
        json={"expected_version": 1, "status": "disabled"},
        headers=_bearer(admin.id),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "disabled"

    await db_session.refresh(target)
    assert target.token_invalidated_at is not None
    assert target.status == "disabled"

    rt = (
        await db_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == _h(refresh_raw))
        )
    ).scalar_one_or_none()
    assert rt is None

    logs = (
        (await db_session.execute(select(AuthAuditLog).where(AuthAuditLog.user_id == target.id)))
        .scalars()
        .all()
    )
    action_types = {log.action_type for log in logs}
    assert "user.admin_update_status" in action_types
    assert "user.all_tokens_revoked" in action_types


async def test_admin_enable_disabled_user_does_not_revoke_again(auth_client, make_user, db_session):
    """G11: disabled→active 不触发 token revoke。"""
    admin = await make_user(role="platform_admin", email="adm2@example.com")
    target = await make_user(email="dis2@example.com", status_="disabled")

    r = await auth_client.patch(
        f"/auth/users/{target.id}",
        json={"expected_version": 1, "status": "active"},
        headers=_bearer(admin.id),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "active"

    revoke_logs = (
        (
            await db_session.execute(
                select(AuthAuditLog).where(
                    AuthAuditLog.user_id == target.id,
                    AuthAuditLog.action_type == "user.all_tokens_revoked",
                )
            )
        )
        .scalars()
        .all()
    )
    assert revoke_logs == []


async def test_admin_self_downgrade_returns_400(auth_client, make_user):
    admin = await make_user(role="platform_admin", email="self@example.com")
    r = await auth_client.patch(
        f"/auth/users/{admin.id}",
        json={"expected_version": 1, "role": "user"},
        headers=_bearer(admin.id),
    )
    assert r.status_code == 400
    assert r.json()["code"] == "self_downgrade_forbidden"


async def test_admin_disable_last_admin_returns_400(auth_client, make_user):
    """P8: 系统只剩 1 active admin 时禁用他被拒。"""
    only_admin = await make_user(role="platform_admin", email="only@example.com")
    # 用 P2 internal token 触发 PATCH（admin 不能自己 disable，必须另一 admin 操作；
    # 为简化测试用 P2 模拟另一身份；但 require_admin 校验当前 user 是 admin。
    # 这里改用 admin 自己 disable：先建第二个 admin 测正常路径，对比单 admin 路径
    second_admin = await make_user(role="platform_admin", email="second@example.com")

    # 先把 second_admin 禁用，留 only_admin 为最后 active admin
    r1 = await auth_client.patch(
        f"/auth/users/{second_admin.id}",
        json={"expected_version": 1, "status": "disabled"},
        headers=_bearer(only_admin.id),
    )
    assert r1.status_code == 200

    # 现在 only_admin 是最后 active admin。再尝试由 only_admin 触发禁 only_admin
    # （自己禁自己）应该被 LastAdminProtectedError 拦
    r2 = await auth_client.patch(
        f"/auth/users/{only_admin.id}",
        json={"expected_version": 1, "status": "disabled"},
        headers=_bearer(only_admin.id),
    )
    assert r2.status_code == 400
    assert r2.json()["code"] == "last_admin_protected"


async def test_admin_update_nonexistent_user_returns_404(auth_client, make_user):
    admin = await make_user(role="platform_admin")
    r = await auth_client.patch(
        f"/auth/users/{uuid4()}",
        json={"expected_version": 1, "role": "user"},
        headers=_bearer(admin.id),
    )
    assert r.status_code == 404
    assert r.json()["code"] == "user_not_found"


async def test_admin_update_invalid_uuid_returns_422(auth_client, make_user):
    admin = await make_user(role="platform_admin")
    r = await auth_client.patch(
        "/auth/users/not-a-uuid",
        json={"expected_version": 1, "role": "user"},
        headers=_bearer(admin.id),
    )
    assert r.status_code == 422


async def test_admin_update_stale_version_returns_409(auth_client, make_user):
    admin = await make_user(role="platform_admin")
    target = await make_user(email="stale@example.com")
    r = await auth_client.patch(
        f"/auth/users/{target.id}",
        json={"expected_version": 99, "role": "platform_admin"},
        headers=_bearer(admin.id),
    )
    assert r.status_code == 409
    assert r.json()["code"] == "version_conflict"


async def test_non_admin_patch_other_user_returns_403(auth_client, make_user):
    user = await make_user(role="user")
    other = await make_user(email="other@example.com")
    r = await auth_client.patch(
        f"/auth/users/{other.id}",
        json={"expected_version": 1, "role": "platform_admin"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 403
