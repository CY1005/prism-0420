"""M11 冷启动 Pydantic schema — design/02-modules/M11-cold-start/00-design.md §7。

文件由 FastAPI UploadFile 接收，不在 Pydantic schema 内（multipart/form-data）。
G6 决策：固定模板列名（不支持自定义列映射）。
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ColdStartStatusEnum(StrEnum):
    PENDING = "pending"
    VALIDATING = "validating"
    IMPORTING = "importing"
    COMPLETED = "completed"
    FAILED = "failed"


class CsvRowError(BaseModel):
    row: int
    field: str
    message: str


class ColdStartTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    user_id: UUID
    source_filename: str
    status: ColdStartStatusEnum
    total_rows: int
    success_rows: int
    failed_rows: int
    created_at: datetime
    completed_at: datetime | None = None


class ColdStartTaskDetailResponse(ColdStartTaskResponse):
    error_report: list[CsvRowError] | None = None


class ColdStartTaskListResponse(BaseModel):
    items: list[ColdStartTaskResponse]
    total: int
