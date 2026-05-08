"""M08 模块关系图 SQLAlchemy 模型（design/02-modules/M08-module-relation/00-design.md §3）。

1 表：module_relations（节点之间有向关系；CY ack 候选 A 三元组唯一）

# 双向关系策略（design §1 边界灰区 + §3 候选 A）：
# 关联为有向（source → target）；A→B 与 B→A 是不同记录；无向关系（如 related_to）
# 由前端展示层对称显示，后端仅存有向。
# UNIQUE(source, target, type) 三元组：同一对节点允许多种 relation_type 但禁完全重复。

# Node back_populates 策略：design 字面无要求；FK ondelete=CASCADE DB 兜底 +
# R-X2 第四真注入 IssueService.delete_by_node_id 显式调用 + activity_log。
# 不加 Node 端 module_relations relationship（避免 source/target 双 FK 反向歧义）。
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class RelationTypeEnum(StrEnum):
    """CY ack 候选 A（2026-04-21）：3 种枚举够用，可扩展走 Alembic ALTER CHECK。"""

    depends_on = "depends_on"
    related_to = "related_to"
    conflicts_with = "conflicts_with"


class ModuleRelation(Base, TimestampMixin):
    """module_relations 表（design §3 SQLAlchemy block）。

    R3-1：含完整 SQLAlchemy class
    R3-2：relation_type 三重防护（Mapped[Enum] + String(32) + CheckConstraint）
    R3-3：project_id 冗余 tenant 字段
    R10-1：delete_by_node_id 写 N 条独立 activity_log
    """

    __tablename__ = "module_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_node_id",
            "target_node_id",
            "relation_type",
            name="uq_module_relation_src_tgt_type",
        ),
        CheckConstraint(
            "relation_type IN ('depends_on', 'related_to', 'conflicts_with')",
            name="ck_module_relation_type_valid",
        ),
        CheckConstraint(
            "source_node_id != target_node_id",
            name="ck_module_relation_no_self_loop",
        ),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_node_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_node_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    source_node = relationship("Node", foreign_keys=[source_node_id])
    target_node = relationship("Node", foreign_keys=[target_node_id])
