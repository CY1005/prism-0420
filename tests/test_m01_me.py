"""M01 子片 1 — GET /auth/me (G2, P1-P4, A1-A4 / A5-A9c basics)."""

from __future__ import annotations

import time
from datetime import UTC, datetime

import jwt
from sqlalchemy import update

from api.auth.internal import compute_signature
from api.auth.jwt_utils import encode_jwt
from api.core.config import settings
from api.models.user import User


async def test_me_with_valid_bearer_returns_profile(auth_client, make_user):
    user = await make_user(email="me@example.com")
    token = encode_jwt(user.id, extra_claims={"type": "access"})

    r = await auth_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == str(user.id)
    assert body["email"] == "me@example.com"
    assert body["version"] == 1


async def test_me_without_credentials_returns_401(auth_client):
    r = await auth_client.get("/auth/me")
    assert r.status_code == 401
    assert r.json()["code"] == "unauthenticated"


async def test_me_with_expired_jwt_returns_401(auth_client, make_user):
    user = await make_user()
    expired = jwt.encode(
        {"sub": str(user.id), "iat": int(time.time()) - 7200, "exp": int(time.time()) - 60},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    r = await auth_client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401


async def test_me_with_forged_signature_returns_401(auth_client, make_user):
    user = await make_user()
    forged = jwt.encode(
        {"sub": str(user.id), "iat": int(time.time())},
        "wrong-secret",
        algorithm=settings.jwt_algorithm,
    )
    r = await auth_client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


async def test_me_with_disabled_account_returns_401(auth_client, make_user, db_session):
    user = await make_user()
    token = encode_jwt(user.id, extra_claims={"type": "access"})
    await db_session.execute(update(User).where(User.id == user.id).values(status="disabled"))
    await db_session.flush()

    r = await auth_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


async def test_me_with_iat_before_token_invalidated_at_returns_401(
    auth_client, make_user, db_session
):
    user = await make_user()
    token = encode_jwt(user.id, extra_claims={"type": "access"})
    await db_session.execute(
        update(User).where(User.id == user.id).values(token_invalidated_at=datetime.now(UTC))
    )
    await db_session.flush()
    # 老 token 的 iat 是"现在或更早"——服务端看到 token_invalidated_at >= iat 就拒
    time.sleep(1.1)
    # 触发服务端比较：让墙钟向前 1s 后再请求；token 的 iat 不变，token_invalidated_at 变近
    r = await auth_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


async def test_me_with_internal_token_path_returns_profile(auth_client, make_user):
    """A5 / A9b 兜底：无 Bearer 时走 P2 internal token 路径。"""
    user = await make_user()
    ts = str(int(time.time()))
    sig = compute_signature(ts, "GET", "/auth/me", user.id, b"")
    r = await auth_client.get(
        "/auth/me",
        headers={
            "X-Internal-Token": settings.internal_token,
            "X-User-Id": str(user.id),
            "X-Internal-Timestamp": ts,
            "X-Internal-Signature": sig,
        },
    )
    assert r.status_code == 200
    assert r.json()["id"] == str(user.id)


async def test_me_with_invalid_internal_signature_returns_401(auth_client, make_user):
    user = await make_user()
    ts = str(int(time.time()))
    r = await auth_client.get(
        "/auth/me",
        headers={
            "X-Internal-Token": settings.internal_token,
            "X-User-Id": str(user.id),
            "X-Internal-Timestamp": ts,
            "X-Internal-Signature": "deadbeef",
        },
    )
    assert r.status_code == 401


async def test_me_refresh_token_used_as_bearer_returns_401(auth_client, make_user):
    """A4 — refresh_token 不是 JWT，放进 Authorization 头会 decode 失败 → 401."""
    await make_user()
    r = await auth_client.get(
        "/auth/me", headers={"Authorization": "Bearer not-a-jwt-just-some-random"}
    )
    assert r.status_code == 401
