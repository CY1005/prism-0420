"""M12 功能对比矩阵 SQLAlchemy 模型（design/02-modules/M12-comparison/00-design.md §3）。

2 表：
- comparison_snapshots（快照主表 / 含 nodes_ref + dimensions_ref 元数据 + version 乐观锁）
- comparison_snapshot_items（G4=B 值快照明细 / node_id ON DELETE SET NULL 不降级）

设计要点（design §3）：
- G2/G4：无 status 字段（快照无状态最小集）；G4=B 值快照（保存时拷贝 content 副本）
- G2 Q2：保留 version 字段（rename 并发乐观锁）
- R3-3：project_id 冗余 tenant 字段
- G4=B 节点删除策略：comparison_snapshot_items.node_id ON DELETE SET NULL（快照仍展示原值）
- G7-M12-R2-09：nodes_ref 存 list[str(UUID)]，service 层做 str↔UUID 转换
"""

from datetime import datetime
from typing import Any
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class ComparisonSnapshot(Base, TimestampMixin):
    """comparison_snapshots 表（design §3 主表 / G2 无 status / G4=B 值快照）。"""

    __tablename__ = "comparison_snapshots"
    __table_args__ = (
        Index("ix_comparison_snapshot_project", "project_id"),
        Index("ix_comparison_snapshot_user_project", "user_id", "project_id"),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    nodes_ref: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    dimensions_ref: Mapped[list[int]] = mapped_column(JSONB, nullable=False, default=list)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    items: Mapped[list["ComparisonSnapshotItem"]] = relationship(
        "ComparisonSnapshotItem",
        back_populates="snapshot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]


class ComparisonSnapshotItem(Base):
    """comparison_snapshot_items 表（G4=B 值快照明细）。

    node_id ON DELETE SET NULL（passive_deletes）：节点被删后保留原值副本（不降级）。
    """

    __tablename__ = "comparison_snapshot_items"
    __table_args__ = (
        Index("ix_snapshot_items_snapshot", "snapshot_id"),
        Index("ix_snapshot_items_node", "node_id"),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    snapshot_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comparison_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="SET NULL"),
        nullable=True,
    )
    dimension_type_id: Mapped[int] = mapped_column(
        ForeignKey("dimension_types.id"),
        nullable=False,
    )
    content: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    snapshot_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    snapshot: Mapped[ComparisonSnapshot] = relationship(
        "ComparisonSnapshot", back_populates="items"
    )
