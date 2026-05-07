"""M01 子片 2 — PATCH /auth/me (G5, G6, C7-C10, I2, B11-B12, L6-L7)."""

from __future__ import annotations

import hashlib

from sqlalchemy import select

from api.auth.jwt_utils import encode_jwt
from api.auth.password import verify_password
from api.models.user import AuthAuditLog, RefreshToken


def _h(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _bearer(user_id) -> dict:
    token = encode_jwt(user_id, extra_claims={"type": "access"})
    return {"Authorization": f"Bearer {token}"}


# ────────────────── G5 改 name ──────────────────


async def test_patch_me_change_name_bumps_version_and_writes_audit(
    auth_client, make_user, db_session
):
    user = await make_user(email="n1@example.com", name="Old Name")

    r = await auth_client.patch(
        "/auth/me",
        json={"expected_version": 1, "name": "New Name"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "New Name"
    assert body["version"] == 2

    await db_session.refresh(user)
    assert user.name == "New Name"
    assert user.version == 2

    logs = (
        (
            await db_session.execute(
                select(AuthAuditLog).where(
                    AuthAuditLog.user_id == user.id,
                    AuthAuditLog.action_type == "user.profile_update",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(logs) == 1
    assert logs[0].metadata_["changed_fields"] == ["name"]


async def test_patch_me_does_not_revoke_tokens_on_name_change(auth_client, make_user, db_session):
    user = await make_user(email="n2@example.com", password="hunter2hunter")
    login = await auth_client.post(
        "/auth/login", json={"email": "n2@example.com", "password": "hunter2hunter"}
    )
    refresh_raw = login.json()["refresh_token"]

    r = await auth_client.patch(
        "/auth/me",
        json={"expected_version": 1, "name": "Renamed"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200

    rt = (
        await db_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == _h(refresh_raw))
        )
    ).scalar_one_or_none()
    assert rt is not None  # name change does NOT revoke


# ────────────────── G6 改密码 ──────────────────


async def test_patch_me_change_password_revokes_tokens_and_writes_2_audits(
    auth_client, make_user, db_session
):
    user = await make_user(email="p1@example.com", password="oldsecret123")
    login = await auth_client.post(
        "/auth/login", json={"email": "p1@example.com", "password": "oldsecret123"}
    )
    refresh_raw = login.json()["refresh_token"]

    r = await auth_client.patch(
        "/auth/me",
        json={
            "expected_version": 1,
            "old_password": "oldsecret123",
            "new_password": "newsecret456",
        },
        headers=_bearer(user.id),
    )
    assert r.status_code == 200, r.text
    assert r.json()["version"] == 2

    await db_session.refresh(user)
    assert verify_password("newsecret456", user.password_hash)
    assert user.token_invalidated_at is not None

    rts = (
        (
            await db_session.execute(
                select(RefreshToken).where(RefreshToken.token_hash == _h(refresh_raw))
            )
        )
        .scalars()
        .all()
    )
    assert rts == []  # I2: tokens revoked

    logs = (
        (await db_session.execute(select(AuthAuditLog).where(AuthAuditLog.user_id == user.id)))
        .scalars()
        .all()
    )
    action_types = {log.action_type for log in logs}
    assert "user.password_change" in action_types
    assert "user.all_tokens_revoked" in action_types


async def test_patch_me_old_password_wrong_returns_400(auth_client, make_user, db_session):
    user = await make_user(email="p2@example.com", password="rightpass123")
    r = await auth_client.patch(
        "/auth/me",
        json={
            "expected_version": 1,
            "old_password": "WRONG",
            "new_password": "newsecret456",
        },
        headers=_bearer(user.id),
    )
    assert r.status_code == 400
    assert r.json()["code"] == "old_password_mismatch"

    await db_session.refresh(user)
    assert verify_password("rightpass123", user.password_hash)  # 密码未变


async def test_patch_me_new_password_too_short_returns_422(auth_client, make_user):
    user = await make_user(email="p3@example.com", password="rightpass123")
    r = await auth_client.patch(
        "/auth/me",
        json={
            "expected_version": 1,
            "old_password": "rightpass123",
            "new_password": "short",
        },
        headers=_bearer(user.id),
    )
    assert r.status_code == 422


async def test_patch_me_new_password_without_old_password_returns_400(auth_client, make_user):
    user = await make_user(email="p4@example.com", password="rightpass123")
    r = await auth_client.patch(
        "/auth/me",
        json={"expected_version": 1, "new_password": "newsecret456"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 400


# ────────────────── 乐观锁 + 校验 ──────────────────


async def test_patch_me_missing_expected_version_returns_422(auth_client, make_user):
    user = await make_user()
    r = await auth_client.patch("/auth/me", json={"name": "X"}, headers=_bearer(user.id))
    assert r.status_code == 422


async def test_patch_me_stale_expected_version_returns_409(auth_client, make_user):
    user = await make_user()
    r = await auth_client.patch(
        "/auth/me",
        json={"expected_version": 99, "name": "X"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 409
    assert r.json()["code"] == "version_conflict"


async def test_patch_me_extra_field_returns_422(auth_client, make_user):
    user = await make_user()
    r = await auth_client.patch(
        "/auth/me",
        json={"expected_version": 1, "nickname": "X"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 422


async def test_patch_me_empty_body_returns_400(auth_client, make_user):
    user = await make_user()
    r = await auth_client.patch("/auth/me", json={"expected_version": 1}, headers=_bearer(user.id))
    # 至少需要 name 或 new_password 之一
    assert r.status_code in (400, 422)


# ────────────────── C9 事务原子性 ──────────────────


async def test_patch_me_password_change_revoke_failure_rolls_back_all(
    isolated_client, isolated_db, monkeypatch
):
    """C9（子片 5 isolated_db fixture 转 PASS）：

    mock revoke_all_for_user 抛异常 → 事务回滚，users.password_hash 不变 +
    token_invalidated_at 不变 + version 不 bump + refresh_tokens 不删 +
    auth_audit_log password_change/all_tokens_revoked 都不写。
    """
    from api.auth.password import hash_password, verify_password
    from api.models.user import User

    user = User(
        email="c9-iso@example.com",
        name="C9",
        password_hash=hash_password("oldsecret123"),
        role="user",
        status="active",
        failed_login_count=0,
        version=1,
    )
    isolated_db.add(user)
    await isolated_db.commit()
    await isolated_db.refresh(user)
    user_id = user.id
    original_hash = user.password_hash

    login = await isolated_client.post(
        "/auth/login",
        json={"email": "c9-iso@example.com", "password": "oldsecret123"},
    )
    assert login.status_code == 200
    refresh_raw = login.json()["refresh_token"]

    from api.services.auth_service import get_auth_service

    svc = get_auth_service()

    async def _boom(*args, **kwargs):
        raise RuntimeError("simulated DB failure mid-transaction")

    monkeypatch.setattr(svc.tokens, "revoke_all_for_user", _boom)

    r = await isolated_client.patch(
        "/auth/me",
        json={
            "expected_version": 1,
            "old_password": "oldsecret123",
            "new_password": "newsecret456",
        },
        headers=_bearer(user_id),
    )
    assert r.status_code == 500

    # 真实 rollback 后重读
    isolated_db.expire_all()
    fresh = (await isolated_db.execute(select(User).where(User.id == user_id))).scalar_one()
    assert fresh.password_hash == original_hash
    assert fresh.token_invalidated_at is None
    assert fresh.version == 1
    assert verify_password("oldsecret123", fresh.password_hash)

    rt = (
        await isolated_db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == _h(refresh_raw))
        )
    ).scalar_one_or_none()
    assert rt is not None

    audit_rows = (
        (
            await isolated_db.execute(
                select(AuthAuditLog).where(
                    AuthAuditLog.user_id == user_id,
                    AuthAuditLog.action_type.in_(
                        ["user.password_change", "user.all_tokens_revoked"]
                    ),
                )
            )
        )
        .scalars()
        .all()
    )
    assert audit_rows == []
