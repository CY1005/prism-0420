"""M18 Embedding Pydantic schema（design §7 line 647-657 + admin endpoints）。

# horizontal: 否（M18 专属）
# owner: M18
# 位置: api/schemas/（横切 schema 层）
# 范畴: EmbedSinglePayload（Queue task）+ admin endpoint schema
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from api.queue.base import TaskPayload  # EmbedSinglePayload 继承
from api.schemas.search_schema import EmbeddingTargetType


class EmbedSinglePayload(TaskPayload):
    """§12D Queue payload（design §7 line 647-657 / 继承 TaskPayload 基类强制 user_id + project_id）。

    注意：source_text 不放 payload——worker 内调上游 Service 拉取，避免大 payload 塞爆 Redis
    （design §12D line 954 字面）。
    """

    model_config = ConfigDict(extra="forbid")

    target_type: EmbeddingTargetType
    """强类型枚举（非裸 str）。"""
    target_id: UUID
    provider: str
    """调度时锁定的 provider（如 'openai'）。"""
    model_name: str
    """★ fix v4.1 R5'=B 新增：调度时锁定的 model_name（如 'text-embedding-3-small'）。"""
    model_version: str
    """调度时锁定的业务版本号（如 'v1'）。"""
    enqueued_by: Literal["incremental", "backfill", "model_upgrade"]
    """★ 限定取值（用于监控/告警按来源分桶）。"""


# ─── Admin endpoint schema ─────────────────────────────────────────────────


class BackfillRequest(BaseModel):
    """POST /api/admin/embedding/backfill 请求（platform_admin only）。

    继承 BaseModel（非 TaskPayload）：HTTP request body 不应含 user_id（来自 JWT）
    + project_id 来自 body 显式传参（不来自 URL / 符合 ADR-002 + ADR-004 R1 fix #1）。
    """

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    """要 backfill 的项目（必填 / tenant 隔离）。"""
    provider: str | None = None
    """None = 用当前 env EMBEDDING_PROVIDER。"""
    model_name: str | None = None
    model_version: str | None = None


class BackfillResponse(BaseModel):
    """POST /api/admin/embedding/backfill 响应（202 Accepted）。

    继承 BaseModel（非 TaskPayload）：HTTP 响应无需强制 user_id + project_id（R1 fix #1）。
    """

    model_config = ConfigDict(extra="forbid")

    enqueued_count: int
    """本次 enqueue 的 task 数量。"""
    message: str = "Backfill enqueued"


class ModelUpgradeRequest(BaseModel):
    """POST /api/admin/embedding/model-upgrade 请求（platform_admin only）。

    继承 BaseModel（非 TaskPayload）：HTTP request body 不应含 user_id（来自 JWT）
    （ADR-002 + ADR-004 R1 fix #1）。
    """

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    new_provider: str
    new_model_name: str
    new_model_version: str


class ModelUpgradeResponse(BaseModel):
    """POST /api/admin/embedding/model-upgrade 响应（202 Accepted）。

    继承 BaseModel（非 TaskPayload）：HTTP 响应无需强制 user_id + project_id（R1 fix #1）。
    """

    model_config = ConfigDict(extra="forbid")

    enqueued_count: int
    old_triple: tuple[str, str, str]
    """(provider, model_name, model_version) 旧三元组。"""
    new_triple: tuple[str, str, str]
    """(provider, model_name, model_version) 新三元组。"""
    message: str = "Model upgrade enqueued"


class EmbeddingStatsResponse(BaseModel):
    """GET /api/admin/embedding/stats 响应（platform_admin only）。

    继承 BaseModel（非 TaskPayload）：HTTP 响应无需强制 user_id + project_id（R1 fix #1）。
    """

    model_config = ConfigDict(extra="forbid")

    total_embeddings: int
    pending_tasks: int
    failed_last_hour: int
    model_version_distribution: dict[str, int]
    """key = '{provider}/{model_name}/{model_version}', value = count。"""


__all__ = [
    "EmbedSinglePayload",
    "BackfillRequest",
    "BackfillResponse",
    "ModelUpgradeRequest",
    "ModelUpgradeResponse",
    "EmbeddingStatsResponse",
]
