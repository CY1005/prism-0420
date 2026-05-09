"""M02 项目管理 SQLAlchemy 模型（design/02-modules/M02-project/00-design.md §3）。

4 表：projects / project_members / project_dimension_configs / dimension_types

# 实施期处理段引用：
# A1=C 中间态：projects.team_id 是 UUID nullable 但 **不挂 ForeignKey**（teams 表 M20 才存在）；
#              M20 sprint 启用 FK ondelete=RESTRICT。详 design §3.X A1。
# A2=A 现在建：rrf_k + similarity_threshold + 2 CHECK 约束本期落地（M18 baseline-patch）。详 design §3.X A2。
# R3-6-B：dimension_types 表必种 1 条 key='default' 行（alembic data migration 同 revision 落地）。
"""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class MemberRole(StrEnum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


_PROJECT_STATUSES = ("active", "archived")
_MEMBER_ROLES = ("owner", "editor", "viewer")


def _ck_in(name: str, column: str, values: tuple[str, ...]) -> CheckConstraint:
    quoted = ", ".join(f"'{v}'" for v in values)
    return CheckConstraint(f"{column} IN ({quoted})", name=name)


def _default_hierarchy_labels() -> list[str]:
    return ["层级1", "层级2", "层级3"]


class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("name <> ''", name="ck_project_name_not_empty"),
        _ck_in("ck_project_status", "status", _PROJECT_STATUSES),
        # G3 部分唯一索引：同 owner 下 active 项目名唯一（archived 释放 name）
        Index(
            "uq_project_owner_name_active",
            "owner_id",
            "name",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        # M18 baseline-patch（A2=A 现在建）
        CheckConstraint("rrf_k > 0 AND rrf_k <= 200", name="ck_project_rrf_k_range"),
        CheckConstraint(
            "similarity_threshold >= 0.0 AND similarity_threshold <= 1.0",
            name="ck_project_similarity_threshold_range",
        ),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ProjectStatus.ACTIVE.value
    )
    template_type: Mapped[str] = mapped_column(String(50), nullable=False, default="custom")
    hierarchy_labels: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=_default_hierarchy_labels
    )
    version_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="release")
    ai_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_api_key_enc: Mapped[str | None] = mapped_column(
        String(1000), nullable=True
    )  # AES-256-GCM base64
    owner_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    # M20 sprint（2026-05-09）：启用 FK ondelete=RESTRICT（Q8=B 强制前置迁出 / 删 team
    # 前 SELECT FOR UPDATE projects WHERE team_id=tid 必须为空 / 否则 422 TEAM_HAS_PROJECTS）。
    # 原 A1=C 中间态（仅 UUID nullable 列不挂 ForeignKey）已升级。
    team_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    # M18 baseline-patch（A2=A 现在建）
    rrf_k: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    similarity_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)

    members: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember", back_populates="project", cascade="all, delete-orphan"
    )
    dimension_configs: Mapped[list["ProjectDimensionConfig"]] = relationship(
        "ProjectDimensionConfig", back_populates="project", cascade="all, delete-orphan"
    )


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_member"),
        _ck_in("ck_member_role", "role", _MEMBER_ROLES),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=MemberRole.VIEWER.value)
    invited_by: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    project: Mapped["Project"] = relationship("Project", back_populates="members")


class ProjectDimensionConfig(Base):
    __tablename__ = "project_dimension_configs"
    __table_args__ = (
        UniqueConstraint("project_id", "dimension_type_id", name="uq_proj_dim_config"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dimension_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("dimension_types.id"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    project: Mapped["Project"] = relationship("Project", back_populates="dimension_configs")


class DimensionType(Base):
    __tablename__ = "dimension_types"
    __table_args__ = (UniqueConstraint("key", name="uq_dimension_type_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    icon: Mapped[str] = mapped_column(String(100), nullable=False, default="FileText")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    field_schema: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
