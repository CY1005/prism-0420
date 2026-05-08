"""M18 EmbeddingTaskDAO (sync) — design/02-modules/M18-semantic-search/00-design.md §9.

R-X3 精神：DAO 接受外部 session，不自 commit / 不自 begin。
**例外**：cas_* 方法内部 commit（顶层方法 / 仅供 worker / cron 调用，禁 Service 事务上下文）。
仿 M16 AISnapshotTaskDAO CAS 模式（api/dao/ai_snapshot_task_dao.py）。

主查询模式（design §9 + §12D §5 zombie cron）：
- 所有方法 project_id 参与 tenant 过滤（embedding_tasks.project_id 字段）
- cas_start_running：pending → running（runner 起跑 CAS）
- cas_complete：running → succeeded/failed/dead_letter（runner 完成 CAS）
- cas_zombie_transition：running 超时 → dead_letter（zombie cron CAS）
- find_zombie_tasks：5min cron 预扫（不走 CAS，供 cron 逐条处理）
- find_pending_for_recovery：fix v4.1 R5'=B startup recovery

状态机（design §3 EmbeddingTaskStatus）：
  pending → running → succeeded | failed | dead_letter
反向不允许（service/worker 层保证；DAO 层 CAS WHERE status=:expected 实现）

尊重红线：
- DAO 不调 service 层
- DAO 不写 activity_log（service 层职责）
- IntegrityError 不在 DAO 层处理
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.embedding import EmbeddingTask, EmbeddingTaskStatus


class EmbeddingTaskDAO:
    # ─────────── 写（caller 事务内）───────────

    async def create(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        target_type: str,
        target_id: UUID,
        provider: str,
        model_name: str,
        model_version: str,
        enqueued_by: str = "incremental",
    ) -> EmbeddingTask:
        """新建 EmbeddingTask（status=pending / caller 事务内）。

        project_id 必填：强 tenant 归属（design §9 R3-3 冗余 tenant 字段）。
        注意：EmbeddingTask 表无 content_hash 字段（content_hash 在 embeddings 表）。
        worker 层 content_hash 幂等比对是读 embeddings 表（design §11 Q8=D）。
        """
        task = EmbeddingTask(
            project_id=project_id,
            target_type=target_type,
            target_id=target_id,
            provider=provider,
            model_name=model_name,
            model_version=model_version,
            status=EmbeddingTaskStatus.pending.value,
            enqueued_by=enqueued_by,
        )
        db.add(task)
        await db.flush()
        await db.refresh(task)
        return task

    # ─────────── CAS（顶层方法 / 内部 commit / 禁 Service 事务上下文）───────────

    async def cas_start_running(
        self,
        db: AsyncSession,
        task_id: UUID,
    ) -> EmbeddingTask | None:
        """runner 起跑 CAS UPDATE：仅当 status='pending' 才转 running。

        返回更新后的 task 对象（命中）/ None（已被 cron 抢先 / 任务不存在）。
        仿 M16 AISnapshotTaskDAO.cas_start_running 模式（内部 commit）。

        ⚠️ 内部 commit，禁止在 Service 事务上下文调用（仅供 worker 顶层）。
        """
        result = await db.execute(
            text(
                """
                UPDATE embedding_tasks
                SET status = 'running',
                    updated_at = NOW()
                WHERE id = :tid AND status = 'pending'
                RETURNING id
                """
            ),
            {"tid": task_id},
        )
        await db.commit()
        row = result.fetchone()
        if row is None:
            return None
        # populate_existing=True forces re-fetch from DB bypassing identity map cache
        stmt = select(EmbeddingTask).where(EmbeddingTask.id == task_id)
        result2 = await db.execute(stmt.execution_options(populate_existing=True))
        return result2.scalar_one_or_none()

    async def cas_complete(
        self,
        db: AsyncSession,
        task_id: UUID,
        status: EmbeddingTaskStatus,
        *,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> EmbeddingTask | None:
        """runner 完成 CAS UPDATE：仅当 status='running' 才转换。

        允许目标 status：succeeded | failed | dead_letter（design §3 状态机）。
        返回更新后的 task（命中）/ None（已被 cron 抢先）。

        ⚠️ 内部 commit，禁止在 Service 事务上下文调用（仅供 worker 顶层）。
        """
        allowed_terminal = {
            EmbeddingTaskStatus.succeeded,
            EmbeddingTaskStatus.failed,
            EmbeddingTaskStatus.dead_letter,
        }
        if status not in allowed_terminal:
            raise ValueError(f"cas_complete 只允许终态转换；got status={status!r}")

        result = await db.execute(
            text(
                """
                UPDATE embedding_tasks
                SET status      = :status,
                    error_code  = :ec,
                    error_message = :em,
                    completed_at  = NOW(),
                    expires_at    = NOW() + INTERVAL '30 days',
                    updated_at    = NOW()
                WHERE id = :tid AND status = 'running'
                RETURNING id
                """
            ),
            {
                "status": status.value,
                "ec": error_code,
                "em": error_message,
                "tid": task_id,
            },
        )
        await db.commit()
        row = result.fetchone()
        if row is None:
            return None
        # populate_existing=True forces re-fetch from DB bypassing identity map cache
        stmt2 = select(EmbeddingTask).where(EmbeddingTask.id == task_id)
        result2 = await db.execute(stmt2.execution_options(populate_existing=True))
        return result2.scalar_one_or_none()

    async def cas_zombie_transition(
        self,
        db: AsyncSession,
        task_id: UUID,
        timeout_seconds: int,
    ) -> EmbeddingTask | None:
        """zombie cron CAS：running 超时 → dead_letter（单条 / 精确 task_id）。

        设计参考 M16 cas_zombie_transition；M18 zombie 走 dead_letter（非 failed）——
        design §12D：embedding zombie 标记为 dead_letter + cron 可重新 enqueue。
        返回更新后的 task（命中）/ None（已非 running / 未超时）。

        ⚠️ 内部 commit，禁止在 Service 事务上下文调用（仅供 cron 顶层）。
        """
        result = await db.execute(
            text(
                """
                UPDATE embedding_tasks
                SET status        = 'dead_letter',
                    error_code    = 'embedding_zombie',
                    error_message = '任务执行超时',
                    completed_at  = NOW(),
                    expires_at    = NOW() + INTERVAL '30 days',
                    updated_at    = NOW()
                WHERE id = :tid
                  AND status = 'running'
                  AND updated_at < NOW() - make_interval(secs => :timeout)
                RETURNING id
                """
            ),
            {"tid": task_id, "timeout": timeout_seconds},
        )
        await db.commit()
        row = result.fetchone()
        if row is None:
            return None
        # populate_existing=True forces re-fetch from DB bypassing identity map cache
        stmt2 = select(EmbeddingTask).where(EmbeddingTask.id == task_id)
        result2 = await db.execute(stmt2.execution_options(populate_existing=True))
        return result2.scalar_one_or_none()

    # ─────────── 读 ───────────

    async def find_zombie_tasks(
        self,
        db: AsyncSession,
        timeout_seconds: int,
    ) -> list[EmbeddingTask]:
        """5min cron 用：列出 status='running' 且 updated_at < NOW() - timeout 的 zombie 任务。

        cron 拿到列表后逐条调 cas_zombie_transition 做精确 CAS（design §12D zombie 策略）。
        全局查（embedding zombie cron 不按 project_id 扫，下同 M16 模式）。
        """
        threshold = datetime.now(UTC) - timedelta(seconds=timeout_seconds)
        result = await db.execute(
            select(EmbeddingTask)
            .where(
                EmbeddingTask.status == EmbeddingTaskStatus.running.value,
                EmbeddingTask.updated_at < threshold,
            )
            .order_by(EmbeddingTask.updated_at.asc())
        )
        return list(result.scalars().all())

    async def find_pending_for_recovery(
        self,
        db: AsyncSession,
    ) -> list[EmbeddingTask]:
        """fix v4.1 R5'=B startup recovery：列出 status='pending' 残留任务。

        startup 钩子 + backfill_recovery cron 每小时调，防 arq 重启后丢失任务
        (design §6 Lifespan + Cron embedding_backfill_recovery.py)。
        全局查（startup 恢复不限 project）。
        """
        result = await db.execute(
            select(EmbeddingTask)
            .where(EmbeddingTask.status == EmbeddingTaskStatus.pending.value)
            .order_by(EmbeddingTask.created_at.asc())
        )
        return list(result.scalars().all())

    async def delete_old_terminal(
        self,
        db: AsyncSession,
        days: int = 30,
    ) -> int:
        """30 天清理 cron：物理删除终态（succeeded/failed/dead_letter）且 expires_at < NOW() 的行。

        design §3 embedding_tasks 保留策略：终态 30 天后清理（expires_at 字段）。
        返回删除行数。
        """
        result = await db.execute(
            sa_delete(EmbeddingTask).where(
                EmbeddingTask.status.in_(
                    [
                        EmbeddingTaskStatus.succeeded.value,
                        EmbeddingTaskStatus.failed.value,
                        EmbeddingTaskStatus.dead_letter.value,
                    ]
                ),
                EmbeddingTask.expires_at < datetime.now(UTC),
            )
        )
        return result.rowcount or 0


__all__ = ["EmbeddingTaskDAO"]
