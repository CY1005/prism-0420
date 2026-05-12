"""全局错误中间件横切 helper（horizontal）。

# horizontal: 是
# owner: engineering-spec §7.2（统一错误响应 payload 格式）
# 位置: api/errors/（横切层，对齐原则 6 + R-X6 + 04-layer Q7）
# 范畴: FastAPI exception_handler 注册（AppError → JSONResponse 序列化）
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
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


# P4 cluster-5 (2026-05-13): 全局 RequestValidationError → flat error 包装
# 取代 FastAPI 默认输出 `{"detail":[{"type":"missing","loc":["body"],"msg":...}]}`
# 防止 raw Pydantic 内部字段名（loc/type/msg）泄漏 + 让所有 422 走 design §13 flat 契约
# 锚: B-P2-cc-A-empty-body-pydantic-422 / engineering-spec §7.4 / §7.6
# 简化 details.errors[]：只保留 loc 路径 + msg 文案 / 去掉 type / input 等内部字段
async def _handle_request_validation(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors_simplified = [
        {
            "loc": [str(item) for item in (err.get("loc") or [])],
            "msg": err.get("msg") or "Field invalid",
        }
        for err in (exc.errors() or [])
    ]
    log.info(
        "app.request_validation",
        code=ErrorCode.INVALID_REQUEST_BODY.value,
        path=request.url.path,
        method=request.method,
        error_count=len(errors_simplified),
    )
    return JSONResponse(
        status_code=422,
        content=_payload(
            ErrorCode.INVALID_REQUEST_BODY,
            "Request body validation failed",
            {"errors": errors_simplified},
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_request_validation)
    app.add_exception_handler(Exception, _handle_unhandled)
