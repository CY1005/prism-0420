"""M01 auth router（design §7）。

P1（Bearer JWT）+ P2（Internal token + HMAC）双路径合一在 ``current_user``，
失败统一抛 UnauthenticatedError。
"""

from __future__ import annotations

from uuid import UUID

import jwt
from fastapi import APIRouter, Cookie, Depends, Header, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.internal import verify_internal_signature
from api.auth.jwt_utils import decode_jwt
from api.core.config import settings
from api.core.db import get_db
from api.errors.exceptions import PermissionDeniedError, UnauthenticatedError
from api.models.user import User
from api.schemas.auth import (
    CreateUserRequest,
    CreateUserResponse,
    LoginRequest,
    LogoutResponse,
    RefreshRequest,
    RefreshResponse,
    TokenResponse,
    UpdateProfileRequest,
    UpdateUserRequest,
    UserListItem,
    UserListResponse,
    UserProfile,
)
from api.services.auth_service import AuthService, get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

# Phase 2.2 子片 2 — refresh cookie 名 / path（spec 06 §2）
# Path=/ 全局：dogfooding sprint trigger_bug 修复（2026-05-12）
# 原 Path=/auth 与 router prefix 对齐，但导致 Next.js Server Action 端点（/projects/new 等
# 应用路径）请求时浏览器不携带 refresh cookie → server-auth.ts `cookies().get(refresh_token)`
# 返 undefined → server action 全部 401 redirect /login。
# 修为 Path=/ 让所有同源请求带 refresh cookie / 安全护栏仍是 HttpOnly + Secure(prod) + SameSite=strict。
# 详见 _handoff/dogfooding/04-bug-fixes/B-trigger-bug-server-action-cookie/rca.md
REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/"


def _set_refresh_cookie(response: Response, raw_refresh: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_refresh,
        max_age=settings.refresh_token_ttl_days * 86400,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        # Phase 2.3 cleanup A+ follow-up: production-only secure
        # (旧 "!= local" 把 CI/test 当 production / 但 CI ASGITransport base_url=
        # http://test 不是 HTTPS，secure=True 时 cookie 不发 → refresh test 401)
        secure=settings.app_env == "production",
        samesite="strict",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
    )


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


async def _resolve_bearer(
    authorization: str | None, db: AsyncSession, svc: AuthService
) -> User | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    try:
        claims = decode_jwt(token)
    except jwt.PyJWTError:
        return None
    if claims.get("type") and claims["type"] != "access":
        return None
    try:
        user_id = UUID(str(claims["sub"]))
        iat = int(claims["iat"])
    except (KeyError, ValueError):
        return None
    try:
        return await svc.get_user_for_jwt(db, user_id, iat)
    except UnauthenticatedError:
        return None


async def _resolve_internal(
    request: Request,
    x_internal_token: str | None,
    x_user_id: str | None,
    x_internal_signature: str | None,
    x_internal_timestamp: str | None,
    db: AsyncSession,
    svc: AuthService,
) -> User | None:
    if not all((x_internal_token, x_user_id, x_internal_signature, x_internal_timestamp)):
        return None
    try:
        user_id = UUID(str(x_user_id))
    except ValueError:
        return None
    body = await request.body()
    path_with_query = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    if not verify_internal_signature(
        token=str(x_internal_token),
        user_id=user_id,
        signature=str(x_internal_signature),
        timestamp=str(x_internal_timestamp),
        method=request.method,
        path_with_query=path_with_query,
        body=body,
    ):
        return None
    try:
        return await svc.get_user_for_internal(db, user_id)
    except UnauthenticatedError:
        return None


async def current_user(
    request: Request,
    authorization: str | None = Header(None),
    x_internal_token: str | None = Header(None),
    x_user_id: str | None = Header(None),
    x_internal_signature: str | None = Header(None),
    x_internal_timestamp: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """ADR-004 §2 P1+P2 合并入口（design §8）。

    P1 优先（B1 决策）；P1 解析失败再走 P2。两者都失败抛 401。
    """
    svc = get_auth_service()
    user = await _resolve_bearer(authorization, db, svc)
    if user is None:
        user = await _resolve_internal(
            request,
            x_internal_token,
            x_user_id,
            x_internal_signature,
            x_internal_timestamp,
            db,
            svc,
        )
    if user is None:
        raise UnauthenticatedError()
    return user


# ─────────────── endpoints ───────────────


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    svc = get_auth_service()
    user_agent = request.headers.get("user-agent")
    user, access_token, raw_refresh = await svc.login(
        db,
        email=payload.email,
        password=payload.password,
        ip=_client_ip(request),
        user_agent=user_agent,
    )
    # spec 06 §2: refresh 走 httpOnly cookie / body 字段保留做 deprecated 兼容
    _set_refresh_cookie(response, raw_refresh)
    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        user=UserProfile.model_validate(user),
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> RefreshResponse:
    # spec 06 §2: cookie 优先 / body 兜底（ADR-004 P3 字面双通道）
    raw = refresh_cookie or payload.refresh_token
    if not raw:
        raise UnauthenticatedError("missing refresh token")
    svc = get_auth_service()
    _, access_token = await svc.refresh(db, refresh_token=raw, ip=_client_ip(request))
    return RefreshResponse(access_token=access_token)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    payload: RefreshRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> LogoutResponse:
    raw = refresh_cookie or payload.refresh_token
    svc = get_auth_service()
    if raw:
        await svc.logout(db, refresh_token=raw, ip=_client_ip(request))
    _clear_refresh_cookie(response)
    return LogoutResponse()


@router.get("/me", response_model=UserProfile)
async def me(user: User = Depends(current_user)) -> UserProfile:
    return UserProfile.model_validate(user)


async def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "platform_admin":
        raise PermissionDeniedError()
    return user


@router.patch("/me", response_model=UserProfile)
async def update_me(
    payload: UpdateProfileRequest,
    request: Request,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    svc = get_auth_service()
    updated = await svc.update_self_profile(
        db,
        user_id=user.id,
        expected_version=payload.expected_version,
        name=payload.name,
        old_password=payload.old_password,
        new_password=payload.new_password,
        ip=_client_ip(request),
    )
    return UserProfile.model_validate(updated)


# ─────────────── admin endpoints ───────────────


@router.post("/users", response_model=CreateUserResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    payload: CreateUserRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CreateUserResponse:
    svc = get_auth_service()
    user = await svc.admin_create_user(
        db,
        admin_id=admin.id,
        email=payload.email,
        name=payload.name,
        password=payload.password,
        role=payload.role,
        ip=_client_ip(request),
    )
    return CreateUserResponse.model_validate(user)


@router.get("/users", response_model=UserListResponse)
async def admin_list_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    svc = get_auth_service()
    users = await svc.admin_list_users(db)
    return UserListResponse(users=[UserListItem.model_validate(u) for u in users], total=len(users))


@router.patch("/users/{user_id}", response_model=UserProfile)
async def admin_update_user(
    user_id: UUID,
    payload: UpdateUserRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    svc = get_auth_service()
    target = await svc.admin_update_user(
        db,
        admin_id=admin.id,
        target_user_id=user_id,
        expected_version=payload.expected_version,
        role=payload.role,
        status_=payload.status,
        ip=_client_ip(request),
    )
    return UserProfile.model_validate(target)
