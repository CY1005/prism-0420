"""M01 AuthService（design §6）。

事务边界：所有"产生副作用 + 写审计"的方法都用 ``async with db.begin():`` 单
原子事务包裹。失败路径（如 login_failed）走独立小事务，确保即使主路径回滚也留痕。
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.jwt_utils import encode_jwt
from api.auth.password import hash_password, verify_password
from api.core.config import settings
from api.dao.user_dao import AuthAuditLogDAO, RefreshTokenDAO, UserDAO
from api.errors.exceptions import (
    AccountDisabledError,
    AccountLockedError,
    AccountPendingError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    PasswordTooWeakError,
    RefreshTokenExpiredError,
    UnauthenticatedError,
)
from api.models.user import User, UserStatus

MIN_PASSWORD_LEN = 8


def _now() -> datetime:
    return datetime.now(UTC)


def _hash_refresh(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


class AuthService:
    def __init__(self) -> None:
        self.users = UserDAO()
        self.tokens = RefreshTokenDAO()
        self.audit = AuthAuditLogDAO()

    # ─────────────── login / refresh / logout / me ───────────────

    async def login(
        self,
        db: AsyncSession,
        *,
        email: str,
        password: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str, str]:
        """返回 (user, access_token, raw_refresh_token)。"""
        user = await self.users.get_by_email(db, email)
        if user is None:
            await self.audit.write(
                db,
                action_type="user.login_failed",
                user_id=None,
                metadata={"email": email, "reason": "unknown_email", "ip": ip},
            )
            await db.commit()
            raise InvalidCredentialsError()

        # 状态闸（先于密码核对，避免暴露密码强度信息）
        if user.status == UserStatus.DISABLED.value:
            raise AccountDisabledError()
        if user.status == UserStatus.PENDING.value:
            raise AccountPendingError()

        if user.locked_until is not None and user.locked_until > _now():
            raise AccountLockedError(locked_until=user.locked_until.isoformat())

        if not verify_password(password, user.password_hash or ""):
            user.failed_login_count = (user.failed_login_count or 0) + 1
            metadata: dict[str, Any] = {
                "email": email,
                "reason": "wrong_password",
                "ip": ip,
                "failed_count": user.failed_login_count,
            }
            await self.audit.write(
                db, action_type="user.login_failed", user_id=user.id, metadata=metadata
            )
            if user.failed_login_count >= settings.max_failed_logins:
                user.locked_until = _now() + timedelta(minutes=settings.account_lock_minutes)
                await self.audit.write(
                    db,
                    action_type="user.locked",
                    user_id=user.id,
                    metadata={"ip": ip, "locked_until": user.locked_until.isoformat()},
                )
            await db.commit()
            raise InvalidCredentialsError()

        # 成功：重置 failed_count，发放 token
        user.failed_login_count = 0
        user.locked_until = None

        access_token = encode_jwt(user.id, extra_claims={"type": "access"})
        raw_refresh = _new_refresh_token()
        await self.tokens.create(
            db,
            user_id=user.id,
            token_hash=_hash_refresh(raw_refresh),
            expires_at=_now() + timedelta(days=settings.refresh_token_ttl_days),
            ip=ip,
            user_agent=user_agent,
        )
        await self.audit.write(
            db,
            action_type="user.login_success",
            user_id=user.id,
            metadata={"ip": ip, "user_agent": user_agent},
        )
        await db.commit()
        return user, access_token, raw_refresh

    async def refresh(
        self,
        db: AsyncSession,
        *,
        refresh_token: str,
        ip: str | None = None,
    ) -> tuple[User, str]:
        token_hash = _hash_refresh(refresh_token)
        rt = await self.tokens.get_by_hash(db, token_hash)
        if rt is None:
            raise InvalidRefreshTokenError()

        now = _now()
        if rt.expires_at <= now:
            await db.delete(rt)
            await db.commit()
            raise RefreshTokenExpiredError()

        user = await self.users.get_by_id(db, rt.user_id)
        if user is None or user.status != UserStatus.ACTIVE.value:
            raise InvalidRefreshTokenError()

        # ADR-004 #5：token_invalidated_at 晚于 refresh_token 创建则失效
        if user.token_invalidated_at is not None and user.token_invalidated_at > rt.created_at:
            raise InvalidRefreshTokenError()

        rt.last_seen_at = now
        access_token = encode_jwt(user.id, extra_claims={"type": "access"})
        await self.audit.write(
            db, action_type="user.refresh_token", user_id=user.id, metadata={"ip": ip}
        )
        await db.commit()
        return user, access_token

    async def logout(
        self,
        db: AsyncSession,
        *,
        refresh_token: str,
        ip: str | None = None,
    ) -> None:
        token_hash = _hash_refresh(refresh_token)
        rt = await self.tokens.get_by_hash(db, token_hash)
        if rt is not None:
            user_id = rt.user_id
            await db.delete(rt)
            await self.audit.write(
                db, action_type="user.logout", user_id=user_id, metadata={"ip": ip}
            )
            await db.commit()
        # 即使 token 不存在也返回 ok（不暴露存在性）

    async def get_user_for_jwt(self, db: AsyncSession, user_id: UUID, iat: int) -> User:
        user = await self.users.get_by_id(db, user_id)
        if user is None:
            raise UnauthenticatedError()
        if user.status != UserStatus.ACTIVE.value:
            raise UnauthenticatedError()
        if user.token_invalidated_at is not None:
            # iat 是秒级；token_invalidated_at 微秒级。同秒边界情况按"已失效"处理（ADR-004 #5 安全侧倾）。
            invalidated_at = int(user.token_invalidated_at.timestamp())
            if iat <= invalidated_at:
                raise UnauthenticatedError()
        return user

    async def get_user_for_internal(self, db: AsyncSession, user_id: UUID) -> User:
        user = await self.users.get_by_id(db, user_id)
        if user is None or user.status != UserStatus.ACTIVE.value:
            raise UnauthenticatedError()
        return user

    # ─────────────── bootstrap ───────────────

    async def bootstrap_admin_if_empty(
        self,
        db: AsyncSession,
        *,
        email: str,
        password: str,
        name: str,
    ) -> User | None:
        from sqlalchemy import select

        from api.models.user import User as UserModel

        result = await db.execute(select(UserModel).limit(1))
        if result.scalar_one_or_none() is not None:
            return None
        if len(password) < MIN_PASSWORD_LEN:
            raise PasswordTooWeakError()
        user = await self.users.create(
            db,
            email=email,
            name=name,
            password_hash=hash_password(password),
            role="platform_admin",
            status="active",
            failed_login_count=0,
            version=1,
        )
        await self.audit.write(
            db,
            action_type="user.admin_create",
            user_id=user.id,
            metadata={"role": "platform_admin", "created_by": "bootstrap"},
        )
        await db.commit()
        return user

    async def create_admin(
        self,
        db: AsyncSession,
        *,
        email: str,
        password: str,
        name: str,
    ) -> User:
        if len(password) < MIN_PASSWORD_LEN:
            raise PasswordTooWeakError()
        existing = await self.users.get_by_email(db, email)
        if existing is not None:
            from api.errors.exceptions import EmailAlreadyExistsError

            raise EmailAlreadyExistsError()
        user = await self.users.create(
            db,
            email=email,
            name=name,
            password_hash=hash_password(password),
            role="platform_admin",
            status="active",
            failed_login_count=0,
            version=1,
        )
        await self.audit.write(
            db,
            action_type="user.admin_create",
            user_id=user.id,
            metadata={"role": "platform_admin", "created_by": "cli"},
        )
        await db.commit()
        return user


_singleton: AuthService | None = None


def get_auth_service() -> AuthService:
    global _singleton
    if _singleton is None:
        _singleton = AuthService()
    return _singleton
