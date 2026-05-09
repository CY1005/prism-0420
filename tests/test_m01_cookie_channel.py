"""M01 Phase 2.2 子片 2 — refresh cookie 通道 e2e（spec 06 §2 / ADR-004 P3）。

验 login Set-Cookie / refresh cookie-only / logout 清 cookie。
1619 baseline 不破前提下，新增对 cookie 双通道的字面断言（防 P3 实施漂移）。
"""

from __future__ import annotations


async def test_login_sets_refresh_cookie(auth_client, make_user):
    await make_user(email="cookie1@example.com", password="hunter2hunter")
    r = await auth_client.post(
        "/auth/login", json={"email": "cookie1@example.com", "password": "hunter2hunter"}
    )
    assert r.status_code == 200
    cookie_header = r.headers.get("set-cookie", "")
    assert "refresh_token=" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "Path=/auth" in cookie_header
    assert "SameSite=strict" in cookie_header.lower() or "samesite=strict" in cookie_header.lower()


async def test_refresh_with_cookie_only_no_body_token(auth_client, make_user):
    await make_user(email="cookie2@example.com", password="hunter2hunter")
    login = await auth_client.post(
        "/auth/login", json={"email": "cookie2@example.com", "password": "hunter2hunter"}
    )
    assert login.status_code == 200
    # httpx AsyncClient 自动携带 Set-Cookie 收到的 cookie；body 不传 refresh_token
    r = await auth_client.post("/auth/refresh", json={})
    assert r.status_code == 200
    assert r.json()["access_token"]


async def test_refresh_missing_cookie_and_body_returns_401(auth_client):
    # 无 cookie + 无 body refresh_token → 401（不是 422）
    r = await auth_client.post("/auth/refresh", json={})
    assert r.status_code == 401


async def test_logout_clears_refresh_cookie(auth_client, make_user):
    await make_user(email="cookie3@example.com", password="hunter2hunter")
    login = await auth_client.post(
        "/auth/login", json={"email": "cookie3@example.com", "password": "hunter2hunter"}
    )
    refresh_raw = login.json()["refresh_token"]
    r = await auth_client.post("/auth/logout", json={"refresh_token": refresh_raw})
    assert r.status_code == 200
    cookie_header = r.headers.get("set-cookie", "")
    # delete_cookie 设 Max-Age=0 + 空值
    assert "refresh_token=" in cookie_header
    assert "Max-Age=0" in cookie_header or "max-age=0" in cookie_header.lower()
