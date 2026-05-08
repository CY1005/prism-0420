"""M06 竞品参考 SQLAlchemy 模型（design/02-modules/M06-competitor/00-design.md §3）。

2 表：
  - competitors（项目级竞品全局实体）
  - competitor_refs（功能项级竞品对标记录；project_id 冗余 tenant 字段）

# project_id 冗余兜底（design §3 CY 2026-04-21 ack）：
# DAO 强制 WHERE competitor_refs.project_id = ?；Service 层创建时强制
# ref.project_id == competitor.project_id（防 cross-project 引用，由
# CompetitorCrossProjectError 拦截）。
"""

from typing import Any
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import (
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class Competitor(Base, TimestampMixin):
    """项目级竞品全局实体（design §3）。

    intentionally no UNIQUE on display_name：允许同一项目多个同名竞品（版本不同）。
    """

    __tablename__ = "competitors"
    __table_args__ = (Index("ix_competitor_project", "project_id"),)

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    website_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    refs: Mapped[list["CompetitorRef"]] = relationship(
        "CompetitorRef",
        back_populates="competitor",
        cascade="all, delete-orphan",
    )


class CompetitorRef(Base, TimestampMixin):
    """功能项级竞品对标记录（design §3）。

    R3-3：project_id 冗余 tenant 字段（DAO 强制 WHERE project_id 过滤）
    """

    __tablename__ = "competitor_refs"
    __table_args__ = (
        UniqueConstraint("node_id", "competitor_id", name="uq_competitor_ref_node_competitor"),
        Index("ix_competitor_ref_node_project", "node_id", "project_id"),
        Index("ix_competitor_ref_project", "project_id"),
        Index("ix_competitor_ref_competitor", "competitor_id"),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    node_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    competitor_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("competitors.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    competitor_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    feature_coverage: Mapped[str | None] = mapped_column(Text, nullable=True)
    tech_approach: Mapped[str | None] = mapped_column(Text, nullable=True)
    pros_and_cons: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="refs")
    node = relationship("Node", back_populates="competitor_refs")
