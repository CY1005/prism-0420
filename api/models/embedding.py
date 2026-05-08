"""M18 语义搜索 SQLAlchemy 模型（design/02-modules/M18-semantic-search/00-design.md §3）。

4 表：
- embeddings（7 字段复合 PK / 3 异维列 / 4 CHECK / 3 ivfflat 索引占位 + 1 filter 索引）
- embedding_failures（失败计数 + 监控源 / R10-2 例外 / 2 索引）
- embedding_tasks（task 跟踪 + zombie 兜底 / 5 状态 / 3 CHECK / 2 索引）
- search_evaluation_log（1% 采样离线评估 / 2 索引）

设计要点：
- R3-2 status 三重防护：Text + CheckConstraint + Mapped[str]（与 M17 范式一致）
- R3-3 project_id 冗余 tenant 字段
- 7 字段复合 PK：(project_id, modality, target_type, target_id, provider, model_name, model_version)
- pgvector 未安装：embedding_512/1536/3072 列暂用 ARRAY(Float) 占位；
  子片 3 安装 pgvector 后回写为 Vector(N) + 同步 __table_args__ ivfflat Index
- ivfflat 索引在 Alembic migration 中用 op.execute() raw SQL 写入（ORM 层注释保留占位）
- ck_embeddings_dim_column_consistency：dim 与 non-NULL 列严格互斥（design line 274-279 字面）
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID as PyUUID

import sqlalchemy as sa
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.models.base import Base, TimestampMixin

# ── EmbeddingTaskStatus（R3-2 第 1 重防护 / StrEnum + _tuple）──────────────


class EmbeddingTaskStatus(StrEnum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    dead_letter = "dead_letter"


_EMBEDDING_TASK_STATUSES = (
    "pending",
    "running",
    "succeeded",
    "failed",
    "dead_letter",
)


def _in_sql_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


# ── 自有表 1：embeddings（7 字段复合 PK + 3 异维列 + 4 CHECK）────────────────


class Embedding(Base, TimestampMixin):
    """M18 embeddings 表（design §3 line 212-308）。

    R3-1：完整 SQLAlchemy class
    R3-2：modality / target_type / provider / dim 四重 CHECK 防护
    R3-3：project_id 冗余 tenant 字段（fix v2 Q5=B）

    注意：embedding_512/1536/3072 暂用 ARRAY(Float) 占位（pgvector 未安装）。
    子片 3 安装 pgvector 后改为 Vector(N)。ivfflat 三索引在 migration raw SQL 中。
    """

    __tablename__ = "embeddings"

    # 7 字段复合主键（fix v4.1 R5'=B：model_name + model_version 两层语义）
    project_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    modality: Mapped[str] = mapped_column(sa.String(16), default="text", primary_key=True)
    target_type: Mapped[str] = mapped_column(Text, primary_key=True)
    target_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    provider: Mapped[str] = mapped_column(sa.String(32), primary_key=True)
    model_name: Mapped[str] = mapped_column(Text, primary_key=True)
    model_version: Mapped[str] = mapped_column(Text, primary_key=True)

    # 向量维度显式记录（fix v3 决策 1=D：M18 v1 仅 {512, 1536, 3072}）
    dim: Mapped[int] = mapped_column(Integer, nullable=False)

    # ★ fix v2 决策 1=B：3 异维列（按维度区段路由，恰好填一列其余为 NULL）
    # 暂用 ARRAY(Float) 占位；pgvector 安装后子片 3 改为 Vector(N)
    embedding_512: Mapped[list[float] | None] = mapped_column(ARRAY(sa.Float), nullable=True)
    embedding_1536: Mapped[list[float] | None] = mapped_column(ARRAY(sa.Float), nullable=True)
    embedding_3072: Mapped[list[float] | None] = mapped_column(ARRAY(sa.Float), nullable=True)

    # 内容哈希（Q8=D worker 内兜底）
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        # R3-2 三重防护——modality + target_type + provider + dim 各自 CHECK
        CheckConstraint(
            "modality IN ('text', 'image', 'audio')",
            name="ck_embeddings_modality",
        ),
        CheckConstraint(
            "target_type IN ('node', 'dimension_record', 'competitor', 'issue')",
            name="ck_embeddings_target_type",
        ),
        CheckConstraint(
            "provider IN ('openai', 'bge', 'mock')",
            name="ck_embeddings_provider",
        ),
        # fix v3 决策 1=D：{512, 1536, 3072} 三档锁定；新 dim 走 ADR 升级 + Alembic 加列
        CheckConstraint("dim IN (512, 1536, 3072)", name="ck_embeddings_dim_range"),
        # 异维列互斥约束：恰好一列非 NULL，且与 dim 字段一致（design line 274-279 字面）
        CheckConstraint(
            "(dim = 512 AND embedding_512 IS NOT NULL AND embedding_1536 IS NULL AND embedding_3072 IS NULL) "
            "OR (dim = 1536 AND embedding_1536 IS NOT NULL AND embedding_512 IS NULL AND embedding_3072 IS NULL) "
            "OR (dim = 3072 AND embedding_3072 IS NOT NULL AND embedding_512 IS NULL AND embedding_1536 IS NULL)",
            name="ck_embeddings_dim_column_consistency",
        ),
        # ivfflat 索引：ORM 层占位注释；实际在 migration op.execute() raw SQL 创建（pgvector 未安装）
        # ix_embeddings_vector_512  — ivfflat / vector_cosine_ops / lists=100 / WHERE embedding_512 IS NOT NULL
        # ix_embeddings_vector_1536 — ivfflat / vector_cosine_ops / lists=100 / WHERE embedding_1536 IS NOT NULL
        # ix_embeddings_vector_3072 — ivfflat / vector_cosine_ops / lists=100 / WHERE embedding_3072 IS NOT NULL
        # project filter 索引（Q5=B 选型核心收益）
        Index(
            "ix_embeddings_project_provider_model",
            "project_id",
            "provider",
            "model_name",
            "model_version",
        ),
    )


# ── 自有表 2：embedding_failures（失败计数 + 监控源 / R10-2 例外）─────────────


class EmbeddingFailure(Base, TimestampMixin):
    """embedding_failures 表（design §3 line 355-391）。

    M18 own 横切表——R10-2 例外（auth_audit_log 类）。
    高频系统行为（embedding 计算失败）不进 M15 activity_log，写本表。
    保留策略：90 天后物理删除（cron）。
    """

    __tablename__ = "embedding_failures"

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    provider: Mapped[str] = mapped_column(
        sa.String(32), nullable=False
    )  # fix v4.2 verify B5：与 embeddings 7 字段 PK 对齐
    model_name: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # fix v4.2 verify B5 R5'=B 同步：拆 provider-level 模型名
    model_version: Mapped[str] = mapped_column(Text, nullable=False)  # product-level 业务版本号
    error_code: Mapped[str] = mapped_column(Text, nullable=False)  # ErrorCode 字符串
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=text("NOW()")
    )

    __table_args__ = (
        CheckConstraint(
            "target_type IN ('node', 'dimension_record', 'competitor', 'issue')",
            name="ck_embedding_failures_target_type",
        ),
        Index("ix_embedding_failures_failed_at", "failed_at"),  # cron 监控走时间窗口扫
        Index(
            "ix_embedding_failures_project_target",
            "project_id",
            "target_type",
            "target_id",
        ),
    )


# ── 自有表 3：embedding_tasks（task 跟踪 + zombie 兜底锚点）─────────────────


class EmbeddingTask(Base, TimestampMixin):
    """embedding_tasks 表（design §3 line 393-430）。

    R3-1：完整 SQLAlchemy class
    R3-2：status / target_type / enqueued_by 三重 CHECK 防护
    R3-3：project_id 冗余 tenant 字段
    """

    __tablename__ = "embedding_tasks"

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    provider: Mapped[str] = mapped_column(
        sa.String(32), nullable=False
    )  # fix v4.2 verify B5：与 embeddings 7 字段 PK 对齐
    model_name: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # fix v4.2 verify B5 + O5 同步：recovery 时 enqueue payload 必填
    model_version: Mapped[str] = mapped_column(Text, nullable=False)  # product-level 业务版本号
    # audit m1 修复：Mapped[str]（R3-2 第 1 重防护）+ default pending
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default=EmbeddingTaskStatus.pending.value
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enqueued_by: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # 'incremental' | 'backfill' | 'model_upgrade'
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )  # 终态后 30 天清理

    __table_args__ = (
        CheckConstraint(
            f"status IN ({_in_sql_list(_EMBEDDING_TASK_STATUSES)})",
            name="ck_embedding_tasks_status",
        ),
        CheckConstraint(
            "target_type IN ('node', 'dimension_record', 'competitor', 'issue')",
            name="ck_embedding_tasks_target_type",
        ),
        CheckConstraint(
            "enqueued_by IN ('incremental', 'backfill', 'model_upgrade')",
            name="ck_embedding_tasks_enqueued_by",
        ),
        Index("ix_embedding_tasks_status_created", "status", "created_at"),  # zombie 兜底用
        Index(
            "ix_embedding_tasks_project_target",
            "project_id",
            "target_type",
            "target_id",
        ),
    )


# ── 自有表 4：search_evaluation_log（audit M13 修复 - 1% 采样离线评估）──────


class SearchEvaluationLog(Base, TimestampMixin):
    """search_evaluation_log 表（design §3 line 432-462）。

    audit M13 修复：1% 采样记录三模式（keyword/semantic/hybrid）top5 + 用户点击，
    用于半年后离线分析"RRF k=60 是否真的优于 k=80"等调优问题。
    PRD F18 没"质量评估"机制——这是补盲点。
    保留策略：1 年保留（评估目的），cron 清理。
    """

    __tablename__ = "search_evaluation_log"

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    keyword_top5: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )  # [{target_type, target_id, score}]
    semantic_top5: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    hybrid_top5: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    user_clicked_target_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_clicked_target_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    rrf_k: Mapped[int] = mapped_column(Integer, nullable=False)  # 当时 project 配置
    similarity_threshold: Mapped[float] = mapped_column(sa.Float, nullable=False)
    sampled_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=text("NOW()")
    )

    __table_args__ = (
        Index("ix_search_eval_sampled_at", "sampled_at"),
        Index("ix_search_eval_project_query", "project_id", "query"),
    )


__all__ = [
    "Embedding",
    "EmbeddingFailure",
    "EmbeddingTask",
    "EmbeddingTaskStatus",
    "SearchEvaluationLog",
    "_EMBEDDING_TASK_STATUSES",
]
