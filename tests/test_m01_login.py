"""M01 子片 1 — POST /auth/login (G1, B1-B2, P9-P11, L1-L3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from api.models.user import AuthAuditLog, RefreshToken


async def test_login_success_returns_tokens_and_writes_audit(auth_client, make_user, db_session):
    user = await make_user(email="alice@example.com", password="hunter2hunter")

    r = await auth_client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "hunter2hunter"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["version"] == 1

    rts = (
        (await db_session.execute(select(RefreshToken).where(RefreshToken.user_id == user.id)))
        .scalars()
        .all()
    )
    assert len(rts) == 1
    assert rts[0].ip is not None  # TestClient localhost

    logs = (
        (
            await db_session.execute(
                select(AuthAuditLog).where(
                    AuthAuditLog.user_id == user.id,
                    AuthAuditLog.action_type == "user.login_success",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(logs) == 1
    assert "ip" in logs[0].metadata_


async def test_login_empty_email_422(auth_client):
    r = await auth_client.post("/auth/login", json={"email": "", "password": "x"})
    assert r.status_code == 422


async def test_login_invalid_email_format_422(auth_client):
    r = await auth_client.post("/auth/login", json={"email": "not-an-email", "password": "x"})
    assert r.status_code == 422


async def test_login_unknown_email_returns_invalid_credentials_and_logs_failure(
    auth_client, db_session
):
    r = await auth_client.post(
        "/auth/login", json={"email": "ghost@example.com", "password": "whatever"}
    )
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_credentials"

    logs = (
        (
            await db_session.execute(
                select(AuthAuditLog).where(AuthAuditLog.action_type == "user.login_failed")
            )
        )
        .scalars()
        .all()
    )
    assert any(log.user_id is None for log in logs)


async def test_login_disabled_account_returns_403(auth_client, make_user):
    await make_user(email="dis@example.com", password="hunter2hunter", status_="disabled")
    r = await auth_client.post(
        "/auth/login", json={"email": "dis@example.com", "password": "hunter2hunter"}
    )
    assert r.status_code == 403
    assert r.json()["code"] == "account_disabled"


async def test_login_pending_account_returns_403(auth_client, make_user):
    await make_user(email="pend@example.com", password="hunter2hunter", status_="pending")
    r = await auth_client.post(
        "/auth/login", json={"email": "pend@example.com", "password": "hunter2hunter"}
    )
    assert r.status_code == 403
    assert r.json()["code"] == "account_pending"


async def test_login_locked_account_returns_423(auth_client, make_user, db_session):
    user = await make_user(email="lock@example.com", password="hunter2hunter")
    user.locked_until = datetime.now(UTC) + timedelta(minutes=10)
    await db_session.flush()

    r = await auth_client.post(
        "/auth/login", json={"email": "lock@example.com", "password": "hunter2hunter"}
    )
    assert r.status_code == 423
    assert r.json()["code"] == "account_locked"


async def test_login_wrong_password_increments_failed_count_and_locks_after_5(
    auth_client, make_user, db_session
):
    user = await make_user(email="boom@example.com", password="hunter2hunter")
    for _ in range(5):
        r = await auth_client.post(
            "/auth/login", json={"email": "boom@example.com", "password": "wrong"}
        )
        assert r.status_code == 401
        assert r.json()["code"] == "invalid_credentials"

    await db_session.refresh(user)
    assert user.failed_login_count >= 5
    assert user.locked_until is not None

    locked_logs = (
        (
            await db_session.execute(
                select(AuthAuditLog).where(
                    AuthAuditLog.user_id == user.id,
                    AuthAuditLog.action_type == "user.locked",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(locked_logs) == 1
