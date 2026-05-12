"""M03 Pydantic schemas — design/02-modules/M03-module-tree/00-design.md §7."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NodeTypeEnum(StrEnum):
    folder = "folder"
    file = "file"


# ─────────────── 入参 ───────────────


class NodeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    type: NodeTypeEnum = NodeTypeEnum.folder
    parent_id: UUID | None = None
    sort_order: int | None = Field(None, ge=0)
    description: str | None = Field(None, max_length=2000)


class NodeUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    # design §4: type 不可变更，但显式声明字段以便 service 层抛 NODE_TYPE_IMMUTABLE 422
    # （B-P2-M03-node-type-immutable-not-enforced fix：原 schema 排除法 → Pydantic 静默忽略 → 返 200）
    type: NodeTypeEnum | None = None
    # 注：parent_id 走独立 /move endpoint


class NodeReorderItem(BaseModel):
    node_id: UUID
    sort_order: int = Field(..., ge=0)


class NodeReorder(BaseModel):
    """批量更新同级节点排序——所有 node_id 必须属于同一 parent_id。"""

    parent_id: UUID | None = None
    items: list[NodeReorderItem] = Field(..., min_length=1)


class NodeMove(BaseModel):
    """跨父移动节点（G5）——目标父节点不能是被移动节点的子孙。"""

    new_parent_id: UUID | None = None


# ─────────────── 出参 ───────────────


class NodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    parent_id: UUID | None
    name: str
    description: str | None
    # R2-8 修: design §7 字面 NodeTypeEnum, 实装回归 (前端拿到 enum 类型保证)
    type: NodeTypeEnum
    depth: int
    sort_order: int
    path: str
    created_by: UUID | None
    updated_by: UUID | None
    created_at: datetime
    updated_at: datetime


class NodeWithChildrenResponse(NodeResponse):
    children: list[NodeWithChildrenResponse] = Field(default_factory=list)


class NodeTreeResponse(BaseModel):
    roots: list[NodeWithChildrenResponse]


class NodeListResponse(BaseModel):
    items: list[NodeResponse]


class BreadcrumbItem(BaseModel):
    id: UUID
    name: str
    depth: int


class BreadcrumbResponse(BaseModel):
    items: list[BreadcrumbItem]


NodeWithChildrenResponse.model_rebuild()
