"""M01 子片 1 — POST /auth/refresh (G3, B10, A10-A13, L5)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from api.models.user import AuthAuditLog, RefreshToken, User


def _h(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def _login(auth_client, email: str, password: str) -> dict:
    r = await auth_client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


async def test_refresh_returns_new_access_token_and_writes_audit(
    auth_client, make_user, db_session
):
    user = await make_user(email="r1@example.com", password="hunter2hunter")
    body = await _login(auth_client, "r1@example.com", "hunter2hunter")
    refresh_raw = body["refresh_token"]

    r = await auth_client.post("/auth/refresh", json={"refresh_token": refresh_raw})
    assert r.status_code == 200
    new_body = r.json()
    assert new_body["token_type"] == "bearer"
    assert new_body["access_token"]
    assert "refresh_token" not in new_body  # spec: refresh 不轮换

    rt = (
        await db_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == _h(refresh_raw))
        )
    ).scalar_one_or_none()
    assert rt is not None
    assert rt.last_seen_at is not None

    logs = (
        (
            await db_session.execute(
                select(AuthAuditLog).where(
                    AuthAuditLog.user_id == user.id,
                    AuthAuditLog.action_type == "user.refresh_token",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(logs) == 1


async def test_refresh_with_garbage_token_returns_401(auth_client):
    r = await auth_client.post("/auth/refresh", json={"refresh_token": "garbage"})
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_refresh_token"


async def test_refresh_with_empty_token_returns_422(auth_client):
    r = await auth_client.post("/auth/refresh", json={"refresh_token": ""})
    assert r.status_code == 422


async def test_refresh_with_expired_token_returns_401_and_deletes_row(
    auth_client, make_user, db_session
):
    await make_user(email="r2@example.com", password="hunter2hunter")
    body = await _login(auth_client, "r2@example.com", "hunter2hunter")
    refresh_raw = body["refresh_token"]

    # 把 expires_at 推回过去
    await db_session.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == _h(refresh_raw))
        .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    )
    await db_session.flush()

    r = await auth_client.post("/auth/refresh", json={"refresh_token": refresh_raw})
    assert r.status_code == 401
    assert r.json()["code"] == "refresh_token_expired"

    rt = (
        await db_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == _h(refresh_raw))
        )
    ).scalar_one_or_none()
    assert rt is None


async def test_refresh_with_disabled_user_returns_401(auth_client, make_user, db_session):
    user = await make_user(email="r3@example.com", password="hunter2hunter")
    body = await _login(auth_client, "r3@example.com", "hunter2hunter")
    refresh_raw = body["refresh_token"]

    await db_session.execute(update(User).where(User.id == user.id).values(status="disabled"))
    await db_session.flush()

    r = await auth_client.post("/auth/refresh", json={"refresh_token": refresh_raw})
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_refresh_token"


async def test_refresh_with_token_invalidated_at_after_creation_returns_401(
    auth_client, make_user, db_session
):
    user = await make_user(email="r4@example.com", password="hunter2hunter")
    body = await _login(auth_client, "r4@example.com", "hunter2hunter")
    refresh_raw = body["refresh_token"]

    await db_session.execute(
        update(User)
        .where(User.id == user.id)
        .values(token_invalidated_at=datetime.now(UTC) + timedelta(seconds=10))
    )
    await db_session.flush()

    r = await auth_client.post("/auth/refresh", json={"refresh_token": refresh_raw})
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_refresh_token"
