"""M03 功能模块树 SQLAlchemy 模型（design/02-modules/M03-module-tree/00-design.md §3）。

1 表：nodes（自关联树形结构 + 物化路径）

# 实施期处理段引用：
# A1 范式校准（M02 R1 已立）：状态/类型字段一律 `Mapped[str]` + StrEnum.value default
#                              + DB CHECK，与 M01 user.py / M02 project.py 一致；
#                              design §3 字面 `Mapped[NodeType]` 是 sprint 末 R1 punt
#                              回写差异（与 M02 R1 P1/P2 第 2 行同款）。
# A2 reconcile 加 `description` 字段（M03 design §6 M18 baseline-patch 拼接 name+description；
#                                     design §3 字面缺 description = 内部矛盾，sprint 末 §3 回写）。
# 跨模块 stub（A3 reconcile）：M03 §6 R-X2 要求 delete_node 调 M04/M06/M07 service，但这些
#                              模块 sprint 期不存在。NodeChildrenServiceProtocol 注入点见
#                              api/services/node_service.py（同 tenant_filter scaffold S2 范式）。
"""

from enum import StrEnum
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class NodeType(StrEnum):
    FOLDER = "folder"
    FILE = "file"


_NODE_TYPES = ("folder", "file")


class Node(Base, TimestampMixin):
    """nodes 表 — 项目内树形导航锚点。

    R3-2 三重防护（NodeType）：String(20) + DB CHECK + StrEnum.value default
    R3-3：project_id 冗余 tenant 字段
    R4-1：无状态字段（G2 决策：硬删除，无 archived）
    G5：path Text 无长度限制；移动子树时 REPLACE path 一条 SQL 批量更新
    """

    __tablename__ = "nodes"
    __table_args__ = (
        Index("ix_nodes_project_parent", "project_id", "parent_id"),
        Index("ix_nodes_project_sort", "project_id", "sort_order"),
        # path text_pattern_ops 索引在 alembic 里建（postgresql_ops 仅 op.create_index 支持）
        CheckConstraint("name <> ''", name="ck_node_name_not_empty"),
        CheckConstraint("depth >= 0", name="ck_node_depth_non_negative"),
        CheckConstraint("sort_order >= 0", name="ck_node_sort_order_non_negative"),
        CheckConstraint(
            f"type IN ({', '.join(repr(v) for v in _NODE_TYPES)})",
            name="ck_node_type",
        ),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # A2 reconcile 加：M18 get_for_embedding 拼接 name + "\n" + description
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    # A1 范式：Mapped[str] + StrEnum.value default + DB CHECK（与 M01/M02 一致）
    type: Mapped[str] = mapped_column(String(20), nullable=False, default=NodeType.FOLDER.value)
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # G5：path 物化路径 "/rootId/parentId/thisId/"，Text 无长度限制
    path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    updated_by: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    children: Mapped[list["Node"]] = relationship(
        "Node",
        back_populates="parent",
        cascade="all, delete-orphan",
        foreign_keys="Node.parent_id",
    )
    parent: Mapped["Node | None"] = relationship(
        "Node",
        back_populates="children",
        remote_side="Node.id",
        foreign_keys="Node.parent_id",
    )
