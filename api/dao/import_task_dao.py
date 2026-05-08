"""M17 DAO (async) — design/02-modules/M17-ai-import/00-design.md §9.

R-X3 精神：DAO 接受外部 session，不自 commit / 不自 begin。
事务由 Service 层（orchestrator + Queue worker）控制；R-X1 失败补偿 commit boundary
通过 compensation_session helper 独立 connection 实现（service 层调，本 DAO 中立）。

主查询模式（design §9）：所有 list/get 强制 ``WHERE project_id = ?`` tenant 过滤；
list_by_project 同时强制 ``WHERE user_id = ?``（每用户只看自己的导入任务，与 M11 范式一致）。

idempotency 实现（design §11）：
- find_idempotent：7 天内同 (user_id, project_id, source_hash) 命中 status ∈
  {completed, awaiting_review, partial_failed} 的任务复用（failed/cancelled 不复用）
- DB UNIQUE(user_id, project_id, source_hash) 兜底防 race（audit B1 修复 / project_id
  必须在 key 内防跨租户污染）

zombie cron orphan（design §12 死信策略）：
- find_zombie_dead_letter：dead_letter=true 的 failed 任务 30 天后清理
- ai_step* 状态超时（>10min）由 service 层处置（不在 DAO）
"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.import_task import ImportTask, ImportTaskItem, ImportTaskStatus

# idempotency 复用窗口（design §11）
IDEMPOTENCY_WINDOW_DAYS = 7
# 死信清理窗口（design §12）
DEAD_LETTER_RETENTION_DAYS = 30


class ImportTaskDAO:
    # ─────────── 读 ───────────

    async def list_by_project(
        self,
        db: AsyncSession,
        project_id: UUID,
        user_id: UUID,
        *,
        limit: int = 50,
    ) -> Sequence[ImportTask]:
        """项目 + 用户级导入任务列表，created_at desc 排序（design §9）。"""
        stmt = (
            select(ImportTask)
            .where(
                ImportTask.project_id == project_id,
                ImportTask.user_id == user_id,
            )
            .order_by(ImportTask.created_at.desc(), ImportTask.id.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(
        self,
        db: AsyncSession,
        task_id: UUID,
        project_id: UUID,
    ) -> ImportTask | None:
        """单任务（强制 project_id tenant 过滤；跨项目越权返 None → service 转 404）。"""
        result = await db.execute(
            select(ImportTask).where(
                ImportTask.id == task_id,
                ImportTask.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def find_idempotent(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        project_id: UUID,
        source_hash: str,
    ) -> ImportTask | None:
        """idempotency: 7 天内同 (user_id, project_id, source_hash) 命中可复用任务。

        ★ project_id 是 key 的一部分（audit B1 修复——防跨项目 task 误复用导致租户污染）。

        复用范围（design §11）：completed / awaiting_review / partial_failed
        不复用范围：failed / cancelled（让用户能重新跑）

        与 DB UNIQUE(user_id, project_id, source_hash) 配合避免并发提交多跑（service
        层先查 find_idempotent → 未命中再 INSERT；INSERT 端到端 catch IntegrityError 转
        ImportTaskDuplicateError，6-design-principles 清单 6 落地）。
        """
        threshold = datetime.now(UTC) - timedelta(days=IDEMPOTENCY_WINDOW_DAYS)
        stmt = (
            select(ImportTask)
            .where(
                ImportTask.user_id == user_id,
                ImportTask.project_id == project_id,
                ImportTask.source_hash == source_hash,
                ImportTask.created_at > threshold,
                ImportTask.status.in_(
                    [
                        ImportTaskStatus.completed.value,
                        ImportTaskStatus.awaiting_review.value,
                        ImportTaskStatus.partial_failed.value,
                    ]
                ),
            )
            .order_by(ImportTask.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_dead_letter_orphans(
        self,
        db: AsyncSession,
        *,
        retention_days: int = DEAD_LETTER_RETENTION_DAYS,
        limit: int = 200,
    ) -> Sequence[ImportTask]:
        """zombie cron：列出 status=failed 且 created_at < NOW - 30d 的死信任务待清理。

        cron daily 调（api/queue/import_cleanup_dead_letter）；返回 id 清单后 cron 逐条
        delete（physical）+ activity_log housekeeping（design §12）。
        """
        threshold = datetime.now(UTC) - timedelta(days=retention_days)
        stmt = (
            select(ImportTask)
            .where(
                ImportTask.status == ImportTaskStatus.failed.value,
                ImportTask.created_at < threshold,
            )
            .order_by(ImportTask.created_at.asc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    # ─────────── 写（普通 INSERT/UPDATE；caller 事务内）───────────

    async def create(self, db: AsyncSession, record: ImportTask) -> ImportTask:
        """新建任务（caller 事务内 / service 层立即 commit 让 task 行脱离批量入库 txn）。"""
        db.add(record)
        await db.flush()
        await db.refresh(record)
        return record

    async def update(
        self,
        db: AsyncSession,
        task_id: UUID,
        project_id: UUID,
        *,
        fields: dict[str, Any],
    ) -> int:
        """状态转换 + progress + error_metadata 写入（service 层调）。

        强制 project_id tenant 过滤；返回 rowcount（service 层 0→ 视为竞态 / not found）。
        """
        if not fields:
            raise ValueError("fields cannot be empty")
        result = await db.execute(
            update(ImportTask)
            .where(
                ImportTask.id == task_id,
                ImportTask.project_id == project_id,
            )
            .values(**fields)
        )
        return result.rowcount

    async def delete(self, db: AsyncSession, task_id: UUID, project_id: UUID) -> int:
        """物理删除任务（cron 死信清理 / 用户取消即删）。

        强制 project_id tenant 过滤；级联删 import_task_items（FK CASCADE）。
        返回 rowcount（0 = 已被他方删 / not found）。
        """
        from sqlalchemy import delete as sa_delete

        result = await db.execute(
            sa_delete(ImportTask).where(
                ImportTask.id == task_id,
                ImportTask.project_id == project_id,
            )
        )
        return result.rowcount


class ImportTaskItemDAO:
    # ─────────── 读 ───────────

    async def list_by_task(
        self,
        db: AsyncSession,
        task_id: UUID,
        *,
        status: str | None = None,
    ) -> Sequence[ImportTaskItem]:
        """task 下所有 items（按 file_path asc）；可选 status 过滤。

        无 project_id 参数：caller (service) 必须先确认 task 归属（防跨租户读 item）。
        """
        stmt = select(ImportTaskItem).where(ImportTaskItem.task_id == task_id)
        if status is not None:
            stmt = stmt.where(ImportTaskItem.status == status)
        stmt = stmt.order_by(ImportTaskItem.file_path.asc(), ImportTaskItem.id.asc())
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(
        self, db: AsyncSession, item_id: UUID, task_id: UUID
    ) -> ImportTaskItem | None:
        """单 item（强制 task_id 过滤防跨任务读）。"""
        result = await db.execute(
            select(ImportTaskItem).where(
                ImportTaskItem.id == item_id,
                ImportTaskItem.task_id == task_id,
            )
        )
        return result.scalar_one_or_none()

    # ─────────── 写 ───────────

    async def create(self, db: AsyncSession, record: ImportTaskItem) -> ImportTaskItem:
        db.add(record)
        await db.flush()
        await db.refresh(record)
        return record

    async def bulk_create(
        self, db: AsyncSession, records: Sequence[ImportTaskItem]
    ) -> Sequence[ImportTaskItem]:
        """批量插入 items（zip/git repo 解压后 / caller 事务内）。"""
        db.add_all(records)
        await db.flush()
        return records

    async def update(
        self,
        db: AsyncSession,
        item_id: UUID,
        task_id: UUID,
        *,
        fields: dict[str, Any],
    ) -> int:
        """item 状态 / ai_output / target_node_id / retry_count 更新。

        强制 task_id 过滤防跨任务越权写。
        """
        if not fields:
            raise ValueError("fields cannot be empty")
        result = await db.execute(
            update(ImportTaskItem)
            .where(
                ImportTaskItem.id == item_id,
                ImportTaskItem.task_id == task_id,
            )
            .values(**fields)
        )
        return result.rowcount


__all__ = [
    "DEAD_LETTER_RETENTION_DAYS",
    "IDEMPOTENCY_WINDOW_DAYS",
    "ImportTaskDAO",
    "ImportTaskItemDAO",
]
