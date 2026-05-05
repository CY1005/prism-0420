"""SQLAlchemy 声明基类 + 通用 Mixin。

Mixin 定义对应 reconcile S6（design/audit/scaffold-design-reconcile.md）。
各模块 design 直接 `from .base import Base, TimestampMixin`，故必须在 scaffold
统一定义。具体落点见 reconcile 报告 §S6 Reconcile 段。
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ImmutableMixin:
    """只 INSERT 不 UPDATE 的表（audit log 等）使用。

    只含 created_at 无 updated_at，语义上即"不可变"。
    实装侧 DAO/Service 层禁止对继承本 Mixin 的表执行 UPDATE，
    由 R13-2 类规约 + CI grep 守护（M15 owner）。本类不挂 event listener，
    保持 Mixin 纯结构、避免侵入 sessionmaker。
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class SoftDeleteMixin:
    """软删除：deleted_at IS NULL 表示活跃，非 NULL 表示已删除。

    DAO 层默认 WHERE deleted_at IS NULL 过滤；恢复操作 SET deleted_at = NULL。
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
