"""M07 Pydantic schemas — design/02-modules/M07-issue/00-design.md §7."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

CategoryLiteral = Literal["bug", "tech_debt", "design_flaw", "performance"]
StatusLiteral = Literal["open", "in_progress", "resolved", "closed"]


class IssueCreate(BaseModel):
    node_id: UUID | None = None
    category: CategoryLiteral
    title: str = Field(..., min_length=1, max_length=256)
    description: str = Field(..., min_length=1)
    tags: list[str] = []
    assigned_to: UUID | None = None


class IssueUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = None
    tags: list[str] | None = None
    node_id: UUID | None = None
    assigned_to: UUID | None = None


class IssueTransition(BaseModel):
    target_status: StatusLiteral
    assigned_to: UUID | None = None
    note: str | None = None


class IssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    node_id: UUID | None
    category: str
    status: str
    title: str
    description: str
    tags: list[str] | None
    created_by: UUID | None
    assigned_to: UUID | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # M-CLEANUP（cross-sprint #3 立修 / M07 R2 P2-1 / Phase 2.2 前端真用时立刻触发）：
    # 列表卡顿防御 — 前端不需要 N+1 拼接 user/node 名 / DAO selectinload 在数据加载期一次性 join
    node_name: str | None = None
    created_by_name: str | None = None
    assigned_to_name: str | None = None


class IssueListResponse(BaseModel):
    items: list[IssueResponse]
    total: int
