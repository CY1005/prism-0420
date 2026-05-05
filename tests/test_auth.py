import time
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from api.auth import (
    compute_signature,
    decode_jwt,
    encode_jwt,
    require_user,
    set_auth_service,
    verify_internal_signature,
)
from api.core.config import settings
from api.errors import register_exception_handlers


class _StubAuthService:
    def __init__(self, valid_id: UUID):
        self.valid_id = valid_id
        self.calls: list[UUID] = []

    async def get_user_by_id(self, user_id):
        self.calls.append(user_id)
        if user_id == self.valid_id:
            return {"id": str(user_id), "email": "u@example.com"}
        return None


_RequireUser = Depends(require_user)


def _build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/me")
    async def me(user=_RequireUser):
        return user

    return app


def test_jwt_encode_decode_roundtrip():
    uid = uuid4()
    token = encode_jwt(uid, extra_claims={"role": "admin"})
    decoded = decode_jwt(token)
    assert decoded["sub"] == str(uid)
    assert decoded["role"] == "admin"
    assert "exp" in decoded


def test_jwt_expired_raises():
    uid = uuid4()
    expired = jwt.encode(
        {"sub": str(uid), "exp": int(time.time()) - 60},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_jwt(expired)


def test_internal_signature_roundtrip():
    uid = uuid4()
    ts = str(int(time.time()))
    sig = compute_signature(ts, "POST", "/x?q=1", uid, b'{"k":1}')
    assert verify_internal_signature(
        token=settings.internal_token,
        user_id=uid,
        signature=sig,
        timestamp=ts,
        method="POST",
        path_with_query="/x?q=1",
        body=b'{"k":1}',
    )


def test_internal_signature_rejects_tampered_body():
    uid = uuid4()
    ts = str(int(time.time()))
    sig = compute_signature(ts, "POST", "/x", uid, b'{"k":1}')
    assert not verify_internal_signature(
        token=settings.internal_token,
        user_id=uid,
        signature=sig,
        timestamp=ts,
        method="POST",
        path_with_query="/x",
        body=b'{"k":2}',
    )


def test_internal_signature_rejects_old_timestamp():
    uid = uuid4()
    old_ts = str(int(time.time()) - 1000)
    sig = compute_signature(old_ts, "GET", "/x", uid, b"")
    assert not verify_internal_signature(
        token=settings.internal_token,
        user_id=uid,
        signature=sig,
        timestamp=old_ts,
        method="GET",
        path_with_query="/x",
        body=b"",
    )


def test_internal_signature_rejects_wrong_token():
    uid = uuid4()
    ts = str(int(time.time()))
    sig = compute_signature(ts, "GET", "/x", uid, b"")
    assert not verify_internal_signature(
        token="wrong-token",
        user_id=uid,
        signature=sig,
        timestamp=ts,
        method="GET",
        path_with_query="/x",
        body=b"",
    )


def test_require_user_p1_jwt_happy_path():
    uid = uuid4()
    set_auth_service(_StubAuthService(uid))
    try:
        token = encode_jwt(uid)
        client = TestClient(_build_app())
        r = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["id"] == str(uid)
    finally:
        set_auth_service(None)


def test_require_user_p2_internal_happy_path():
    uid = uuid4()
    set_auth_service(_StubAuthService(uid))
    try:
        ts = str(int(time.time()))
        sig = compute_signature(ts, "GET", "/me", uid, b"")
        client = TestClient(_build_app())
        r = client.get(
            "/me",
            headers={
                "X-Internal-Token": settings.internal_token,
                "X-User-Id": str(uid),
                "X-Internal-Timestamp": ts,
                "X-Internal-Signature": sig,
            },
        )
        assert r.status_code == 200
        assert r.json()["id"] == str(uid)
    finally:
        set_auth_service(None)


def test_require_user_no_credentials_returns_401():
    set_auth_service(_StubAuthService(uuid4()))
    try:
        client = TestClient(_build_app())
        r = client.get("/me")
        assert r.status_code == 401
        assert r.json()["code"] == "UNAUTHENTICATED"
    finally:
        set_auth_service(None)


def test_require_user_unknown_user_returns_401():
    real = uuid4()
    other = uuid4()
    set_auth_service(_StubAuthService(real))
    try:
        token = encode_jwt(other)
        client = TestClient(_build_app())
        r = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401
    finally:
        set_auth_service(None)


def test_require_user_without_service_initialized_returns_401():
    set_auth_service(None)
    client = TestClient(_build_app())
    r = client.get("/me", headers={"Authorization": "Bearer x"})
    assert r.status_code == 401
