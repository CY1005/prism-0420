"""M02 Pydantic schemas + SearchConfig (A 路径子选项实证: M02 own raw types).

设计来源: design/02-modules/M02-project/00-design.md §7。

A 路径子选项 (5 步法决): SearchConfig 类型 owner = M02 own (本文件)
- 理由: M18 是下游 caller, 依赖方向 M18→M02 符合分层; 建 horizontal shared.py 仅为 1 类型 = YAGNI
- 登记: design/audit/m02-pilot-template-validation.md (子片 5)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectStatusEnum(StrEnum):
    active = "active"
    archived = "archived"


class MemberRoleEnum(StrEnum):
    owner = "owner"
    editor = "editor"
    viewer = "viewer"


# ─── Project ────────────────────────────────────────


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    template_type: str = Field("custom", max_length=50)
    hierarchy_labels: list[str] | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    hierarchy_labels: list[str] | None = None
    version_mode: str | None = None


class AiProviderUpdate(BaseModel):
    ai_provider: str | None = Field(None, max_length=50)
    ai_api_key: str | None = Field(None, max_length=500)  # 明文; service 加密存


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    status: ProjectStatusEnum
    template_type: str
    hierarchy_labels: list[str]
    version_mode: str
    ai_provider: str | None
    owner_id: UUID
    team_id: UUID | None
    created_at: datetime
    updated_at: datetime
    # ai_api_key_enc 不返回


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int


# ─── Member ─────────────────────────────────────────


class MemberInvite(BaseModel):
    user_id: UUID
    role: MemberRoleEnum = MemberRoleEnum.viewer


class MemberRoleUpdate(BaseModel):
    role: MemberRoleEnum


class MemberResponse(BaseModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    user_name: str  # join from users (R2 P1: design §7 行 642)
    user_email: str  # join from users (R2 P1: design §7 行 643)
    role: MemberRoleEnum
    invited_by: UUID | None
    joined_at: datetime
    created_at: datetime  # R2 P1: design §7 行 647


class MemberListResponse(BaseModel):
    items: list[MemberResponse]


# ─── DimensionConfig ────────────────────────────────


class DimensionConfigItem(BaseModel):
    dimension_type_id: int
    enabled: bool
    sort_order: int = 0


class DimensionConfigBatchUpdate(BaseModel):
    configs: list[DimensionConfigItem]


class DimensionConfigResponse(BaseModel):
    id: int
    project_id: UUID
    dimension_type_id: int
    dimension_type_key: str  # join from dimension_types (R2 P1: design §7 行 668)
    dimension_type_name: str  # join from dimension_types (R2 P1: design §7 行 669)
    enabled: bool
    sort_order: int


class DimensionConfigListResponse(BaseModel):
    items: list[DimensionConfigResponse]


# ─── SearchConfig (M18 baseline-patch caller; A 路径 M02 own) ───


@dataclass(frozen=True)
class SearchConfig:
    """M18 SearchService.hybrid_search 入口取的 RRF 融合参数 (design §3 / §6)."""

    rrf_k: int
    similarity_threshold: float
