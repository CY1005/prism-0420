"""M17 AI 智能导入 SQLAlchemy 模型（design/02-modules/M17-ai-import/00-design.md §3）。

2 表：
- import_tasks（用户视角的导入批次 / 11 状态 / arq Queue 异步 pilot）
- import_task_items（每个文件 / git file 一条记录 / 细粒度重试 + 部分失败追踪）

设计要点（design §3 + §12 Queue payload）：
- R3-2 status 三重防护：Text + CheckConstraint + Mapped[str]（M02-M16 14 模块同款 /
  避免 model 反向依赖 schema 引循环 import）
- R3-3 project_id 冗余 tenant 字段
- DB UNIQUE(user_id, project_id, source_hash)：idempotency 7 天复用 key（B1 修复——
  project_id 必须在 key 内防跨租户污染）；过期判定走 ORM created_at 比较，DB 仅约束唯一
- 11 状态主表（含 partial_failed 半终态 / R4-3a 登记表表达半终态行为）
- 5 状态明细表（pending/processing/completed/failed/skipped）
- 3 源形态：zip / git_url / git_bundle
- expires_at 双用：① idempotency 7 天 ② 死信 30 天（按 status 区分）
- review_data JSONB 大字段（典型 MB 级）：PG TOAST 自动压缩
- 4 索引主表 / 1 索引明细表
"""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class ImportTaskStatus(StrEnum):
    pending = "pending"
    extracting = "extracting"
    ai_step1 = "ai_step1"
    ai_step2 = "ai_step2"
    ai_step3 = "ai_step3"
    awaiting_review = "awaiting_review"
    importing = "importing"
    completed = "completed"
    partial_failed = "partial_failed"  # 半终态 / R4-3a 登记表
    failed = "failed"
    cancelled = "cancelled"


_IMPORT_TASK_STATUSES = (
    "pending",
    "extracting",
    "ai_step1",
    "ai_step2",
    "ai_step3",
    "awaiting_review",
    "importing",
    "completed",
    "partial_failed",
    "failed",
    "cancelled",
)


class ImportTaskItemStatus(StrEnum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


_IMPORT_TASK_ITEM_STATUSES = (
    "pending",
    "processing",
    "completed",
    "failed",
    "skipped",
)


class ImportSourceType(StrEnum):
    zip = "zip"
    git_url = "git_url"
    git_bundle = "git_bundle"


_IMPORT_SOURCE_TYPES = ("zip", "git_url", "git_bundle")


def _in_sql_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


class ImportTask(Base, TimestampMixin):
    """import_tasks 表（design §3 主表）。

    R3-1：完整 SQLAlchemy class
    R3-2：status / source_type 三重防护（Text + CheckConstraint + Mapped[str]）
    R3-3：project_id 冗余 tenant 字段
    """

    __tablename__ = "import_tasks"
    __table_args__ = (
        # idempotency：7 天内同 user + 同 project + 同 source_hash 复用（B1 修复）
        UniqueConstraint(
            "user_id",
            "project_id",
            "source_hash",
            name="uq_import_user_project_hash",
        ),
        CheckConstraint(
            f"status IN ({_in_sql_list(_IMPORT_TASK_STATUSES)})",
            name="ck_import_task_status",
        ),
        CheckConstraint(
            f"source_type IN ({_in_sql_list(_IMPORT_SOURCE_TYPES)})",
            name="ck_import_source_type",
        ),
        Index("ix_import_project_status", "project_id", "status"),
        Index("ix_import_user_created", "user_id", "created_at"),
        Index("ix_import_expires", "expires_at"),
        # zombie cron 用：拉超时 ai_step* 状态 / 过期清理
        Index("ix_import_status_created", "status", "created_at"),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    # SHA256(zip 内容 / git URL+ref hash / .git 包内容)；与 (user_id, project_id) 组合做 idempotency
    source_hash: Mapped[str] = mapped_column(Text, nullable=False)
    # S3 path 或 git URL（zip 暂存路径 / git_url 原值 / git_bundle S3 path）
    source_uri: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default=ImportTaskStatus.pending.value
    )
    # 0-100 进度（WebSocket 推 progress_update 事件用）
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # {step, retry_count, dead_letter}（重试用尽时 dead_letter=True / 死信 30d 清理）
    error_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # claude / codex / kimi（M02 项目级配置快照）
    ai_provider: Mapped[str] = mapped_column(Text, nullable=False)
    ai_model: Mapped[str] = mapped_column(Text, nullable=False)
    # AI 步骤 1+2 输出，待用户 review；step3 入库后清空
    review_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 双用语义：① idempotency 7 天 ② 死信 30 天（按 status 区分；cron 物理删除）
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["ImportTaskItem"]] = relationship(
        "ImportTaskItem",
        back_populates="task",
        cascade="all, delete-orphan",
    )


class ImportTaskItem(Base, TimestampMixin):
    """import_task_items 表（design §3 明细表 / 细粒度重试 + 部分失败追踪）。

    R3-1：完整 SQLAlchemy class
    R3-2：status 三重防护（Text + CheckConstraint + Mapped[str]）
    """

    __tablename__ = "import_task_items"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({_in_sql_list(_IMPORT_TASK_ITEM_STATUSES)})",
            name="ck_import_item_status",
        ),
        Index("ix_import_item_task_status", "task_id", "status"),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default=ImportTaskItemStatus.pending.value
    )
    # AI 处理结果 {extracted_dimensions, suggested_node_path, ...}
    ai_output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # review 后用户决定的目标 node_id；ondelete=SET NULL 防 node 删除时 cascade item
    target_node_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="SET NULL"),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    task: Mapped["ImportTask"] = relationship("ImportTask", back_populates="items")


__all__ = [
    "ImportSourceType",
    "ImportTask",
    "ImportTaskItem",
    "ImportTaskItemStatus",
    "ImportTaskStatus",
    "_IMPORT_SOURCE_TYPES",
    "_IMPORT_TASK_ITEM_STATUSES",
    "_IMPORT_TASK_STATUSES",
]
