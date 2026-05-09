"""M04 Pydantic schemas — design/02-modules/M04-feature-archive/00-design.md §7."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ─────────────── 入参 ───────────────


class DimensionCreate(BaseModel):
    """POST 创建维度记录。"""

    dimension_type_id: int = Field(..., gt=0)
    content: dict[str, Any] = Field(default_factory=dict)


class DimensionUpdate(BaseModel):
    """PUT 更新维度记录（带乐观锁）。"""

    content: dict[str, Any] = Field(default_factory=dict)
    expected_version: int = Field(..., ge=1)


# ─────────────── 出参 ───────────────


class DimensionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    node_id: UUID
    project_id: UUID
    dimension_type_id: int
    content: dict[str, Any]
    version: int
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime
    # M-CLEANUP（cross-sprint #15 立修 / M04 R2 A1 / Phase 2.2 前端真用时立刻触发）：
    # 与 IssueResponse #3 同款契约缺口；前端不需要 N+1 拼接 dim_type_key / updated_by 名
    dimension_type_key: str | None = None
    updated_by_name: str | None = None


class DimensionTypeRef(BaseModel):
    """档案页装配出参：项目启用的维度类型（含未填的）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    name: str
    icon: str
    sort_order: int
    enabled: bool


class DimensionListResponse(BaseModel):
    """档案页主查询：节点已有维度记录 + 项目启用维度类型清单。"""

    items: list[DimensionResponse]
    enabled_dimension_types: list[DimensionTypeRef]


class CompletionResponse(BaseModel):
    enabled_count: int
    filled_count: int
    completion_rate: float
