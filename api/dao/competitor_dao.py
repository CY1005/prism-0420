"""M06 DAO (async) — design/02-modules/M06-competitor/00-design.md §9.

R-X3 精神：DAO 接受外部 session，不自 commit / 不自 begin。
事务由 Service 层（多表事务 competitors + competitor_refs 同事务包裹）或
Router 层（单表 CRUD）控制。

主查询模式（design §9）：所有 list/get/update/delete 强制 ``WHERE project_id = ?``
tenant 过滤。豁免清单：无。
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.competitor import Competitor, CompetitorRef


class CompetitorDAO:
    # ─────────── Competitor 全局实体 ───────────

    async def list_by_project(self, db: AsyncSession, project_id: UUID) -> Sequence[Competitor]:
        """项目竞品全局列表（按 display_name ASC）。"""
        result = await db.execute(
            select(Competitor)
            .where(Competitor.project_id == project_id)
            .order_by(Competitor.display_name.asc(), Competitor.id.asc())
        )
        return result.scalars().all()

    async def get_competitor_by_id(
        self, db: AsyncSession, competitor_id: UUID, project_id: UUID
    ) -> Competitor | None:
        result = await db.execute(
            select(Competitor).where(
                Competitor.id == competitor_id,
                Competitor.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_competitor(self, db: AsyncSession, record: Competitor) -> Competitor:
        db.add(record)
        await db.flush()
        return record

    async def update_competitor(
        self,
        db: AsyncSession,
        competitor_id: UUID,
        project_id: UUID,
        *,
        fields: dict[str, Any],
    ) -> int:
        if not fields:
            raise ValueError("fields cannot be empty")
        result = await db.execute(
            update(Competitor)
            .where(
                Competitor.id == competitor_id,
                Competitor.project_id == project_id,
            )
            .values(**fields)
        )
        return result.rowcount

    async def delete_competitor(
        self, db: AsyncSession, competitor_id: UUID, project_id: UUID
    ) -> int:
        """硬删除；DB CASCADE 自动清 competitor_refs。"""
        result = await db.execute(
            delete(Competitor).where(
                Competitor.id == competitor_id,
                Competitor.project_id == project_id,
            )
        )
        return result.rowcount

    async def count_refs_by_competitor(
        self, db: AsyncSession, competitor_id: UUID, project_id: UUID
    ) -> int:
        """删除 competitor 前先查 ref_count（写 activity_log metadata 用）。"""
        result = await db.execute(
            select(func.count()).where(
                CompetitorRef.competitor_id == competitor_id,
                CompetitorRef.project_id == project_id,
            )
        )
        return int(result.scalar_one())

    # ─────────── CompetitorRef 节点级对标记录 ───────────

    async def list_refs_by_node(
        self, db: AsyncSession, node_id: UUID, project_id: UUID
    ) -> Sequence[CompetitorRef]:
        """节点下所有对标记录（按 created_at ASC 旧→新 / id tie-break）。"""
        result = await db.execute(
            select(CompetitorRef)
            .where(
                CompetitorRef.node_id == node_id,
                CompetitorRef.project_id == project_id,
            )
            .order_by(CompetitorRef.created_at.asc(), CompetitorRef.id.asc())
        )
        return result.scalars().all()

    async def list_refs_by_node_for_delete(
        self, db: AsyncSession, node_id: UUID, project_id: UUID
    ) -> Sequence[CompetitorRef]:
        """R-X2 delete_by_node_id 内部使用：取节点下所有对标记录（id 字段足够，
        但返回完整对象供 activity_log metadata 提取 competitor_id）。"""
        result = await db.execute(
            select(CompetitorRef).where(
                CompetitorRef.node_id == node_id,
                CompetitorRef.project_id == project_id,
            )
        )
        return result.scalars().all()

    async def get_ref_by_id(
        self, db: AsyncSession, ref_id: UUID, project_id: UUID
    ) -> CompetitorRef | None:
        result = await db.execute(
            select(CompetitorRef).where(
                CompetitorRef.id == ref_id,
                CompetitorRef.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_ref(self, db: AsyncSession, record: CompetitorRef) -> CompetitorRef:
        db.add(record)
        await db.flush()
        return record

    async def update_ref(
        self,
        db: AsyncSession,
        ref_id: UUID,
        project_id: UUID,
        *,
        fields: dict[str, Any],
    ) -> int:
        if not fields:
            raise ValueError("fields cannot be empty")
        result = await db.execute(
            update(CompetitorRef)
            .where(
                CompetitorRef.id == ref_id,
                CompetitorRef.project_id == project_id,
            )
            .values(**fields)
        )
        return result.rowcount

    async def delete_ref(self, db: AsyncSession, ref_id: UUID, project_id: UUID) -> int:
        result = await db.execute(
            delete(CompetitorRef).where(
                CompetitorRef.id == ref_id,
                CompetitorRef.project_id == project_id,
            )
        )
        return result.rowcount
