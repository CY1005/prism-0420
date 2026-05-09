"""M04 维度记录 SQLAlchemy 模型（design/02-modules/M04-feature-archive/00-design.md §3）。

1 表：dimension_records（节点 × 维度类型 → JSONB content + 乐观锁）

# Scaffold 简化决策（2026-05-07，子片 1 — A5 get_for_embedding A 路径）
# ① 决策内容：M04 sprint 期 create/update/delete commit 后**不调** embedding_service.enqueue
# ② 简化理由：M18 own embedding_service 在 M04 sprint 期不存在（B caller）；
#             按 design §6.X A5 主标准 Q1 否 + Q2 caller → B 推迟
# ③ 由 M18 sprint 扩齐：DimensionService 三处 commit 后尾调
#    embedding_service.enqueue(target_type="dimension_record", target_id, project_id, user_id,
#    enqueued_by="incremental")；delete commit 后异步 enqueue_delete + SilentFailure +
#    embedding_failures EMBEDDING_DELETE_FAILED + cleanup cron 兜底
# ④ 触发回写动作：M18 sprint add 调用 + 回归测试 + 回写 M04 §6.X 实施期处理段 status

# project_id 一致性兜底（design §3 决策）：
# service 层创建时强制 record.project_id = node.project_id；
# alembic CHECK 约束 ck_dim_project_id_not_null（NOT NULL 约束 + service 层等值约束）
"""

from typing import Any
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class DimensionRecord(Base, TimestampMixin):
    """dimension_records 表 — 节点的某个维度类型对应一条 JSONB 内容 + 乐观锁版本。

    R3-1：含完整 SQLAlchemy class（design §3 SQLAlchemy block）
    R3-2：无状态字段（design §4 决策：无 status 枚举；version 仅是乐观锁计数器）
    R3-3：project_id 冗余 tenant 字段（design §3 CY 2026-04-21 ack 批量统一）
    """

    __tablename__ = "dimension_records"
    __table_args__ = (
        UniqueConstraint("node_id", "dimension_type_id", name="uq_dim_node_type"),
        # tenant 一致性：service 层强制 record.project_id == node.project_id
        # CHECK NOT NULL 配合 alembic NOT NULL 列约束（PG 14+ generated column 是后续优化）
        CheckConstraint("project_id IS NOT NULL", name="ck_dim_project_id_not_null"),
        Index("ix_dim_node_type", "node_id", "dimension_type_id"),
        Index("ix_dim_project_updated", "project_id", "updated_at"),
        # M-CLEANUP（cross-sprint #13 立修 / M04 R1-A A2）：(updated_by, updated_at) 联合索引
        # activity_stream 时间线按 user 视角查询性能基线（M13/M14 写大量行的源表）
        Index("ix_dim_updated_by_updated_at", "updated_by", "updated_at"),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    node_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dimension_type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("dimension_types.id"),
        nullable=False,
    )
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    # 乐观锁；UPDATE 时 WHERE version=expected，rows=0 → ConflictError
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    updated_by: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    node = relationship("Node", back_populates="dimension_records")
