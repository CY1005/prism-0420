from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from api.errors import (
    AppError,
    ConflictError,
    ErrorCode,
    NotFoundError,
    PermissionDeniedError,
    UnauthenticatedError,
    ValidationError,
    register_exception_handlers,
)


def _build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/raise-app")
    def _raise_app():
        raise NotFoundError("Module 42 not found", module_id=42)

    @app.get("/raise-perm")
    def _raise_perm():
        raise PermissionDeniedError()

    @app.get("/raise-conflict")
    def _raise_conflict():
        raise ConflictError()

    @app.get("/raise-validation")
    def _raise_validation():
        raise ValidationError("Bad name")

    @app.get("/raise-unauth")
    def _raise_unauth():
        raise UnauthenticatedError()

    @app.get("/raise-bare")
    def _raise_bare():
        raise RuntimeError("oops should not leak")

    class _Body(BaseModel):
        name: str
        value: int

    @app.post("/needs-body")
    def _needs_body(payload: _Body):
        return {"ok": True}

    return app


def test_apperror_default_code_is_internal():
    err = AppError()
    assert err.code == ErrorCode.INTERNAL_ERROR
    assert err.http_status == 500


def test_apperror_message_overridable_with_details():
    err = NotFoundError("Module 42 not found", module_id=42)
    assert err.message == "Module 42 not found"
    assert err.details == {"module_id": 42}


def test_app_error_returns_structured_json():
    client = TestClient(_build_app())
    r = client.get("/raise-app")
    assert r.status_code == 404
    body = r.json()
    assert body == {
        "code": "not_found",
        "message": "Module 42 not found",
        "details": {"module_id": 42},
    }


def test_other_app_errors_status_codes():
    client = TestClient(_build_app())
    assert client.get("/raise-perm").status_code == 403
    assert client.get("/raise-conflict").status_code == 409
    assert client.get("/raise-validation").status_code == 422
    assert client.get("/raise-unauth").status_code == 401


def test_unhandled_exception_does_not_leak_internal_message():
    client = TestClient(_build_app(), raise_server_exceptions=False)
    r = client.get("/raise-bare")
    assert r.status_code == 500
    body = r.json()
    assert body["code"] == "internal_error"
    assert "oops" not in body["message"]


# ─── B-P2-cc-A-empty-body-pydantic-422 / P4 cluster-5 (2026-05-13) ─────────


def test_request_validation_empty_body_returns_flat_invalid_request_body():
    """空 body → flat `{"code":"invalid_request_body", ...}` / 不暴露 raw Pydantic detail。"""
    client = TestClient(_build_app())
    r = client.post("/needs-body")  # 无 body
    assert r.status_code == 422
    body = r.json()
    # flat 契约：顶层 code/message/details / 无 "error" wrapper / 无 "detail" raw 输出
    assert body["code"] == "invalid_request_body"
    assert body["message"] == "Request body validation failed"
    assert "error" not in body  # 防嵌套契约回滚
    assert "detail" not in body  # 防 raw Pydantic 输出回滚
    # details.errors[] 简化版只含 loc + msg / 不含 type / input
    assert "errors" in body["details"]
    assert isinstance(body["details"]["errors"], list)
    assert len(body["details"]["errors"]) >= 1
    first = body["details"]["errors"][0]
    assert "loc" in first
    assert "msg" in first
    assert "type" not in first  # 不暴露 Pydantic 内部 type
    assert "input" not in first


def test_request_validation_missing_field_returns_flat():
    """字段缺失 → 同样走 flat handler。"""
    client = TestClient(_build_app())
    r = client.post("/needs-body", json={"name": "x"})  # 缺 value
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "invalid_request_body"
    assert "errors" in body["details"]


def test_request_validation_invalid_type_returns_flat():
    """类型不符 → flat handler。"""
    client = TestClient(_build_app())
    r = client.post("/needs-body", json={"name": "x", "value": "not-int"})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "invalid_request_body"
