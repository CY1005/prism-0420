"""Alembic migration 共享 helper（horizontal）。

# horizontal: 是
# owner: M04 sprint R1-B C2 punt 闭环（M03 sprint 决定 M04 migration 出现前提取）
# 位置: migrations/（Alembic 横切层，与 versions/ 同级）
# 范畴: 所有 revision 复用的 SQL 片段拼接器（CHECK 约束子句等）
"""

from __future__ import annotations


def ck_clause(column: str, values: tuple[str, ...]) -> str:
    """生成 ``column IN ('v1', 'v2', ...)`` SQL 子句（用于 CheckConstraint）。

    在 m01/m02/m03 三处重复定义，M04 sprint 提取（R1-B C2 punt 触发条件
    "M04 migration 出现前提取"已达成）。
    """
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"
