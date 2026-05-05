"""SQLAlchemy 声明基类。

Mixin（TimestampMixin / ImmutableMixin / SoftDeleteMixin）由 M01 实装时按
engineering-spec §3 增量加入。本期 B9 仅落基础 Base 让 fixture + dummy 表可用。
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
