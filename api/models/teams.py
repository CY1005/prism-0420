"""M20 团队 SQLAlchemy 模型（design/02-modules/M20-team/00-design.md §3）。

2 表：
- teams（团队主表 / Q9=A 乐观锁 version / Q13=C creator_id 永不变）
- team_members（团队成员表 / Q2=B 三角色 owner/admin/member / Q13.1②=B RESTRICT FK）

设计要点（design §3.2 + §3.5）：
- R3-2 三重防护（team_members.role）：Mapped[TeamRole] + String(20) + CheckConstraint role IN (...)
  / 与 M02-M19 11 模块同款范式 / 避免 model 反向依赖 schema 引循环 import
- R3-4 改回成本块见 design §3.5（11 项核心决策反悔代价）
- TimestampMixin 不继承（design frontmatter line 56-57 字面：no_dependency mixin /
  Team/TeamMember 直接声明 created_at / updated_at / joined_at 列）
- Team.creator_id ondelete=RESTRICT（Q13.1②a / 强不变量：creator 不可随便删 / 删 user
  时校验链 USER_HAS_OWNED_TEAMS / M01 baseline-patch 提议）
- TeamMember.team_id ondelete=RESTRICT（Q13.1②b / Q8=B 强制前置迁出 / 删 teams 行前
  Service 层显式 5 步删除）
- TeamMember.user_id ondelete=CASCADE（与 M01 用户删除范式对齐 / 删 user 自动清其
  team_members 行）
- UniqueConstraint(creator_id, name)（Q13.1①=A 同 creator 下唯一 / B5/B5b 测试覆盖）
- UniqueConstraint(team_id, user_id)（防重复加同 user / E8/B11 测试覆盖）
- ix_team_members_user_team 反向索引（高频「U 所在所有 team」查询 / L1 require_team_access +
  L3 user_accessible_project_ids_subquery 子查询性能基线）

R10-2 横切 owner = M15 activity_log（M20 仅枚举字符串值 / accepted 后 baseline-patch 已落地
api/models/activity_log.py:_ACTION_TYPES + _TARGET_TYPES）。
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base


class TeamRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


_TEAM_ROLES = ("owner", "admin", "member")


class Team(Base):
    """teams 主表（design §3.2 / Q9=A 乐观锁 / Q13=C creator_id 永不变）。

    R3-1：含完整 SQLAlchemy class
    R3-3：N/A（M20 不属于 project tenant / team 自身是 tenant 容器）
    """

    __tablename__ = "teams"
    __table_args__ = (
        # Q13.1①=A 同 creator 下唯一（不同 creator 可同名 / B5+B5b 测试覆盖）
        UniqueConstraint("creator_id", "name", name="uq_teams_creator_name"),
        # name 长度约束 1-100（B1 测试：空 / 101 字符 → 422）
        CheckConstraint(
            "char_length(name) >= 1 AND char_length(name) <= 100",
            name="ck_teams_name_length",
        ),
        # Q9=A 乐观锁 version 非负
        CheckConstraint("version >= 1", name="ck_teams_version_positive"),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    # Q13=C creator_id 永不变（创建者只读 / 与当前 owner 由 team_members.role 单独查询分离）
    # ondelete=RESTRICT：删 user 前必须先 transfer 或删 team（M01 baseline-patch
    # 提议 USER_HAS_OWNED_TEAMS 校验链）
    creator_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Q9=A teams 加乐观锁 version（team_members 不加 / 最后写入获胜）
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # 直接声明 created_at / updated_at（no_dependency mixin / design frontmatter line 56-57）
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Q13.1②=B RESTRICT：删 teams 行前 Service 必须先 DELETE team_members
    # 不级联 delete-orphan —— RESTRICT 强制 Service 层显式 5 步流程
    members: Mapped[list["TeamMember"]] = relationship(
        "TeamMember",
        back_populates="team",
    )


class TeamMember(Base):
    """team_members 成员表（design §3.2 / Q2=B 三角色 / Q13.1②=B RESTRICT）。

    R3-2 三重防护：role 三层（Mapped[TeamRole] + String(20) + CheckConstraint role IN (...)）
    """

    __tablename__ = "team_members"
    __table_args__ = (
        # 防重复加同 user（E8/B11 测试覆盖）
        UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),
        # R3-2 三重防护：role 枚举 CheckConstraint
        CheckConstraint(
            f"role IN ({', '.join(repr(r) for r in _TEAM_ROLES)})",
            name="ck_team_members_role_valid",
        ),
        # 反向索引：高频「U 所在所有 team」查询
        # （L1 require_team_access + L3 user_accessible_project_ids_subquery 性能基线）
        Index("ix_team_members_user_team", "user_id", "team_id"),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    # Q13.1②a=B RESTRICT：删 teams 行前 Service 必须先 DELETE team_members
    team_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Q13.1②b=CASCADE：删 user 时自动清其所有 team_members 行（与 M01 用户删除范式对齐）
    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # R3-2 三重防护：Mapped[TeamRole] + String(20) + CheckConstraint
    role: Mapped[TeamRole] = mapped_column(String(20), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    team: Mapped["Team"] = relationship("Team", back_populates="members")
