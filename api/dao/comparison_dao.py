"""M12 DAO (async) — design/02-modules/M12-comparison/00-design.md §9.

R-X3 精神：DAO 接受外部 session，不自 commit / 不自 begin。
事务由 Service 层（多表事务 create_snapshot）或 Router 层（CRUD）控制。

主查询模式（design §9）：所有 list/get/update/delete 强制 ``WHERE project_id = ?``
tenant 过滤。items 查询通过 JOIN comparison_snapshots.project_id 双重 tenant 过滤。
豁免清单：无。

G2/G4 决策：
- comparison_snapshots 无 status 字段（快照无状态最小集）
- G4=B 值快照：comparison_snapshot_items 表存 content 副本
- G2 Q2：保留 version 乐观锁（rename 并发保护）
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.models.comparison_snapshot import ComparisonSnapshot, ComparisonSnapshotItem


class ComparisonDAO:
    # ─────────── 读：snapshots ───────────

    async def list_snapshots(
        self,
        db: AsyncSession,
        project_id: UUID,
        *,
        limit: int = 50,
    ) -> Sequence[ComparisonSnapshot]:
        """项目级快照列表（按 created_at DESC）。tenant 过滤强制。"""
        stmt = (
            select(ComparisonSnapshot)
            .where(ComparisonSnapshot.project_id == project_id)
            .order_by(ComparisonSnapshot.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def count_snapshots(self, db: AsyncSession, project_id: UUID) -> int:
        """SnapshotListResponse.total 用。"""
        result = await db.execute(
            select(func.count(ComparisonSnapshot.id)).where(
                ComparisonSnapshot.project_id == project_id
            )
        )
        return int(result.scalar_one() or 0)

    async def list_snapshots_with_total(
        self,
        db: AsyncSession,
        project_id: UUID,
        *,
        limit: int = 50,
    ) -> tuple[list[ComparisonSnapshot], int]:
        """M-CLEANUP（cross-sprint #7 立修）：list + count 双查询合一（COUNT OVER 单 SQL）。

        SELECT *, COUNT(*) OVER() AS total ... LIMIT :limit
        空集合 total=0（COUNT OVER 不返回行）。
        """
        total_col = func.count().over().label("__total")
        stmt = (
            select(ComparisonSnapshot, total_col)
            .where(ComparisonSnapshot.project_id == project_id)
            .order_by(ComparisonSnapshot.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = result.all()
        if not rows:
            return [], 0
        items = [row[0] for row in rows]
        total = int(rows[0][1])
        return items, total

    async def get_snapshot(
        self,
        db: AsyncSession,
        snapshot_id: UUID,
        project_id: UUID,
    ) -> ComparisonSnapshot | None:
        """单快照查询：tenant 过滤强制（防 snapshot_id 跨项目越权）。"""
        result = await db.execute(
            select(ComparisonSnapshot).where(
                ComparisonSnapshot.id == snapshot_id,
                ComparisonSnapshot.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_snapshot_with_items(
        self,
        db: AsyncSession,
        snapshot_id: UUID,
        project_id: UUID,
    ) -> ComparisonSnapshot | None:
        """SnapshotDetailResponse：eager load items 避免 N+1。"""
        result = await db.execute(
            select(ComparisonSnapshot)
            .options(selectinload(ComparisonSnapshot.items))
            .where(
                ComparisonSnapshot.id == snapshot_id,
                ComparisonSnapshot.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    # ─────────── 读：items ───────────

    async def list_items_by_snapshot(
        self,
        db: AsyncSession,
        snapshot_id: UUID,
        project_id: UUID,
    ) -> Sequence[ComparisonSnapshotItem]:
        """tenant 过滤通过 JOIN comparison_snapshots.project_id 双重保护。"""
        stmt = (
            select(ComparisonSnapshotItem)
            .join(
                ComparisonSnapshot,
                ComparisonSnapshot.id == ComparisonSnapshotItem.snapshot_id,
            )
            .where(
                ComparisonSnapshotItem.snapshot_id == snapshot_id,
                ComparisonSnapshot.project_id == project_id,
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ─────────── 写：snapshots ───────────

    async def insert_snapshot(
        self,
        db: AsyncSession,
        snapshot: ComparisonSnapshot,
    ) -> ComparisonSnapshot:
        """新增快照（service 层负责前置校验 + 事务）。"""
        db.add(snapshot)
        await db.flush()
        return snapshot

    async def update_snapshot_with_version(
        self,
        db: AsyncSession,
        snapshot_id: UUID,
        project_id: UUID,
        expected_version: int,
        **fields: Any,
    ) -> int:
        """乐观锁 rename：UPDATE 带 version=expected → version+1；rows=0 = 冲突/越权/不存在。

        caller（service）在 rows=0 时区分"快照不存在 / 跨租户"（先 get_snapshot 验）
        与"乐观锁冲突"（get 命中但 update rows=0）。
        """
        if not fields:
            raise ValueError("update_snapshot_with_version 至少需要一个 field")
        # R1-C P1-03 立修：Core UPDATE 不触发 ORM onupdate，必须显式刷 updated_at
        stmt = (
            update(ComparisonSnapshot)
            .where(
                ComparisonSnapshot.id == snapshot_id,
                ComparisonSnapshot.project_id == project_id,
                ComparisonSnapshot.version == expected_version,
            )
            .values(
                **fields,
                version=ComparisonSnapshot.version + 1,
                updated_at=datetime.now(UTC),
            )
        )
        result = await db.execute(stmt)
        return int(result.rowcount or 0)

    async def delete_snapshot(
        self,
        db: AsyncSession,
        snapshot_id: UUID,
        project_id: UUID,
    ) -> int:
        """删除快照（CASCADE 自动清 items）。tenant 过滤强制。返回受影响行数（0 或 1）。"""
        stmt = delete(ComparisonSnapshot).where(
            ComparisonSnapshot.id == snapshot_id,
            ComparisonSnapshot.project_id == project_id,
        )
        result = await db.execute(stmt)
        return int(result.rowcount or 0)

    # ─────────── 写：items ───────────

    async def bulk_insert_items(
        self,
        db: AsyncSession,
        items: list[ComparisonSnapshotItem],
    ) -> None:
        """G4=B 值快照明细 bulk insert（service 层多表事务内调用）。"""
        if not items:
            return
        db.add_all(items)
        await db.flush()
