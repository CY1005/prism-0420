"""Tenant 过滤横切 helper（horizontal）。

# horizontal: 是
# owner: M02 / M20（M02 注入 only project_members impl / M20 升级 UNION impl）
# 位置: api/auth/（横切层，对齐原则 6 + R-X6 + 04-layer Q7）
# 范畴: ADR-005 §3.1 团队扩展横切 helper

设计来源：design/adr/ADR-005-team-extension.md §3.1（M20 新增 helper）+
design/00-roadmap.md §5.2 B8。

返回当前 user 可访问的 project_id 子查询。并集来源：
  1. project_members WHERE user_id = X            ← M02 落地
  2. projects WHERE team_id IN (
       SELECT team_id FROM team_members WHERE user_id = X
     )                                            ← M20 落地

本期（B2.4 scaffold）：表 project_members / projects / team_members 由 M02/M20
owns，尚未落地。helper 定义 Protocol + set_tenant_context 注入点；M02 上线时
注入"仅 project_members"实现，M20 上线时注入 UNION 实现。

调用契约（M03-M19 各模块 DAO 使用）：
    accessible = user_accessible_project_ids_subquery(db, user.id)
    db.query(MyModel).filter(MyModel.project_id.in_(select(accessible))).all()
"""

from typing import Any, Protocol
from uuid import UUID


class TenantContextProtocol(Protocol):
    """M02 / M20 提供具体实现。"""

    def user_accessible_project_ids_subquery(self, db: Any, user_id: UUID) -> Any: ...


_ctx: TenantContextProtocol | None = None


def set_tenant_context(ctx: TenantContextProtocol | None) -> None:
    """M02/M20 启动时注入 concrete 实现；测试也用此函数 mock。"""
    global _ctx
    _ctx = ctx


def user_accessible_project_ids_subquery(db: Any, user_id: UUID) -> Any:
    """返回 user 可访问的 project_id SQLAlchemy subquery。

    Raises NotImplementedError 当尚未 set_tenant_context（M02 未落地阶段）。
    """
    if _ctx is None:
        raise NotImplementedError(
            "tenant_context not initialized; M02 (project_members) must call "
            "set_tenant_context() before any DAO list/get with tenant scope. "
            "M20 extends to include team-based access."
        )
    return _ctx.user_accessible_project_ids_subquery(db, user_id)
