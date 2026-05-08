"""M16 AI 快照任务 SQLAlchemy 模型（design/02-modules/M16-ai-snapshot/00-design.md §3）。

1 表：ai_snapshot_tasks（FastAPI BackgroundTasks fire-and-forget §12B 子模板首次实战）

设计要点（design §3 + §12B 字段①）：
- R3-2 status 三重防护：Text + CheckConstraint + Mapped[str]（M02-M14 11 模块同款范式 /
  避免 model 反向依赖 schema layer 引循环 import）
- R3-3 project_id 冗余 tenant 字段（M16 走规则 1 / 非全局豁免）
- 不建 DB UniqueConstraint（audit B1 修复 / 业务幂等含 5min 时间窗口 + status 子集，
  PG partial index 谓词必须 immutable，做不到）；幂等走 ORM find_idempotent +
  PG advisory_xact_lock（design §11）
- 5 状态：pending → running → succeeded / failed / cancelled（cancelled 预留态 R4-3a）
- expires_at 30 天清理（cron 物理删除 / pending|running 不设 / 终态转换时设 NOW+30d）
- review_data JSONB 大字段（典型 5-30KB，少数 >100KB）：PG TOAST 自动压缩
- 5 索引：node_status / user_created / expires / status_created (zombie cron) /
  user_project_node_version_count_created (find_idempotent)
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
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.models.base import Base, TimestampMixin


class AISnapshotTaskStatus(StrEnum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"  # R4-3a 预留态 / 本期不实装端点


_AI_SNAPSHOT_STATUSES = ("pending", "running", "succeeded", "failed", "cancelled")


class AISnapshotTask(Base, TimestampMixin):
    """ai_snapshot_tasks 表（design §3 / §12B 字段①）。

    R3-1：完整 SQLAlchemy class
    R3-2：status 三重防护（Text + CheckConstraint + Mapped[str]）
    R3-3：project_id 冗余 tenant 字段
    """

    __tablename__ = "ai_snapshot_tasks"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in _AI_SNAPSHOT_STATUSES)})",
            name="ck_ai_snapshot_status",
        ),
        Index("ix_ai_snapshot_node_status", "node_id", "status"),
        Index("ix_ai_snapshot_user_created", "user_id", "created_at"),
        Index("ix_ai_snapshot_expires", "expires_at"),
        # zombie cron 用（status='running' AND created_at < NOW-11min / status='pending' AND created_at < NOW-2min）
        Index("ix_ai_snapshot_status_created", "status", "created_at"),
        # find_idempotent 用（5min 窗口 + 同 user/project/node/version_count）
        Index(
            "ix_ai_snapshot_idem_lookup",
            "user_id",
            "project_id",
            "node_id",
            "version_count",
            "created_at",
        ),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default=AISnapshotTaskStatus.pending.value
    )
    # 创建任务时该 node 的 version 总数（≥3 校验 + 幂等 key 一部分）
    version_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # 从 M02 项目配置快照（claude/codex/kimi/mock）
    ai_provider: Mapped[str] = mapped_column(Text, nullable=False)
    ai_model: Mapped[str] = mapped_column(Text, nullable=False)
    # AI 输出 {summary: str, dimensions: [{key, name, content}]}
    review_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 30 天后 cron 物理删除（pending/running 不设；终态转换时设 NOW+30d）
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
