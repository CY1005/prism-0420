"""M14 Pydantic schemas — design/02-modules/M14-industry-news/00-design.md §7。

⚠️ 全局豁免：所有 schema **无 project_id 字段**——M14 是全局共享数据。
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_serializer, field_validator

# R1-C P1-3 立修（2026-05-08）：tags 单元素长度约束（与 title max_length=200 严密性一致）。
_TAG_MAX_LENGTH = 50


def _check_tag_lengths(tags: list[str] | None) -> list[str] | None:
    if tags is None:
        return tags
    for t in tags:
        if len(t) > _TAG_MAX_LENGTH:
            raise ValueError(f"Each tag must be <= {_TAG_MAX_LENGTH} chars, got {len(t)}")
    return tags


class NewsCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    summary: str | None = None
    source_url: AnyHttpUrl | None = Field(None, description="URL 格式校验（design §14 E6）")
    published_date: date | None = None
    tags: list[str] = Field(default_factory=list)
    # source_type 固定为 'manual'，不暴露给用户；service 层强制（design §3）

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, v: list[str]) -> list[str]:
        return _check_tag_lengths(v) or []

    @field_serializer("source_url")
    def _ser_url(self, v: AnyHttpUrl | None) -> str | None:
        return str(v) if v is not None else None


class NewsUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    summary: str | None = None
    source_url: AnyHttpUrl | None = None
    published_date: date | None = None
    tags: list[str] | None = None

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, v: list[str] | None) -> list[str] | None:
        return _check_tag_lengths(v)

    @field_serializer("source_url")
    def _ser_url(self, v: AnyHttpUrl | None) -> str | None:
        return str(v) if v is not None else None


class NodeRef(BaseModel):
    """关联功能项简要信息（design §7 NewsResponse.linked_nodes 元素）。"""

    node_id: UUID
    node_name: str
    project_id: UUID  # 跨项目关联允许（design §1 灰区 2），返回项目归属便于前端区分


class NewsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    summary: str | None
    source_url: str | None
    published_date: date | None
    source_type: str
    tags: list[str]
    linked_nodes: list[NodeRef] = Field(default_factory=list)
    created_by: UUID
    created_by_name: str | None = None
    created_at: datetime
    updated_at: datetime


class NewsListResponse(BaseModel):
    items: list[NewsResponse]
    total: int
    page: int
    page_size: int


class NewsNodeLinkCreate(BaseModel):
    node_id: UUID


class NewsNodeLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    news_id: UUID
    node_id: UUID
    node_name: str
    linked_by: UUID
    linked_at: datetime
