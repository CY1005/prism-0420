from typing import Any, Protocol
from uuid import UUID

from fastapi import Header, Request

from api.auth.internal import verify_internal_signature
from api.auth.jwt_utils import decode_jwt
from api.errors.exceptions import UnauthenticatedError


class AuthServiceProtocol(Protocol):
    """M01 提供具体实现：从凭据返回 user 主体（任意业务对象）。

    本期 B2 仅冻结接口，concrete 实现归 M01。set_auth_service() 注入。
    """

    async def get_user_by_id(self, user_id: UUID) -> Any | None: ...


_service: AuthServiceProtocol | None = None


def set_auth_service(svc: AuthServiceProtocol | None) -> None:
    """M01 启动时注入 concrete service；测试也用此函数 mock。"""
    global _service
    _service = svc


async def require_user(
    request: Request,
    authorization: str | None = Header(None),
    x_internal_token: str | None = Header(None),
    x_user_id: str | None = Header(None),
    x_internal_signature: str | None = Header(None),
    x_internal_timestamp: str | None = Header(None),
) -> Any:
    """ADR-004 §2 P1+P2 合并入口：先试 Bearer JWT，再试 Internal Token + 签名。"""
    if _service is None:
        raise UnauthenticatedError("auth service not initialized (M01 must call set_auth_service)")

    user_id: UUID | None = None

    if authorization and authorization.startswith("Bearer "):
        try:
            claims = decode_jwt(authorization[7:])
            user_id = UUID(str(claims["sub"]))
        except Exception:
            user_id = None

    if user_id is None and all(
        h is not None
        for h in (x_internal_token, x_user_id, x_internal_signature, x_internal_timestamp)
    ):
        try:
            target_user_id = UUID(str(x_user_id))
        except ValueError:
            raise UnauthenticatedError() from None
        body = await request.body()
        path_with_query = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        if verify_internal_signature(
            token=str(x_internal_token),
            user_id=target_user_id,
            signature=str(x_internal_signature),
            timestamp=str(x_internal_timestamp),
            method=request.method,
            path_with_query=path_with_query,
            body=body,
        ):
            user_id = target_user_id

    if user_id is None:
        raise UnauthenticatedError()

    user = await _service.get_user_by_id(user_id)
    if user is None:
        raise UnauthenticatedError()
    return user
