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
    OldPasswordMismatchError,
    PasswordTooWeakError,
    RefreshTokenExpiredError,
    UnauthenticatedError,
    ValidationError,
    VersionConflictError,
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

    async def update_self_profile(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        expected_version: int,
        name: str | None = None,
        old_password: str | None = None,
        new_password: str | None = None,
        ip: str | None = None,
    ) -> User:
        """PATCH /auth/me — 改 name 或改密码（design §5 多人架构 / §10 audit）。

        事务原子性：mutation + audit + revoke_all 在同一事务；任一失败显式 rollback。
        """
        if name is None and new_password is None:
            raise ValidationError("at_least_one_of_name_or_new_password_required")
        if new_password is not None and old_password is None:
            raise OldPasswordMismatchError()

        # 第 1 段：纯校验 + 读，不做 mutation（异常不 rollback）
        user = await self.users.get_by_id(db, user_id)
        if user is None or user.version != expected_version:
            raise VersionConflictError()

        if new_password is not None and not verify_password(
            old_password or "", user.password_hash or ""
        ):
            raise OldPasswordMismatchError()

        # 第 2 段：mutation（任何异常必须 rollback 防部分写入）
        try:
            changed_fields: list[str] = []
            if name is not None and name != user.name:
                user.name = name
                changed_fields.append("name")

            password_changed = False
            if new_password is not None:
                user.password_hash = hash_password(new_password)
                user.token_invalidated_at = _now()
                password_changed = True

            if not changed_fields and not password_changed:
                return user

            user.version = (user.version or 1) + 1

            if changed_fields and not password_changed:
                await self.audit.write(
                    db,
                    action_type="user.profile_update",
                    user_id=user.id,
                    metadata={"changed_fields": changed_fields, "ip": ip},
                )

            if password_changed:
                revoked_count = await self.tokens.revoke_all_for_user(db, user.id)
                await self.audit.write(
                    db,
                    action_type="user.password_change",
                    user_id=user.id,
                    metadata={"triggered_by": "self", "ip": ip},
                )
                await self.audit.write(
                    db,
                    action_type="user.all_tokens_revoked",
                    user_id=user.id,
                    metadata={
                        "reason": "password_change",
                        "revoked_count": revoked_count,
                    },
                )
                if changed_fields:
                    await self.audit.write(
                        db,
                        action_type="user.profile_update",
                        user_id=user.id,
                        metadata={"changed_fields": changed_fields, "ip": ip},
                    )

            await db.commit()
            return user
        except Exception:
            await db.rollback()
            raise

    # ─────────────── admin endpoints ───────────────

    async def admin_create_user(
        self,
        db: AsyncSession,
        *,
        admin_id: UUID,
        email: str,
        name: str,
        password: str,
        role: str,
        ip: str | None = None,
    ) -> User:
        if len(password) < MIN_PASSWORD_LEN:
            raise PasswordTooWeakError()
        existing = await self.users.get_by_email(db, email)
        if existing is not None:
            from api.errors.exceptions import EmailAlreadyExistsError

            raise EmailAlreadyExistsError()
        try:
            user = await self.users.create(
                db,
                email=email,
                name=name,
                password_hash=hash_password(password),
                role=role,
                status=UserStatus.ACTIVE.value,
                failed_login_count=0,
                version=1,
            )
            await self.audit.write(
                db,
                action_type="user.admin_create",
                user_id=user.id,
                metadata={"role": role, "created_by": str(admin_id), "ip": ip},
            )
            await db.commit()
            return user
        except Exception:
            await db.rollback()
            raise

    async def admin_list_users(self, db: AsyncSession) -> list[User]:
        return list(await self.users.list_all(db))

    async def admin_update_user(
        self,
        db: AsyncSession,
        *,
        admin_id: UUID,
        target_user_id: UUID,
        expected_version: int,
        role: str | None = None,
        status_: str | None = None,
        ip: str | None = None,
    ) -> User:
        from api.errors.exceptions import (
            InvalidStatusTransitionError,
            LastAdminProtectedError,
            SelfDowngradeForbiddenError,
            UserNotFoundError,
        )

        if role is None and status_ is None:
            raise ValidationError("at_least_one_of_role_or_status_required")

        target = await self.users.get_by_id(db, target_user_id)
        if target is None:
            raise UserNotFoundError()
        if target.version != expected_version:
            raise VersionConflictError()

        # 自降权防护：admin 不能改自己的 role
        if target_user_id == admin_id and role is not None and role != target.role:
            raise SelfDowngradeForbiddenError()

        # 状态转换闸：禁 disabled→pending，且 R4-3a 任何写入 pending 抛 InvalidTransition
        if status_ is not None and status_ != target.status:
            if status_ == UserStatus.PENDING.value:
                raise InvalidStatusTransitionError()
            if target.status == UserStatus.PENDING.value:
                # pending 是预留态，本期 service 拒任何来自 pending 的转换写入
                raise InvalidStatusTransitionError()

        try:
            old_role = target.role
            old_status = target.status
            role_changed = role is not None and role != target.role
            status_changed = status_ is not None and status_ != target.status

            # 禁用最后 admin 保护
            if (
                status_changed
                and status_ == UserStatus.DISABLED.value
                and target.role == "platform_admin"
                and target.status == "active"
            ):
                active_admin_count = await self.users.count_active_admins(db)
                if active_admin_count <= 1:
                    raise LastAdminProtectedError()

            if role_changed:
                target.role = role  # type: ignore[assignment]
            if status_changed:
                target.status = status_  # type: ignore[assignment]

            need_revoke = status_changed and status_ == UserStatus.DISABLED.value
            if need_revoke:
                target.token_invalidated_at = _now()

            if role_changed or status_changed:
                target.version = (target.version or 1) + 1

            if role_changed:
                await self.audit.write(
                    db,
                    action_type="user.admin_update_role",
                    user_id=target.id,
                    metadata={
                        "old_role": old_role,
                        "new_role": role,
                        "admin_id": str(admin_id),
                        "ip": ip,
                    },
                )
            if status_changed:
                await self.audit.write(
                    db,
                    action_type="user.admin_update_status",
                    user_id=target.id,
                    metadata={
                        "old_status": old_status,
                        "new_status": status_,
                        "admin_id": str(admin_id),
                        "ip": ip,
                    },
                )
            if need_revoke:
                revoked_count = await self.tokens.revoke_all_for_user(db, target.id)
                await self.audit.write(
                    db,
                    action_type="user.all_tokens_revoked",
                    user_id=target.id,
                    metadata={
                        "reason": "admin_disable",
                        "revoked_count": revoked_count,
                    },
                )

            await db.commit()
            return target
        except Exception:
            await db.rollback()
            raise

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
        from api.queue.base import SYSTEM_USER_UUID

        # Phase 2.3 cleanup D follow-up: 排除 system user（migration m16 种入 /
        # 只用于 cron/Queue activity_log / 不算"真实运营用户"）。否则 CI fresh DB
        # bootstrap_admin_if_empty 永远看到 system user 在表里 → 返 None 不创建
        result = await db.execute(
            select(UserModel).where(UserModel.id != SYSTEM_USER_UUID).limit(1)
        )
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
