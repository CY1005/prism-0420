"""M01 auth router（design §7）。

P1（Bearer JWT）+ P2（Internal token + HMAC）双路径合一在 ``current_user``，
失败统一抛 UnauthenticatedError。
"""

from __future__ import annotations

from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.internal import verify_internal_signature
from api.auth.jwt_utils import decode_jwt
from api.core.db import get_db
from api.errors.exceptions import UnauthenticatedError
from api.models.user import User
from api.schemas.auth import (
    LoginRequest,
    LogoutResponse,
    RefreshRequest,
    RefreshResponse,
    TokenResponse,
    UserProfile,
)
from api.services.auth_service import AuthService, get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


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
) -> RefreshResponse:
    svc = get_auth_service()
    _, access_token = await svc.refresh(
        db, refresh_token=payload.refresh_token, ip=_client_ip(request)
    )
    return RefreshResponse(access_token=access_token)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    payload: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> LogoutResponse:
    svc = get_auth_service()
    await svc.logout(db, refresh_token=payload.refresh_token, ip=_client_ip(request))
    return LogoutResponse()


@router.get("/me", response_model=UserProfile)
async def me(user: User = Depends(current_user)) -> UserProfile:
    return UserProfile.model_validate(user)
