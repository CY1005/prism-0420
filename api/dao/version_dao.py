"""M05 DAO (async) — design/02-modules/M05-version-timeline/00-design.md §9.

R-X3 精神：DAO 接受外部 session，不自 commit / 不自 begin。
事务由 Service 层 ``async with db.begin():`` 包裹。

主查询模式（design §9）：所有 list/get/update/delete 强制
``WHERE project_id = ?`` tenant 过滤。豁免清单：无。

A6 ordered 索引（M05 sprint 闸门 2.5 B1 候选 C 实证 / R1-C P2-03 名实修正）：
ix_version_node_proj_created (node_id, project_id, created_at DESC)
→ list_by_node ORDER BY created_at DESC + LIMIT 走 index ordered scan **无 sort 步骤**；
非真 covering index（SELECT VersionRecord 拉全列仍需 heap fetch），但 sort 步骤已避免。
count_by_node 用 ``count(*)`` 让 PG planner 走 index-only scan（无需 heap）。
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.version_record import VersionRecord


class VersionDAO:
    # ─────────── 读 ───────────

    async def list_by_node(
        self,
        db: AsyncSession,
        node_id: UUID,
        project_id: UUID,
        limit: int | None = None,
    ) -> Sequence[VersionRecord]:
        """节点下版本时间线（按 created_at DESC 排序）。

        命中 covering 索引 ix_version_node_proj_created；可选 limit 用于分页。
        """
        # 同事务内插入的多条 created_at 可能相等（PG now() 同事务返回一致值），
        # 加 id DESC 作为稳定 tie-break，保证测试与生产语义一致。
        stmt = (
            select(VersionRecord)
            .where(
                VersionRecord.node_id == node_id,
                VersionRecord.project_id == project_id,
            )
            .order_by(VersionRecord.created_at.desc(), VersionRecord.id.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(
        self, db: AsyncSession, version_id: UUID, project_id: UUID
    ) -> VersionRecord | None:
        """按 id + tenant 取单条（service 用于校验 + 详情）。"""
        result = await db.execute(
            select(VersionRecord).where(
                VersionRecord.id == version_id,
                VersionRecord.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_current(
        self, db: AsyncSession, node_id: UUID, project_id: UUID
    ) -> VersionRecord | None:
        """取节点当前版本（is_current=true 唯一一条）。"""
        result = await db.execute(
            select(VersionRecord).where(
                VersionRecord.node_id == node_id,
                VersionRecord.project_id == project_id,
                VersionRecord.is_current.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def count_by_node(self, db: AsyncSession, node_id: UUID, project_id: UUID) -> int:
        """节点下版本数量（M16 pilot 基线补丁追加，design §6 R-X3 对外契约）。

        R1-C P2-03 立修：``count()`` 替代 ``count(VersionRecord.id)`` 让 PG planner
        走 index-only scan（id 不在 ix_version_node_proj_created 索引中，count(id)
        需 heap fetch；count(*) 仅看 visibility map）。
        """
        result = await db.execute(
            select(func.count()).where(
                VersionRecord.node_id == node_id,
                VersionRecord.project_id == project_id,
            )
        )
        return int(result.scalar_one())

    # ─────────── 写 ───────────

    async def create(self, db: AsyncSession, record: VersionRecord) -> VersionRecord:
        """add + flush，捕 IntegrityError 由 Service 转 AppError。"""
        db.add(record)
        await db.flush()
        return record

    async def update_metadata(
        self,
        db: AsyncSession,
        version_id: UUID,
        project_id: UUID,
        *,
        fields: dict[str, Any],
    ) -> int:
        """更新元数据（不含 snapshot_data / is_current）；返回 rowcount。

        snapshot_data 不可 PUT 更新（design Q3，VersionUpdate schema 不含此字段）；
        is_current 切换走专用 set_current 路径（事务包裹 + DB 部分唯一索引兜底）。
        """
        if not fields:
            raise ValueError("fields cannot be empty")
        result = await db.execute(
            update(VersionRecord)
            .where(
                VersionRecord.id == version_id,
                VersionRecord.project_id == project_id,
            )
            .values(**fields)
        )
        return result.rowcount

    async def clear_current_flag(self, db: AsyncSession, node_id: UUID, project_id: UUID) -> int:
        """切换前清空旧 is_current（必须在事务内调用）；返回 rowcount。"""
        result = await db.execute(
            update(VersionRecord)
            .where(
                VersionRecord.node_id == node_id,
                VersionRecord.project_id == project_id,
                VersionRecord.is_current.is_(True),
            )
            .values(is_current=False)
        )
        return result.rowcount

    async def set_current_flag(self, db: AsyncSession, version_id: UUID, project_id: UUID) -> int:
        """标记为当前版本（is_current=true）；返回 rowcount。"""
        result = await db.execute(
            update(VersionRecord)
            .where(
                VersionRecord.id == version_id,
                VersionRecord.project_id == project_id,
            )
            .values(is_current=True)
        )
        return result.rowcount

    async def delete_by_id(self, db: AsyncSession, version_id: UUID, project_id: UUID) -> int:
        """tenant 隔离删除；返回 rowcount。"""
        result = await db.execute(
            delete(VersionRecord).where(
                VersionRecord.id == version_id,
                VersionRecord.project_id == project_id,
            )
        )
        return result.rowcount
