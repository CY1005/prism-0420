"""M08 DAO (async) — design/02-modules/M08-module-relation/00-design.md §9.

R-X3 精神：DAO 接受外部 session，不自 commit / 不自 begin。

主查询模式：所有查询强制 ``WHERE project_id = ?`` tenant 过滤。
双向关系处理：list_by_node / delete_by_node 用 OR 条件
``(source_node_id == node_id) | (target_node_id == node_id)``。
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.module_relation import ModuleRelation


class ModuleRelationDAO:
    # ─────────── 读 ───────────

    async def list_by_project(
        self, db: AsyncSession, project_id: UUID, *, limit: int | None = None
    ) -> Sequence[ModuleRelation]:
        stmt = (
            select(ModuleRelation)
            .where(ModuleRelation.project_id == project_id)
            .order_by(ModuleRelation.created_at.desc(), ModuleRelation.id.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def list_by_node(
        self, db: AsyncSession, node_id: UUID, project_id: UUID
    ) -> Sequence[ModuleRelation]:
        """节点的所有关联（双向 — 既包含 source=node 也包含 target=node）。"""
        result = await db.execute(
            select(ModuleRelation)
            .where(
                ModuleRelation.project_id == project_id,
                or_(
                    ModuleRelation.source_node_id == node_id,
                    ModuleRelation.target_node_id == node_id,
                ),
            )
            .order_by(ModuleRelation.created_at.desc(), ModuleRelation.id.desc())
        )
        return result.scalars().all()

    async def get_by_id(
        self, db: AsyncSession, relation_id: UUID, project_id: UUID
    ) -> ModuleRelation | None:
        result = await db.execute(
            select(ModuleRelation).where(
                ModuleRelation.id == relation_id,
                ModuleRelation.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def count_by_project(self, db: AsyncSession, project_id: UUID) -> int:
        result = await db.execute(
            select(func.count()).where(ModuleRelation.project_id == project_id)
        )
        return int(result.scalar_one())

    async def search_by_keyword(
        self, db: AsyncSession, query: str, project_id: UUID, *, limit: int = 50
    ) -> Sequence[ModuleRelation]:
        """M09 pilot pass-through：notes ilike 模糊匹配。"""
        result = await db.execute(
            select(ModuleRelation)
            .where(
                ModuleRelation.project_id == project_id,
                ModuleRelation.notes.ilike(f"%{query}%"),
            )
            .order_by(ModuleRelation.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    # ─────────── 写 ───────────

    async def create(self, db: AsyncSession, record: ModuleRelation) -> ModuleRelation:
        db.add(record)
        await db.flush()
        return record

    async def update_notes(
        self,
        db: AsyncSession,
        relation_id: UUID,
        project_id: UUID,
        *,
        notes: str | None,
    ) -> int:
        result = await db.execute(
            update(ModuleRelation)
            .where(
                ModuleRelation.id == relation_id,
                ModuleRelation.project_id == project_id,
            )
            .values(notes=notes)
        )
        return result.rowcount

    async def delete_by_id(self, db: AsyncSession, relation_id: UUID, project_id: UUID) -> int:
        result = await db.execute(
            delete(ModuleRelation).where(
                ModuleRelation.id == relation_id,
                ModuleRelation.project_id == project_id,
            )
        )
        return result.rowcount

    # ─────────── R-X2 第四真注入用 ───────────

    async def list_by_node_for_delete(
        self, db: AsyncSession, node_id: UUID, project_id: UUID
    ) -> Sequence[ModuleRelation]:
        """R-X2 delete_by_node_id 内部用：双向 list（供写 N 条 activity_log）。"""
        return await self.list_by_node(db, node_id, project_id)

    async def delete_by_node_id(self, db: AsyncSession, node_id: UUID, project_id: UUID) -> int:
        """R-X2 删除：双向 DELETE WHERE source=node OR target=node。"""
        result = await db.execute(
            delete(ModuleRelation).where(
                ModuleRelation.project_id == project_id,
                or_(
                    ModuleRelation.source_node_id == node_id,
                    ModuleRelation.target_node_id == node_id,
                ),
            )
        )
        return result.rowcount
