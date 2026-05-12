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
from sqlalchemy.orm import selectinload

from api.models.competitor import Competitor, CompetitorRef

# design §7 CompetitorRefResponse 含 display_name JOIN 自 competitors.display_name；
# 所有 ref 读路径强制 eager-load competitor 关系，杜绝 async lazy-load 失败。
_REF_JOINS = (selectinload(CompetitorRef.competitor),)


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

    async def get_competitor_global(
        self, db: AsyncSession, competitor_id: UUID
    ) -> Competitor | None:
        """无 tenant 过滤的 id 全局查；仅供 service 层用来区分
        "竞品不存在 (404)" vs "竞品存在但跨项目 (422)"。

        DAO 通用查询仍强制 tenant 过滤（design §9）；本方法是 service 层
        防御性错误码区分的窄入口，不暴露给 router。
        """
        result = await db.execute(select(Competitor).where(Competitor.id == competitor_id))
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
        """节点下所有对标记录（按 created_at ASC 旧→新 / id tie-break）。

        design §7 CompetitorRefResponse 含 display_name JOIN：强制 selectinload(competitor)
        让 router `_ref_response` 可读 `ref.competitor.display_name` 而不触发 async lazy-load。
        """
        result = await db.execute(
            select(CompetitorRef)
            .options(*_REF_JOINS)
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
        """单条对标读取（与 list_refs_by_node 同范式：eager-load competitor）。"""
        result = await db.execute(
            select(CompetitorRef)
            .options(*_REF_JOINS)
            .where(
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
