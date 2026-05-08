"""M06 Pydantic schemas — design/02-modules/M06-competitor/00-design.md §7.

8 endpoints schemas：
  - Competitor 全局：CompetitorCreate / CompetitorUpdate / CompetitorResponse /
    CompetitorListResponse
  - CompetitorRef 节点级：CompetitorRefCreate / CompetitorRefUpdate /
    CompetitorRefResponse / CompetitorRefListResponse
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProsAndCons(BaseModel):
    pros: list[str] = []
    cons: list[str] = []


# ─────────────── Competitor 全局 ───────────────


class CompetitorCreate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=128)
    website_url: str | None = Field(None, max_length=512)
    description: str | None = None


class CompetitorUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=128)
    website_url: str | None = None
    description: str | None = None


class CompetitorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    display_name: str
    website_url: str | None
    description: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class CompetitorListResponse(BaseModel):
    items: list[CompetitorResponse]
    total: int


# ─────────────── CompetitorRef 节点级 ───────────────


class CompetitorRefCreate(BaseModel):
    competitor_id: UUID
    competitor_version: str | None = Field(None, max_length=64)
    feature_coverage: str | None = None
    tech_approach: str | None = None
    pros_and_cons: ProsAndCons | None = None


class CompetitorRefUpdate(BaseModel):
    competitor_version: str | None = Field(None, max_length=64)
    feature_coverage: str | None = None
    tech_approach: str | None = None
    pros_and_cons: ProsAndCons | None = None


class CompetitorRefResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    node_id: UUID
    competitor_id: UUID
    project_id: UUID
    competitor_version: str | None
    feature_coverage: str | None
    tech_approach: str | None
    pros_and_cons: dict[str, Any] | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class CompetitorRefListResponse(BaseModel):
    items: list[CompetitorRefResponse]
    total: int
