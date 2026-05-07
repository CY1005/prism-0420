"""M01 子片 2 — PATCH /auth/me (G5, G6, C7-C10, I2, B11-B12, L6-L7)."""

from __future__ import annotations

import hashlib

import pytest
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


@pytest.mark.xfail(
    reason=(
        "C9 atomicity 测试需独立连接 fixture：当前 conftest 的 savepoint 模式"
        "+ 服务层 db.commit()/rollback() 互动后会进入 MissingGreenlet 状态。"
        "子片 5 引入专属 'isolated_db' fixture 实证后转 PASS。"
    ),
    strict=False,
)
async def test_patch_me_password_change_revoke_failure_rolls_back_all(
    auth_client, make_user, db_session, monkeypatch
):
    """C9：mock revoke_all_for_user 抛异常 → 事务回滚，audit 不写、refresh_token 不删。"""
    user = await make_user(email="c9@example.com", password="oldsecret123")

    login = await auth_client.post(
        "/auth/login", json={"email": "c9@example.com", "password": "oldsecret123"}
    )
    refresh_raw = login.json()["refresh_token"]

    from api.services.auth_service import get_auth_service

    svc = get_auth_service()

    async def _boom(*args, **kwargs):
        raise RuntimeError("simulated DB failure mid-transaction")

    monkeypatch.setattr(svc.tokens, "revoke_all_for_user", _boom)

    r = await auth_client.patch(
        "/auth/me",
        json={
            "expected_version": 1,
            "old_password": "oldsecret123",
            "new_password": "newsecret456",
        },
        headers=_bearer(user.id),
    )
    assert r.status_code == 500

    await db_session.rollback()

    rt = (
        await db_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == _h(refresh_raw))
        )
    ).scalar_one_or_none()
    assert rt is not None  # token 未撤销

    audit_rows = (
        (
            await db_session.execute(
                select(AuthAuditLog).where(
                    AuthAuditLog.user_id == user.id,
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
