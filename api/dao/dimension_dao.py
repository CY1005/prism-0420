"""M04 DAO（async）— design/02-modules/M04-feature-archive/00-design.md §9.

R-X3 精神：DAO 接受外部 session，不自 commit / 不自 begin。
事务由 Service 层 `async with db.begin():` 包裹。

主查询模式（design §9）：所有 list/get/update/delete 强制
``WHERE project_id = ?`` tenant 过滤。M04 范围内全部查询都在 tenant 边界内
（豁免清单：无）。
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.dimension_record import DimensionRecord
from api.models.project import DimensionType


class DimensionDAO:
    # ─────────── 读 ───────────

    async def get_type_by_id(
        self, db: AsyncSession, dimension_type_id: int
    ) -> DimensionType | None:
        """M-CLEANUP（cross-sprint #14 立修）：DimensionType lookup 走 DAO 层 / 替换
        service 层 3 处 db.get(DimensionType, id) 风格统一。

        DimensionType 是全局表（不带 project_id 过滤）/ caller 已通过 project_dimension_configs
        校验 enabled 状态。
        """
        result = await db.execute(
            select(DimensionType).where(DimensionType.id == dimension_type_id)
        )
        return result.scalar_one_or_none()

    async def list_by_node(
        self, db: AsyncSession, node_id: UUID, project_id: UUID
    ) -> Sequence[DimensionRecord]:
        """节点下所有维度记录（档案页主查询）。"""
        result = await db.execute(
            select(DimensionRecord)
            .where(
                DimensionRecord.node_id == node_id,
                DimensionRecord.project_id == project_id,
            )
            .order_by(DimensionRecord.dimension_type_id.asc())
        )
        return result.scalars().all()

    async def get_by_id(
        self, db: AsyncSession, record_id: UUID, project_id: UUID
    ) -> DimensionRecord | None:
        result = await db.execute(
            select(DimensionRecord).where(
                DimensionRecord.id == record_id,
                DimensionRecord.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_one(
        self,
        db: AsyncSession,
        node_id: UUID,
        project_id: UUID,
        dimension_type_id: int,
    ) -> DimensionRecord | None:
        """节点 + 维度类型唯一约束查询（创建/更新前 lookup）。"""
        result = await db.execute(
            select(DimensionRecord).where(
                DimensionRecord.node_id == node_id,
                DimensionRecord.project_id == project_id,
                DimensionRecord.dimension_type_id == dimension_type_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_nodes(
        self,
        db: AsyncSession,
        node_ids: list[UUID],
        project_id: UUID,
        dimension_type_ids: list[int] | None = None,
    ) -> list[DimensionRecord]:
        """M12 batch_get_by_nodes：批量读多 node × 多维度类型（design §6 对外契约）。

        双重 tenant 过滤（project_id + node_id IN）防越权。
        dimension_type_ids=None 表示不过滤维度类型（拿全量）。
        """
        if not node_ids:
            return []
        stmt = select(DimensionRecord).where(
            DimensionRecord.project_id == project_id,
            DimensionRecord.node_id.in_(node_ids),
        )
        if dimension_type_ids is not None:
            if not dimension_type_ids:
                return []
            stmt = stmt.where(DimensionRecord.dimension_type_id.in_(dimension_type_ids))
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_node(self, db: AsyncSession, node_id: UUID, project_id: UUID) -> int:
        """完善度计算：节点已填维度数。"""
        result = await db.execute(
            select(func.count(DimensionRecord.id)).where(
                DimensionRecord.node_id == node_id,
                DimensionRecord.project_id == project_id,
            )
        )
        return int(result.scalar_one() or 0)

    # ─────────── 写 ───────────

    async def insert(self, db: AsyncSession, record: DimensionRecord) -> DimensionRecord:
        """新建记录（service 层负责前置校验 + 唯一性保护）。"""
        db.add(record)
        await db.flush()
        return record

    async def update_with_version(
        self,
        db: AsyncSession,
        record_id: UUID,
        project_id: UUID,
        expected_version: int,
        **fields: Any,
    ) -> int:
        """乐观锁更新：UPDATE 带 version=expected → version+1；rows=0 = 冲突/越权/不存在。"""
        if not fields:
            raise ValueError("update_with_version 至少需要一个 field")
        stmt = (
            update(DimensionRecord)
            .where(
                DimensionRecord.id == record_id,
                DimensionRecord.project_id == project_id,
                DimensionRecord.version == expected_version,
            )
            .values(**fields, version=DimensionRecord.version + 1)
        )
        result = await db.execute(stmt)
        return int(result.rowcount or 0)

    async def delete_one(self, db: AsyncSession, record_id: UUID, project_id: UUID) -> int:
        """单条删除（双 tenant 过滤防越权）。"""
        result = await db.execute(
            delete(DimensionRecord).where(
                DimensionRecord.id == record_id,
                DimensionRecord.project_id == project_id,
            )
        )
        return int(result.rowcount or 0)

    async def list_by_node_for_delete(
        self, db: AsyncSession, node_id: UUID, project_id: UUID
    ) -> list[DimensionRecord]:
        """R-X2 delete_by_node_id：service 层 list 后逐条写 activity_log + delete。

        与 list_by_node 区分：caller 语义是"准备删除"，DAO 层不做删除（service 层
        遍历 list 后写 per-record 'delete' 事件 + 调 delete_one；防 DB CASCADE
        绕过 R-X2）。
        """
        result = await db.execute(
            select(DimensionRecord).where(
                DimensionRecord.node_id == node_id,
                DimensionRecord.project_id == project_id,
            )
        )
        return list(result.scalars().all())
