"""M18 语义搜索 Pydantic schema（design §7 line 625-657）。

# horizontal: 否（M18 search 专属）
# owner: M18
# 位置: api/schemas/（横切 schema 层）
# 范畴: SearchRequest / SearchResultItem / SearchResponse
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EmbeddingTargetType(StrEnum):
    """embedding 目标类型枚举（design §7 + model ck_embeddings_target_type 字面对齐）。"""

    NODE = "node"
    DIMENSION_RECORD = "dimension_record"
    COMPETITOR = "competitor"
    ISSUE = "issue"


# StrEnum 三重防护 tuple（R3-2 字面 / StrEnum + Mapped[str] + tuple）
_EMBEDDING_TARGET_TYPES: tuple[str, ...] = ("node", "dimension_record", "competitor", "issue")


class SearchRequest(BaseModel):
    """POST /api/projects/{project_id}/search 请求 schema（design §7 line 626-630）。

    边界校验全部在 router 层抛 400 INVALID_QUERY_LENGTH（design §7 line 663 字面）；
    Pydantic min_length/ge/le 已移除以保持错误路径单一（B-P2-M18-search-query-validation-returns-422 fix）。
    schema 仅保留类型/枚举校验（target_types 仍走 Pydantic 422，错误类型而非边界值）。
    """

    model_config = ConfigDict(extra="forbid")

    query: str
    """长度 1-200 字符；空 / 超 200 均由 router 抛 400 INVALID_QUERY_LENGTH。"""
    target_types: list[EmbeddingTargetType] | None = None
    """None 表示全部 4 类（不过滤）。"""
    limit: int = 20
    """范围 1-100；越界由 router 抛 400 INVALID_QUERY_LENGTH。"""


class SearchResultItem(BaseModel):
    """单条搜索结果（design §7 line 632-639）。"""

    model_config = ConfigDict(extra="forbid")

    target_type: EmbeddingTargetType
    target_id: UUID
    title: str
    snippet: str
    """关键词高亮 or 语义摘要。"""
    score: float
    """RRF 融合分。"""
    matched_by: list[Literal["keyword", "semantic"]]
    """哪条路径命中（调试透明）。"""
    breadcrumb: list[str]
    """复用 M09 已有。"""


class SearchResponse(BaseModel):
    """搜索响应（design §7 line 641-645）。"""

    model_config = ConfigDict(extra="forbid")

    results: list[SearchResultItem]
    total: int
    search_mode: Literal["hybrid", "keyword_only"]
    """pgvector 不可用时降级 keyword_only（PRD AC4）。"""
    query_embedding_cached: bool
    """调试用：query embedding 是否缓存命中。"""


__all__ = [
    "EmbeddingTargetType",
    "_EMBEDDING_TARGET_TYPES",
    "SearchRequest",
    "SearchResultItem",
    "SearchResponse",
]
