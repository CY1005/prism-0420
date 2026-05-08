"""M16 AI 快照 Pydantic schema (design §7 / §12B)。

REST endpoints:
- POST /api/projects/{pid}/nodes/{nid}/snapshot/generate (202)
- GET /api/snapshot-tasks/{task_id} (独立路径 / Q7 子 ack A)
- POST /api/projects/{pid}/nodes/{nid}/snapshot/save

design §3 status 5 枚举（pending/running/succeeded/failed/cancelled-预留）。
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AISnapshotTaskStatusEnum(StrEnum):
    """与 model.AISnapshotTaskStatus 字面同步（status CHECK constraint 三重防护）。"""

    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


# ─────────────── Internal context (Service 内存聚合 / 不暴露 API) ───────────────


class VersionRecordSummary(BaseModel):
    """M05 list_by_node 返回的 DTO 子集（design §3 字面）。"""

    id: UUID
    version_label: str
    description: str | None = None
    created_at: datetime


class DimensionRecordSummary(BaseModel):
    """M04 list_by_node 返回的 DTO 子集。"""

    dimension_type_key: str
    content: dict[str, Any]


class AISnapshotContext(BaseModel):
    """AI 生成前 M16 Service 层聚合上游数据的内存结构（design §3 / 不入库 / 不暴露 API）。"""

    node_name: str
    versions: list[VersionRecordSummary]
    current_dimensions: list[DimensionRecordSummary]
    dimension_keys: list[str]


# ─────────────── Response: POST /generate ───────────────


class SnapshotTaskCreatedResponse(BaseModel):
    """POST /generate 立即返回的 202 响应（design §7）。"""

    task_id: UUID
    status: AISnapshotTaskStatusEnum
    is_idempotent_hit: bool  # true = 复用已有任务（5min 内 + 同 version_count）
    poll_url: str  # 前端直接 GET 此 URL（含 host 路径）
    estimated_duration_seconds: int = 90  # UX 提示，非硬契约


# ─────────────── Response: GET /snapshot-tasks/{id} ───────────────


class SnapshotReviewDimension(BaseModel):
    """review_data.dimensions 单条（design §3 review_data JSONB schema）。"""

    dimension_type_key: str = Field(..., min_length=1)
    name: str
    content: dict[str, Any]


class SnapshotReviewData(BaseModel):
    """review_data JSONB 整体结构（succeeded 时填）。"""

    summary: str
    dimensions: list[SnapshotReviewDimension]


class SnapshotTaskDetailResponse(BaseModel):
    """GET /snapshot-tasks/{task_id} 响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    node_id: UUID
    user_id: UUID
    status: AISnapshotTaskStatusEnum
    version_count: int
    ai_provider: str
    ai_model: str
    review_data: SnapshotReviewData | None = None
    error_code: str | None = None
    error_message: str | None = None
    completed_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime


# ─────────────── Request/Response: POST /save ───────────────


class SnapshotSaveRequest(BaseModel):
    """POST /save 入参（design §7）。"""

    task_id: UUID  # 必须传；service 会校验 task.project_id/node_id 与 URL path 一致（防跨 node 攻击 / audit M5）
    save_summary: bool = True  # 用户是否要保存 summary 到 dimension_records
    selected_dimension_keys: list[str] = Field(
        default_factory=list,
        description="勾选要保存的维度 key（必须是 review_data.dimensions 子集）",
    )


class SnapshotSaveResponse(BaseModel):
    saved_dimension_record_ids: list[UUID]
    saved_count: int
    summary_saved: bool
