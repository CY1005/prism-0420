from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.core.logging import log
from api.errors.codes import ErrorCode
from api.errors.exceptions import AppError


def _payload(code: ErrorCode, message: str, details: dict | None = None) -> dict:
    body: dict = {"code": code.value, "message": message}
    if details:
        body["details"] = details
    return body


async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    log.warning(
        "app.error",
        code=exc.code.value,
        http_status=exc.http_status,
        path=request.url.path,
        method=request.method,
        details=exc.details,
    )
    return JSONResponse(
        status_code=exc.http_status,
        content=_payload(exc.code, exc.message, exc.details or None),
    )


async def _handle_unhandled(request: Request, exc: Exception) -> JSONResponse:
    log.exception(
        "app.unhandled",
        path=request.url.path,
        method=request.method,
        exc_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content=_payload(ErrorCode.INTERNAL_ERROR, "Internal error"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(Exception, _handle_unhandled)
