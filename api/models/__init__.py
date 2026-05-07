"""注册所有 ORM model 到 Base.metadata（Alembic autogenerate 依赖）。"""

from api.models.base import Base, ImmutableMixin, SoftDeleteMixin, TimestampMixin
from api.models.node import Node, NodeType
from api.models.project import (
    DimensionType,
    MemberRole,
    Project,
    ProjectDimensionConfig,
    ProjectMember,
    ProjectStatus,
)
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
    "DimensionType",
    "EmailChangeRequest",
    "ImmutableMixin",
    "InviteCode",
    "MemberRole",
    "Node",
    "NodeType",
    "PasswordResetToken",
    "Project",
    "ProjectDimensionConfig",
    "ProjectMember",
    "ProjectStatus",
    "RefreshToken",
    "SoftDeleteMixin",
    "TimestampMixin",
    "User",
    "UserRole",
    "UserStatus",
]
