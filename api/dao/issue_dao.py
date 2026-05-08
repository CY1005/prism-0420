"""M07 DAO (async) — design/02-modules/M07-issue/00-design.md §9.

R-X3 精神：DAO 接受外部 session，不自 commit / 不自 begin。
事务由 Service 层（状态转换 SELECT FOR UPDATE 行锁）或 Router 层（CRUD）控制。

主查询模式（design §9）：所有 list/get/update/delete 强制 ``WHERE project_id = ?``
tenant 过滤。豁免清单：无。

orphan 语义（design §3 + R-X2 第三真注入）：
  orphan_by_node_id UPDATE issues SET node_id = NULL（不是 DELETE）
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.issue import Issue


class IssueDAO:
    # ─────────── 读 ───────────

    async def list_by_project(
        self,
        db: AsyncSession,
        project_id: UUID,
        *,
        category: str | None = None,
        status: str | None = None,
        node_id: UUID | None = None,
        tag: str | None = None,
        limit: int | None = None,
    ) -> Sequence[Issue]:
        """项目级 issue 列表 + 多维过滤（design §9）。

        - category / status / node_id：等值过滤
        - tag：JSONB 数组包含查询 ``tags @> [tag]``（PG `@>` 操作符）
        """
        stmt = select(Issue).where(Issue.project_id == project_id)
        if category is not None:
            stmt = stmt.where(Issue.category == category)
        if status is not None:
            stmt = stmt.where(Issue.status == status)
        if node_id is not None:
            stmt = stmt.where(Issue.node_id == node_id)
        if tag is not None:
            stmt = stmt.where(Issue.tags.contains([tag]))
        stmt = stmt.order_by(Issue.created_at.desc(), Issue.id.desc())
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, db: AsyncSession, issue_id: UUID, project_id: UUID) -> Issue | None:
        result = await db.execute(
            select(Issue).where(
                Issue.id == issue_id,
                Issue.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_for_update(
        self, db: AsyncSession, issue_id: UUID, project_id: UUID
    ) -> Issue | None:
        """SELECT ... FOR UPDATE（design §5 状态转换竞态分析）。

        Service 层 status transition 必先调本方法锁定行 → 校验当前 status →
        UPDATE 状态字段。并发 open→in_progress 双 user 认领被串行化。
        """
        result = await db.execute(
            select(Issue)
            .where(
                Issue.id == issue_id,
                Issue.project_id == project_id,
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def count_by_project(
        self,
        db: AsyncSession,
        project_id: UUID,
        *,
        status: str | None = None,
    ) -> int:
        """count_by_project（M13/M16 跨模块只读消费可能用）。

        R1-C P1-01 立修（2026-05-08）：用 ``count(Issue.id).select_from(Issue)``
        让 PG planner 走 ix_issue_project_status / ix_issue_project_category index-only
        scan（visibility map 兜底，无 heap fetch）；裸 ``count()`` 缺 select_from
        会被规划成全表 seq scan。
        """
        stmt = select(func.count(Issue.id)).select_from(Issue).where(Issue.project_id == project_id)
        if status is not None:
            stmt = stmt.where(Issue.status == status)
        result = await db.execute(stmt)
        return int(result.scalar_one())

    # ─────────── 写 ───────────

    async def create(self, db: AsyncSession, record: Issue) -> Issue:
        db.add(record)
        await db.flush()
        return record

    async def update(
        self,
        db: AsyncSession,
        issue_id: UUID,
        project_id: UUID,
        *,
        fields: dict[str, Any],
    ) -> int:
        if not fields:
            raise ValueError("fields cannot be empty")
        result = await db.execute(
            update(Issue)
            .where(
                Issue.id == issue_id,
                Issue.project_id == project_id,
            )
            .values(**fields)
        )
        return result.rowcount

    async def delete_by_id(self, db: AsyncSession, issue_id: UUID, project_id: UUID) -> int:
        result = await db.execute(
            delete(Issue).where(
                Issue.id == issue_id,
                Issue.project_id == project_id,
            )
        )
        return result.rowcount

    # ─────────── R-X2 orphan_by_node_id 用 ───────────

    async def list_by_node_for_orphan(
        self, db: AsyncSession, node_id: UUID, project_id: UUID
    ) -> Sequence[Issue]:
        """取节点下所有 issues（R-X2 orphan_by_node_id 内部用，写 N 条 activity_log）。"""
        result = await db.execute(
            select(Issue).where(
                Issue.node_id == node_id,
                Issue.project_id == project_id,
            )
        )
        return result.scalars().all()

    async def orphan_by_node_id(self, db: AsyncSession, node_id: UUID, project_id: UUID) -> int:
        """R-X2 orphan：UPDATE issues SET node_id = NULL（不是 DELETE）。

        与 M04/M06 delete_by_node_id 行为契约不同：issue 不被删除只变游离。
        """
        result = await db.execute(
            update(Issue)
            .where(
                Issue.node_id == node_id,
                Issue.project_id == project_id,
            )
            .values(node_id=None)
        )
        return result.rowcount
