"""注册所有 ORM model 到 Base.metadata（Alembic autogenerate 依赖）。"""

from api.models.base import Base, ImmutableMixin, SoftDeleteMixin, TimestampMixin
from api.models.user import (
    AuthAuditLog,
    AuthIdentity,
    EmailChangeRequest,
    InviteCode,
    PasswordResetToken,
    RefreshToken,
    User,
    UserRole,
    UserStatus,
)

__all__ = [
    "AuthAuditLog",
    "AuthIdentity",
    "Base",
    "EmailChangeRequest",
    "ImmutableMixin",
    "InviteCode",
    "PasswordResetToken",
    "RefreshToken",
    "SoftDeleteMixin",
    "TimestampMixin",
    "User",
    "UserRole",
    "UserStatus",
]
