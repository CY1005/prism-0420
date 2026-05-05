"""S6 reconcile 验证：base.py 三个 Mixin 字段形态符合 design 真相。

不依赖真实 DB 连接 / Alembic migration——直接 introspect SQLAlchemy
mapper 的 column 元数据，验证类型、nullable、server_default、onupdate。
等 M01.2 真表落地时再加端到端 INSERT/UPDATE 验证。
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from api.models.base import Base, ImmutableMixin, SoftDeleteMixin, TimestampMixin


class _StampedRow(Base, TimestampMixin):
    __tablename__ = "_stamped_row_for_test"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


class _ImmutableRow(Base, ImmutableMixin):
    __tablename__ = "_immutable_row_for_test"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


class _SoftDeletableRow(Base, SoftDeleteMixin):
    __tablename__ = "_soft_deletable_row_for_test"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


def test_timestamp_mixin_has_created_and_updated_columns():
    cols = _StampedRow.__table__.c
    assert "created_at" in cols
    assert "updated_at" in cols

    created = cols["created_at"]
    updated = cols["updated_at"]
    assert isinstance(created.type, DateTime) and created.type.timezone is True
    assert isinstance(updated.type, DateTime) and updated.type.timezone is True

    assert created.nullable is False
    assert updated.nullable is False

    assert created.server_default is not None, "created_at 必须有 server_default=now()"
    assert updated.server_default is not None, "updated_at 必须有 server_default=now()"
    assert updated.onupdate is not None, "updated_at 必须有 onupdate=now()"


def test_immutable_mixin_has_only_created_at():
    cols = _ImmutableRow.__table__.c
    assert "created_at" in cols
    assert "updated_at" not in cols, "ImmutableMixin 不应有 updated_at（与 append-only 语义冲突）"

    created = cols["created_at"]
    assert isinstance(created.type, DateTime) and created.type.timezone is True
    assert created.nullable is False
    assert created.server_default is not None


def test_soft_delete_mixin_has_nullable_deleted_at():
    cols = _SoftDeletableRow.__table__.c
    assert "deleted_at" in cols

    deleted = cols["deleted_at"]
    assert isinstance(deleted.type, DateTime) and deleted.type.timezone is True
    assert deleted.nullable is True


def test_python_type_annotation_is_datetime():
    """typing 层确认 Mapped[datetime] 注解生效，IDE/mypy 友好。"""
    hints = TimestampMixin.__annotations__
    assert hints["created_at"] == Mapped[datetime]
    assert hints["updated_at"] == Mapped[datetime]
    assert ImmutableMixin.__annotations__["created_at"] == Mapped[datetime]
    assert SoftDeleteMixin.__annotations__["deleted_at"] == Mapped[datetime | None]
