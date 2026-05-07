"""M01 DAO（async）。

R-X3 精神：DAO 接受外部 session、不自 commit / 不自 begin。
事务由 Service 层 ``async with db.begin():`` 包裹。
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.user import AuthAuditLog, RefreshToken, User


class UserDAO:
    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, db: AsyncSession, user_id: UUID) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def list_all(self, db: AsyncSession) -> Sequence[User]:
        result = await db.execute(select(User).order_by(User.created_at.desc()))
        return result.scalars().all()

    async def create(self, db: AsyncSession, **fields: Any) -> User:
        user = User(**fields)
        db.add(user)
        await db.flush()
        return user

    async def count_active_admins(self, db: AsyncSession) -> int:
        result = await db.execute(
            select(User).where(User.role == "platform_admin", User.status == "active")
        )
        return len(result.scalars().all())


class RefreshTokenDAO:
    async def get_by_hash(self, db: AsyncSession, token_hash: str) -> RefreshToken | None:
        result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        ip: str | None = None,
        user_agent: str | None = None,
        device_info: str | None = None,
    ) -> RefreshToken:
        rt = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            ip=ip,
            user_agent=user_agent,
            device_info=device_info,
        )
        db.add(rt)
        await db.flush()
        return rt

    async def revoke_one(self, db: AsyncSession, token_hash: str) -> int:
        rt = await self.get_by_hash(db, token_hash)
        if rt is None:
            return 0
        await db.delete(rt)
        await db.flush()
        return 1

    async def revoke_all_for_user(self, db: AsyncSession, user_id: UUID) -> int:
        result = await db.execute(select(RefreshToken).where(RefreshToken.user_id == user_id))
        rows = list(result.scalars().all())
        for rt in rows:
            await db.delete(rt)
        await db.flush()
        return len(rows)

    async def touch_last_seen(self, db: AsyncSession, token_hash: str, when: datetime) -> None:
        rt = await self.get_by_hash(db, token_hash)
        if rt is not None:
            rt.last_seen_at = when
            await db.flush()


class AuthAuditLogDAO:
    """INSERT-only。"""

    async def write(
        self,
        db: AsyncSession,
        *,
        action_type: str,
        user_id: UUID | None,
        metadata: dict[str, Any] | None = None,
    ) -> AuthAuditLog:
        row = AuthAuditLog(
            action_type=action_type,
            user_id=user_id,
            metadata_=metadata or {},
        )
        db.add(row)
        await db.flush()
        return row
