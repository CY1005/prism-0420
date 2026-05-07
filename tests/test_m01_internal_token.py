"""M01 子片 4 — ADR-004 P2 (internal token + HMAC) 边界全测试 (A6-A23)。

P1 + P2 双路径合并入口在 routers/auth.py::current_user。本套测试用 GET /auth/me
作为消费侧端点，专注验证 P2 各类篡改 / 重放 / header 缺失 → 401。
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

from sqlalchemy import update

from api.auth.internal import compute_signature
from api.core.config import settings
from api.models.user import User


def _ts(offset_seconds: int = 0) -> str:
    return str(int(time.time()) + offset_seconds)


def _sign_headers(
    *,
    user_id,
    method: str = "GET",
    path: str = "/auth/me",
    body: bytes = b"",
    timestamp: str | None = None,
    token: str | None = None,
) -> dict:
    ts = timestamp or _ts()
    sig = compute_signature(ts, method, path, user_id, body, token=token)
    return {
        "X-Internal-Token": token or settings.internal_token,
        "X-User-Id": str(user_id),
        "X-Internal-Timestamp": ts,
        "X-Internal-Signature": sig,
    }


# ───────────── A6 / A7 / A8 ─────────────


async def test_a6_forged_internal_token_returns_401(auth_client, make_user):
    user = await make_user()
    # 计算签名时用的 token 与发送的 X-Internal-Token 不一致
    headers = _sign_headers(user_id=user.id, token="forged-token")
    headers["X-Internal-Token"] = "forged-token"  # 服务端会和 settings 比，不等
    r = await auth_client.get("/auth/me", headers=headers)
    assert r.status_code == 401


async def test_a7_internal_token_with_unknown_user_id_returns_401(auth_client, make_user):
    """A7：签名+token 正确，但 X-User-Id 在 DB 找不到。"""
    from uuid import uuid4

    await make_user()  # 至少有一个 user 存在
    ghost_id = uuid4()
    headers = _sign_headers(user_id=ghost_id)
    r = await auth_client.get("/auth/me", headers=headers)
    assert r.status_code == 401


async def test_a8_internal_token_for_disabled_user_returns_401(auth_client, make_user, db_session):
    user = await make_user()
    await db_session.execute(update(User).where(User.id == user.id).values(status="disabled"))
    await db_session.flush()

    headers = _sign_headers(user_id=user.id)
    r = await auth_client.get("/auth/me", headers=headers)
    assert r.status_code == 401


# ───────────── A15 缺 header ─────────────


async def test_a15_missing_timestamp_header_returns_401(auth_client, make_user):
    user = await make_user()
    headers = _sign_headers(user_id=user.id)
    headers.pop("X-Internal-Timestamp")
    r = await auth_client.get("/auth/me", headers=headers)
    assert r.status_code == 401


async def test_a15_missing_signature_header_returns_401(auth_client, make_user):
    user = await make_user()
    headers = _sign_headers(user_id=user.id)
    headers.pop("X-Internal-Signature")
    r = await auth_client.get("/auth/me", headers=headers)
    assert r.status_code == 401


async def test_a15_missing_user_id_header_returns_401(auth_client, make_user):
    user = await make_user()
    headers = _sign_headers(user_id=user.id)
    headers.pop("X-User-Id")
    r = await auth_client.get("/auth/me", headers=headers)
    assert r.status_code == 401


# ───────────── A16 / A17 时间戳窗口 ─────────────


async def test_a16_old_timestamp_outside_window_returns_401(auth_client, make_user):
    """5min + 1s 之前的 timestamp。"""
    user = await make_user()
    headers = _sign_headers(
        user_id=user.id,
        timestamp=_ts(offset_seconds=-(settings.internal_signature_window_seconds + 1)),
    )
    r = await auth_client.get("/auth/me", headers=headers)
    assert r.status_code == 401


async def test_a17_future_timestamp_outside_window_returns_401(auth_client, make_user):
    user = await make_user()
    headers = _sign_headers(
        user_id=user.id,
        timestamp=_ts(offset_seconds=settings.internal_signature_window_seconds + 1),
    )
    r = await auth_client.get("/auth/me", headers=headers)
    assert r.status_code == 401


# ───────────── A18 / A19 / A20 / A21 各篡改维度 ─────────────


async def test_a18_body_tampered_returns_401(auth_client, make_user):
    """对 PATCH 端点用 body=A 算签名，但发送 body=B → 401。"""
    user = await make_user()
    ts = _ts()
    sig = compute_signature(ts, "PATCH", "/auth/me", user.id, b'{"k":1}')
    r = await auth_client.patch(
        "/auth/me",
        json={"k": 2, "expected_version": 1, "name": "Z"},
        headers={
            "X-Internal-Token": settings.internal_token,
            "X-User-Id": str(user.id),
            "X-Internal-Timestamp": ts,
            "X-Internal-Signature": sig,
        },
    )
    assert r.status_code == 401


async def test_a19_path_tampered_returns_401(auth_client, make_user):
    """签名材料 path=/auth/users 但请求 /auth/me → 401。"""
    user = await make_user()
    ts = _ts()
    sig = compute_signature(ts, "GET", "/auth/users", user.id, b"")
    r = await auth_client.get(
        "/auth/me",
        headers={
            "X-Internal-Token": settings.internal_token,
            "X-User-Id": str(user.id),
            "X-Internal-Timestamp": ts,
            "X-Internal-Signature": sig,
        },
    )
    assert r.status_code == 401


async def test_a19b_query_string_tampered_returns_401(auth_client, make_user):
    """A19b：签名包含 ?dry_run=true，请求改 ?dry_run=false → 401。"""
    user = await make_user()
    ts = _ts()
    sig = compute_signature(ts, "GET", "/auth/me?dry_run=true", user.id, b"")
    r = await auth_client.get(
        "/auth/me?dry_run=false",
        headers={
            "X-Internal-Token": settings.internal_token,
            "X-User-Id": str(user.id),
            "X-Internal-Timestamp": ts,
            "X-Internal-Signature": sig,
        },
    )
    assert r.status_code == 401


async def test_a19c_query_added_returns_401(auth_client, make_user):
    """原签名无 query，请求加上 query → 401。"""
    user = await make_user()
    ts = _ts()
    sig = compute_signature(ts, "GET", "/auth/me", user.id, b"")
    r = await auth_client.get(
        "/auth/me?foo=bar",
        headers={
            "X-Internal-Token": settings.internal_token,
            "X-User-Id": str(user.id),
            "X-Internal-Timestamp": ts,
            "X-Internal-Signature": sig,
        },
    )
    assert r.status_code == 401


async def test_a19d_query_param_order_changed_returns_401(auth_client, make_user):
    """A19d：本期不做 query 规范化，参数顺序变化即签名失败。"""
    user = await make_user()
    ts = _ts()
    sig = compute_signature(ts, "GET", "/auth/me?a=1&b=2", user.id, b"")
    r = await auth_client.get(
        "/auth/me?b=2&a=1",
        headers={
            "X-Internal-Token": settings.internal_token,
            "X-User-Id": str(user.id),
            "X-Internal-Timestamp": ts,
            "X-Internal-Signature": sig,
        },
    )
    assert r.status_code == 401


async def test_a20_method_tampered_returns_401(auth_client, make_user):
    """签名材料 method=GET，但实际请求 PATCH → 401。"""
    user = await make_user()
    ts = _ts()
    sig = compute_signature(ts, "GET", "/auth/me", user.id, b"")
    # 用 PATCH 触发同 path 但 method 不同
    r = await auth_client.patch(
        "/auth/me",
        json={"expected_version": 1, "name": "X"},
        headers={
            "X-Internal-Token": settings.internal_token,
            "X-User-Id": str(user.id),
            "X-Internal-Timestamp": ts,
            "X-Internal-Signature": sig,
        },
    )
    assert r.status_code == 401


async def test_a21_user_id_header_tampered_returns_401(auth_client, make_user):
    """签名内 user_id=A，但 X-User-Id 头改成 B → HMAC 不等 → 401。"""
    user_a = await make_user(email="a@example.com")
    user_b = await make_user(email="b@example.com")
    ts = _ts()
    sig = compute_signature(ts, "GET", "/auth/me", user_a.id, b"")
    r = await auth_client.get(
        "/auth/me",
        headers={
            "X-Internal-Token": settings.internal_token,
            "X-User-Id": str(user_b.id),  # 不一致
            "X-Internal-Timestamp": ts,
            "X-Internal-Signature": sig,
        },
    )
    assert r.status_code == 401


# ───────────── A22 / A23 重放 ─────────────


async def test_a22_replay_within_window_succeeds_n_times(auth_client, make_user):
    """A22 — 本期允许窗口内重放，多次都 200（nonce 防御未实装）。"""
    user = await make_user()
    headers = _sign_headers(user_id=user.id)
    for _ in range(3):
        r = await auth_client.get("/auth/me", headers=headers)
        assert r.status_code == 200


async def test_a23_replay_outside_window_fails(auth_client, make_user):
    user = await make_user()
    headers = _sign_headers(
        user_id=user.id,
        timestamp=_ts(offset_seconds=-(settings.internal_signature_window_seconds + 5)),
    )
    r = await auth_client.get("/auth/me", headers=headers)
    assert r.status_code == 401


# ───────────── A14 P4 预留端点不存在 ─────────────


async def test_a14_password_reset_endpoint_not_implemented_returns_404(auth_client):
    """A14：P4 一次性 token 路径本期不实装，POST /auth/password-reset 路由不存在 → 404。"""
    r = await auth_client.post("/auth/password-reset", json={"email": "x@example.com"})
    assert r.status_code == 404


# Suppress unused import warning (UTC kept for future iat-based extension)
_ = datetime
_ = UTC
