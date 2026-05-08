"""M11 冷启动支持 SQLAlchemy 模型（design/02-modules/M11-cold-start/00-design.md §3）。

1 表：cold_start_tasks（CSV 导入批次记录 / orchestrator 模式 / 同步 HTTP 路径）

# 设计要点（design §3）：
# - G1 status 三重防护：String(20) + CheckConstraint + Mapped[str]（codebase 范式 follow project.py）
# - G2/G6 无 idempotency：移除 UNIQUE(user_id, project_id, source_hash)
# - G6 全量回滚：枚举仅 5 状态（移除 partial_failed）；终态 completed/failed 各为 [*]
# - 表结构预留 Queue 升级兼容性（status/total_rows/success_rows 与 M17 模式同构）
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
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.models.base import Base, TimestampMixin


class ColdStartStatus(StrEnum):
    PENDING = "pending"
    VALIDATING = "validating"
    IMPORTING = "importing"
    COMPLETED = "completed"
    FAILED = "failed"


_COLD_START_STATUSES = ("pending", "validating", "importing", "completed", "failed")


class ColdStartTask(Base, TimestampMixin):
    """cold_start_tasks 表（design §3）。

    R3-1：完整 SQLAlchemy class
    R3-2：status 三重防护（String(20) + CheckConstraint + Mapped[str]）
    R3-3：project_id 冗余 tenant 字段
    R10-1：orchestrator 完成时按 N 条 batch_create 各写独立 activity_log
    """

    __tablename__ = "cold_start_tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'validating', 'importing', 'completed', 'failed')",
            name="ck_cold_start_status",
        ),
        Index("ix_cold_start_project_status", "project_id", "status"),
        Index("ix_cold_start_user_created", "user_id", "created_at"),
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
    # SHA256(CSV)；G2/G6 不参与 idempotency，仅供错误报告 / 审计
    source_hash: Mapped[str] = mapped_column(Text, nullable=False)
    source_filename: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ColdStartStatus.PENDING.value
    )
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # [{row: int, field: str, message: str}, ...]
    error_report: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
