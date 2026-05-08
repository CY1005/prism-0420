"""M12 功能对比矩阵 Pydantic schema — design §7.

G2/G4 决策：无 ComparisonSnapshotStatusEnum（无 status 字段）。
G7-M12-R2-09：nodes_ref 存 list[str(UUID)]（PG JSONB string 形态）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MatrixCell(BaseModel):
    node_id: UUID
    dimension_type_id: int
    content: dict[str, Any] | None  # None = 当时该格未填写


class ComparisonMatrixResponse(BaseModel):
    """实时矩阵渲染（cells 即聚合结果，前端拼 N×M 网格）。"""

    cells: list[MatrixCell]


class SnapshotCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    node_ids: list[UUID] = Field(..., min_length=1)
    dimension_type_ids: list[int] = Field(..., min_length=1)


class SnapshotUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    expected_version: int = Field(..., ge=1)


class SnapshotItemResponse(BaseModel):
    """G4=B 值快照明细（node_id 为 None 表示节点已删但快照保留 content）。"""

    model_config = ConfigDict(from_attributes=True)
    node_id: UUID | None
    dimension_type_id: int
    content: dict[str, Any] | None


class SnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    user_id: UUID
    name: str
    description: str | None
    nodes_ref: list[str]
    dimensions_ref: list[int]
    version: int
    created_at: datetime
    updated_at: datetime


class SnapshotDetailResponse(SnapshotResponse):
    """详情包含 items（G4=B 值快照不降级）。"""

    items: list[SnapshotItemResponse]


class SnapshotListResponse(BaseModel):
    items: list[SnapshotResponse]
    total: int
