"""M11 DAO (async) — design/02-modules/M11-cold-start/00-design.md §9.

R-X3 精神：DAO 接受外部 session，不自 commit / 不自 begin。
事务由 Service 层（orchestrator 共享 db.begin() 包 4 个 service.batch_create）控制。

主查询模式（design §9）：所有 list/get 强制 ``WHERE project_id = ?`` tenant 过滤。
list_by_project 同时强制 ``WHERE user_id = ?``（每用户只看自己的导入任务）。
豁免清单：无（GET /template 是无 DB 资源不走 DAO）。

G2/G6：无 idempotency；故无 find_idempotent 方法（design §9 显式删除）。
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.cold_start_task import ColdStartTask


class ColdStartDAO:
    # ─────────── 读 ───────────

    async def list_by_project(
        self,
        db: AsyncSession,
        project_id: UUID,
        user_id: UUID,
        *,
        limit: int = 20,
    ) -> Sequence[ColdStartTask]:
        """项目 + 用户级导入任务列表，created_at desc 排序（design §9）。"""
        stmt = (
            select(ColdStartTask)
            .where(
                ColdStartTask.project_id == project_id,
                ColdStartTask.user_id == user_id,
            )
            .order_by(ColdStartTask.created_at.desc(), ColdStartTask.id.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(
        self, db: AsyncSession, task_id: UUID, project_id: UUID
    ) -> ColdStartTask | None:
        """单任务（强制 project_id tenant 过滤；跨项目越权返 None → service 转 404）。"""
        result = await db.execute(
            select(ColdStartTask).where(
                ColdStartTask.id == task_id,
                ColdStartTask.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    # ─────────── 写 ───────────

    async def create(self, db: AsyncSession, record: ColdStartTask) -> ColdStartTask:
        db.add(record)
        await db.flush()
        return record

    async def update(
        self,
        db: AsyncSession,
        task_id: UUID,
        project_id: UUID,
        *,
        fields: dict[str, Any],
    ) -> int:
        """状态转换 + 行计数 + error_report 写入（service 层调）。

        强制 project_id tenant 过滤；返回 rowcount（service 层 0→ 视为竞态 / not found）。
        """
        if not fields:
            raise ValueError("fields cannot be empty")
        result = await db.execute(
            update(ColdStartTask)
            .where(
                ColdStartTask.id == task_id,
                ColdStartTask.project_id == project_id,
            )
            .values(**fields)
        )
        return result.rowcount
