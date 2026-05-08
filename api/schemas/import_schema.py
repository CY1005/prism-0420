"""M17 AI 智能导入 Pydantic schema (design/02-modules/M17-ai-import/00-design.md §7 / §12)。

REST endpoints:
- POST   /api/projects/{pid}/imports                         (multipart 含 file 或 git URL)
- GET    /api/projects/{pid}/imports                         (list)
- GET    /api/projects/{pid}/imports/{task_id}               (detail)
- GET    /api/projects/{pid}/imports/{task_id}/review        (拉 review_data)
- POST   /api/projects/{pid}/imports/{task_id}/confirm       (用户确认 review)
- POST   /api/projects/{pid}/imports/{task_id}/cancel        (取消)
- POST   /api/projects/{pid}/imports/{task_id}/retry         (partial_failed 重试)

WebSocket:
- WS /api/projects/{pid}/imports/{task_id}/progress

design §3 status 11 枚举 + 5 状态明细枚举 + 3 source 枚举（model 字面同步 / R3-2 三重防护）。
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ImportTaskStatusEnum(StrEnum):
    """与 model.ImportTaskStatus 字面同步（status CHECK constraint 三重防护）。"""

    pending = "pending"
    extracting = "extracting"
    ai_step1 = "ai_step1"
    ai_step2 = "ai_step2"
    ai_step3 = "ai_step3"
    awaiting_review = "awaiting_review"
    importing = "importing"
    completed = "completed"
    partial_failed = "partial_failed"
    failed = "failed"
    cancelled = "cancelled"


class ImportTaskItemStatusEnum(StrEnum):
    """与 model.ImportTaskItemStatus 字面同步。"""

    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class ImportSourceTypeEnum(StrEnum):
    """与 model.ImportSourceType 字面同步。"""

    zip = "zip"
    git_url = "git_url"
    git_bundle = "git_bundle"


# ─────────────── Response: 任务 ───────────────


class ImportTaskResponse(BaseModel):
    """单任务响应（list / submit / confirm / retry / cancel 复用）。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    user_id: UUID
    source_type: ImportSourceTypeEnum
    source_hash: str
    source_uri: str  # R2 P1-03 立修：暴露 source_uri 字段，让 e2e 可字面验 sanitize 结果
    status: ImportTaskStatusEnum
    progress: int = Field(..., ge=0, le=100)
    error_message: str | None = None
    ai_provider: str
    ai_model: str
    created_at: datetime
    completed_at: datetime | None = None
    expires_at: datetime | None = None


class ImportTaskItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    file_path: str
    file_size: int
    status: ImportTaskItemStatusEnum
    target_node_id: UUID | None = None
    error_message: str | None = None
    retry_count: int


class ImportTaskListResponse(BaseModel):
    items: list[ImportTaskResponse]
    total: int


class ImportTaskDetailResponse(ImportTaskResponse):
    """detail 含 items + error_metadata（design §7）。"""

    items: list[ImportTaskItemResponse] = Field(default_factory=list)
    error_metadata: dict[str, Any] | None = None


# ─────────────── Review 阶段 ───────────────


class ProposedNode(BaseModel):
    """AI 步骤 1+2 输出的待映射 node（review 阶段展示给用户）。"""

    proposed_id: UUID
    name: str
    type: str = "leaf"
    parent_proposed_id: UUID | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ProposedDimension(BaseModel):
    proposed_id: UUID
    target_proposed_node_id: UUID
    dimension_type_key: str
    content: dict[str, Any]
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ProposedCompetitor(BaseModel):
    proposed_id: UUID
    display_name: str
    website_url: str | None = None
    description: str | None = None


class ProposedIssue(BaseModel):
    proposed_id: UUID
    target_proposed_node_id: UUID | None = None
    title: str
    category: str
    description: str


class ReviewDataResponse(BaseModel):
    """GET /review 响应（AI 步骤 1+2 输出，等用户调整）。"""

    proposed_nodes: list[ProposedNode] = Field(default_factory=list)
    proposed_dimensions: list[ProposedDimension] = Field(default_factory=list)
    proposed_competitors: list[ProposedCompetitor] = Field(default_factory=list)
    proposed_issues: list[ProposedIssue] = Field(default_factory=list)
    confidence_scores: dict[str, float] = Field(default_factory=dict)


# ─────────────── 用户确认 review (POST /confirm) ───────────────


class ConfirmedNode(BaseModel):
    """用户调整后的 node（可改名 / 改父 / 删除）。"""

    proposed_id: UUID
    name: str
    type: str = "leaf"
    parent_proposed_id: UUID | None = None
    skipped: bool = False


class ConfirmedDimension(BaseModel):
    proposed_id: UUID
    target_proposed_node_id: UUID
    dimension_type_key: str
    content: dict[str, Any]


class ConfirmedCompetitor(BaseModel):
    proposed_id: UUID
    display_name: str
    website_url: str | None = None
    description: str | None = None


class ConfirmedIssue(BaseModel):
    proposed_id: UUID
    target_proposed_node_id: UUID | None = None
    title: str
    category: str
    description: str


class ReviewConfirmRequest(BaseModel):
    """POST /confirm 入参——用户调整后的最终映射。"""

    nodes: list[ConfirmedNode] = Field(default_factory=list)
    dimensions: list[ConfirmedDimension] = Field(default_factory=list)
    competitors: list[ConfirmedCompetitor] = Field(default_factory=list)
    issues: list[ConfirmedIssue] = Field(default_factory=list)
    skip_proposed_ids: list[UUID] = Field(default_factory=list)


# ─────────────── WebSocket 事件 schema ───────────────


class ProgressEvent(BaseModel):
    """服务器 → 客户端事件（design §7）。"""

    type: Literal["progress_update", "status_change", "error", "review_ready", "completed"]
    task_id: UUID
    progress: int = Field(..., ge=0, le=100)
    status: ImportTaskStatusEnum
    message: str = ""
    metadata: dict[str, Any] | None = None


class ClientCommand(BaseModel):
    """客户端 → 服务器命令（design §7 / §8 audit B6 修复——每命令 task_id 重校）。"""

    type: Literal["cancel", "ping"]
    task_id: UUID


__all__ = [
    "ClientCommand",
    "ConfirmedCompetitor",
    "ConfirmedDimension",
    "ConfirmedIssue",
    "ConfirmedNode",
    "ImportSourceTypeEnum",
    "ImportTaskDetailResponse",
    "ImportTaskItemResponse",
    "ImportTaskItemStatusEnum",
    "ImportTaskListResponse",
    "ImportTaskResponse",
    "ImportTaskStatusEnum",
    "ProgressEvent",
    "ProposedCompetitor",
    "ProposedDimension",
    "ProposedIssue",
    "ProposedNode",
    "ReviewConfirmRequest",
    "ReviewDataResponse",
]
