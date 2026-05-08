"""M08 Pydantic schemas — design/02-modules/M08-module-relation/00-design.md §7."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

RelationType = Literal["depends_on", "related_to", "conflicts_with"]


class RelationCreate(BaseModel):
    source_node_id: UUID
    target_node_id: UUID
    relation_type: RelationType
    notes: str | None = None
    # R2 P1-01 立修（M02-M07 service-only 范式延续）：self_loop 校验在 service 层
    # raise RelationSelfLoopError → middleware 翻 code=relation_self_loop。
    # 移除 schema 层 model_validator 避免 Pydantic ValueError 走 FastAPI 默认 422
    # 无 code 字段（design §13 字面 ValidationException Handler 实装 drift / 子片 5
    # design 回写 disambiguation 单层防护）。


class RelationUpdate(BaseModel):
    notes: str | None = None


class RelationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    source_node_id: UUID
    target_node_id: UUID
    relation_type: str
    notes: str | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class RelationListResponse(BaseModel):
    items: list[RelationResponse]
    total: int
