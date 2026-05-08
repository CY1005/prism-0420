"""Auth Depends 横切 helper（horizontal）。

# horizontal: 是
# owner: M01（design/adr/ADR-004-auth-cross-cutting.md §1 横切范式）
# 位置: api/auth/（横切层，对齐原则 6 + R-X6 + 04-layer Q7）
# 范畴: ADR-004 横切（require_user / set_auth_service / AuthServiceProtocol）

require_user 是所有业务 endpoint 入口的 Depends——P1 Bearer JWT + P2 internal
token 解码。AuthServiceProtocol concrete 实现由 M01 注入（M01 sprint 落地）。
"""

from typing import Any, Protocol
from uuid import UUID

from fastapi import Depends, Header, Request

from api.auth.internal import verify_internal_signature
from api.auth.jwt_utils import decode_jwt
from api.errors.exceptions import PermissionDeniedError, UnauthenticatedError


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


async def require_platform_admin(user: Any = Depends(require_user)) -> Any:
    """ADR-004 P1 platform_admin 限定 endpoint 守护 / 仿 require_user 形态。

    复用 require_user 做 auth，再加 role 检查——非 platform_admin 抛 403。
    仿 api/routers/auth.py:185 require_admin 内联 check 模式，抽 helper 给所有
    admin endpoint 复用（M18 embedding_admin_router 首发）。

    注意：这里使用 api.auth.dependencies.require_user（Protocol 版），
    embedding_admin_router 改用 api.routers.auth.current_user（真实 DB 版）作为 Depends base。
    """
    if getattr(user, "role", None) != "platform_admin":
        raise PermissionDeniedError()
    return user
