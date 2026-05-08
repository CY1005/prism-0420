"""注册所有 ORM model 到 Base.metadata（Alembic autogenerate 依赖）。"""

from api.models.base import Base, ImmutableMixin, SoftDeleteMixin, TimestampMixin
from api.models.cold_start_task import ColdStartStatus, ColdStartTask
from api.models.comparison_snapshot import ComparisonSnapshot, ComparisonSnapshotItem
from api.models.competitor import Competitor, CompetitorRef
from api.models.dimension_record import DimensionRecord
from api.models.issue import ISSUE_CATEGORIES, ISSUE_STATUSES, Issue
from api.models.module_relation import ModuleRelation, RelationTypeEnum
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
from api.models.version_record import VersionRecord

__all__ = [
    "AuthAuditLog",
    "AuthIdentity",
    "Base",
    "ColdStartStatus",
    "ColdStartTask",
    "ComparisonSnapshot",
    "ComparisonSnapshotItem",
    "Competitor",
    "CompetitorRef",
    "DimensionRecord",
    "DimensionType",
    "EmailChangeRequest",
    "ISSUE_CATEGORIES",
    "ISSUE_STATUSES",
    "ImmutableMixin",
    "InviteCode",
    "Issue",
    "MemberRole",
    "ModuleRelation",
    "RelationTypeEnum",
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
    "VersionRecord",
]
