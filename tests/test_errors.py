from fastapi import FastAPI
from fastapi.testclient import TestClient

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
        "code": "NOT_FOUND",
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
    assert body["code"] == "INTERNAL_ERROR"
    assert "oops" not in body["message"]
