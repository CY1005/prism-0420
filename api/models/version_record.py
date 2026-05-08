"""M05 版本演进时间线 SQLAlchemy 模型（design/02-modules/M05-version-timeline/00-design.md §3）。

1 表：version_records（节点版本快照；project_id 冗余 tenant 字段）

# 索引设计（M05 sprint 闸门 2.5 A6 升级 / B1 候选 C 实证 / 2026-05-08）：
# 主查询路径 list_by_node 是 ORDER BY created_at DESC + LIMIT —— covering 范式要求
# 索引尾部含 created_at；§3 原列出的 (node_id, project_id) 升级为
# (node_id, project_id, created_at DESC)，一索引服务主查询 + 时间线排序 + tenant 过滤。
# §6 R-X3 段引用的 ix_version_records_node_created 已统一为本索引名 ix_version_node_proj_created。

# project_id 冗余 tenant 字段（design §3 CY 2026-04-21 ack 批量统一）：
# DAO 强制 WHERE version_records.project_id = ?；Service 层创建时强制
# record.project_id == node.project_id。
"""

from typing import Any
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class VersionRecord(Base, TimestampMixin):
    """version_records — 节点版本快照（design §3 SQLAlchemy block）。

    R3-1：含完整 SQLAlchemy class
    R3-2：change_type / release_mode 三重防护（Text + CheckConstraint + Mapped[str]）；
          is_current 是布尔标记（design §4 决策：无 status 枚举）
    R3-3：project_id 冗余 tenant 字段
    """

    __tablename__ = "version_records"
    __table_args__ = (
        UniqueConstraint("node_id", "version_label", name="uq_version_node_label"),
        CheckConstraint(
            "change_type IN ('added', 'modified', 'deprecated', 'split', 'merged', 'migrated')",
            name="ck_version_change_type",
        ),
        CheckConstraint(
            "release_mode IN ('release', 'continuous')",
            name="ck_version_release_mode",
        ),
        # A6 covering 主索引：服务 list_by_node ORDER BY created_at DESC + LIMIT
        # + tenant 过滤；闸门 2.5 B1 候选 C 实证（M02-M04 covering 范式延续）
        Index(
            "ix_version_node_proj_created",
            "node_id",
            "project_id",
            text("created_at DESC"),
        ),
        Index("ix_version_project", "project_id"),
        # PG 部分唯一索引：DB 层兜底"同一 node 最多 1 条 is_current=true"
        Index(
            "uq_version_node_is_current",
            "node_id",
            unique=True,
            postgresql_where=text("is_current = true"),
        ),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    node_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_label: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_type: Mapped[str] = mapped_column(Text, nullable=False, default="added")
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    snapshot_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    release_mode: Mapped[str] = mapped_column(Text, nullable=False, default="release")
    created_by: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    node = relationship("Node", back_populates="version_records")
