"""M07 问题沉淀 SQLAlchemy 模型（design/02-modules/M07-issue/00-design.md §3）。

1 表：issues（项目级 / 可选关联节点；node_id 允许 NULL = 游离 issue）

# orphan 语义（design §3 + R-X2 第三真注入）：
# node_id 是 FK to nodes ON DELETE SET NULL —— node 删除时 issue 不被级联删除，
# 而是 node_id 设 NULL 变"游离 issue"。R-X2 注入 IssueService.orphan_by_node_id 在
# DB FK 之前显式 UPDATE + 写 activity_log 'orphan' 事件。

# 状态机 4 状态（design §4）：
# open / in_progress / resolved / closed
# 转换由 Service 层 SELECT FOR UPDATE 行锁串行化 + status 校验
"""

from datetime import datetime
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class Issue(Base, TimestampMixin):
    """issues 表（design §3 SQLAlchemy block）。

    R3-1：含完整 SQLAlchemy class
    R3-2：status / category 三重防护（Text + CheckConstraint + Mapped[str]）
    R3-3：project_id 冗余 tenant 字段
    R10-1：批量 orphan_by_node_id 写 N 条独立 activity_log
    """

    __tablename__ = "issues"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved', 'closed')",
            name="ck_issue_status",
        ),
        CheckConstraint(
            "category IN ('bug', 'tech_debt', 'design_flaw', 'performance')",
            name="ck_issue_category",
        ),
        Index("ix_issue_project_status", "project_id", "status"),
        Index("ix_issue_node_project", "node_id", "project_id"),
        Index("ix_issue_project_category", "project_id", "category"),
        Index("ix_issue_created_by", "created_by"),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    # ON DELETE SET NULL：node 删除时 issue 变游离（不级联删除）
    node_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="SET NULL"),
        nullable=True,
    )
    category: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True, default=list)
    created_by: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    # in_progress 时必填（service 层校验 IssueAssigneeRequiredError）
    assigned_to: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Node 端反向：design §3 + orphan 语义
    # 不带 cascade='all, delete-orphan'（与 M04/M06 不同）— FK ON DELETE SET NULL DB 兜底
    # passive_deletes=True 让 SQLAlchemy 不在 Node 删除时主动 UPDATE issues
    node = relationship("Node", back_populates="issues")
