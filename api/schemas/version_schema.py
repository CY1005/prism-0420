"""M05 版本时间线 Pydantic schema — design §7."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ChangeType = Literal["added", "modified", "deprecated", "split", "merged", "migrated"]
ReleaseMode = Literal["release", "continuous"]


class VersionCreate(BaseModel):
    version_label: str = Field(..., min_length=1, max_length=64)
    summary: str = Field(..., min_length=1, max_length=500)
    details: str | None = None
    change_type: ChangeType = "added"
    release_mode: ReleaseMode = "release"
    is_current: bool = False
    snapshot_data: dict[str, Any] | None = None


class VersionUpdate(BaseModel):
    """元数据更新（PUT）；snapshot_data 不可改（design Q3：快照是历史事实）。"""

    summary: str | None = Field(None, min_length=1, max_length=500)
    details: str | None = None
    change_type: ChangeType | None = None
    release_mode: ReleaseMode | None = None


class VersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    node_id: UUID
    project_id: UUID
    version_label: str
    summary: str
    details: str | None
    change_type: str
    is_current: bool
    release_mode: str
    snapshot_data: dict[str, Any] | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class VersionListResponse(BaseModel):
    items: list[VersionResponse]
    total: int
