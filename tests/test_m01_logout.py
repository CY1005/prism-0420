"""M01 子片 1 — POST /auth/logout (G4, L4)."""

from __future__ import annotations

import hashlib

from sqlalchemy import select

from api.models.user import AuthAuditLog, RefreshToken


def _h(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def _login(auth_client, email: str, password: str) -> dict:
    r = await auth_client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    return r.json()


async def test_logout_deletes_refresh_token_and_writes_audit(auth_client, make_user, db_session):
    user = await make_user(email="o1@example.com", password="hunter2hunter")
    body = await _login(auth_client, "o1@example.com", "hunter2hunter")
    refresh_raw = body["refresh_token"]

    r = await auth_client.post("/auth/logout", json={"refresh_token": refresh_raw})
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

    rt = (
        await db_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == _h(refresh_raw))
        )
    ).scalar_one_or_none()
    assert rt is None

    logs = (
        (
            await db_session.execute(
                select(AuthAuditLog).where(
                    AuthAuditLog.user_id == user.id,
                    AuthAuditLog.action_type == "user.logout",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(logs) == 1


async def test_logout_with_unknown_token_still_returns_ok_no_audit(auth_client, db_session):
    r = await auth_client.post("/auth/logout", json={"refresh_token": "ghost-token"})
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

    logs = (
        (
            await db_session.execute(
                select(AuthAuditLog).where(AuthAuditLog.action_type == "user.logout")
            )
        )
        .scalars()
        .all()
    )
    assert logs == []
