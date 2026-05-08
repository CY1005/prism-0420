"""M16 DAO (async) — design/02-modules/M16-ai-snapshot/00-design.md §9.

R-X3 精神：DAO 接受外部 session，不自 begin。
**例外**：cas_* 方法内部 commit（顶层方法 / 仅供 runner / cron 调用，禁 Service 事务上下文）。

主查询模式（design §9）：
- get_by_id 双签名：传 user_id 强制 task.user_id == user_id（save 端点）；不传由 Service 层
  做 project accessibility 反查（GET endpoint 用 / §8 详述）
- find_idempotent 5min 窗口 + status ∈ {pending, running, succeeded}（failed/cancelled 不复用）
- cas_zombie_transition：单条 CAS UPDATE 转 failed + RETURNING ids 给 cron 入口批量补写
  activity_log（user_id=SYSTEM_USER_UUID per ADR-002 §1.1）
- cas_start_running：runner 起跑 CAS（pending→running，affected=0 表示已被 cron 抢先）
- cas_complete：runner 完成 CAS（running→succeeded/failed，affected=0 表示已被 cron 抢先）

豁免清单：见 §9 字面（GET endpoint 不带 user_id；M02-M05 纯读聚合）。
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.ai_snapshot_task import AISnapshotTask


class AISnapshotTaskDAO:
    # ─────────── 读 ───────────

    async def get_by_id(
        self,
        db: AsyncSession,
        task_id: UUID,
        *,
        user_id: UUID | None = None,
    ) -> AISnapshotTask | None:
        """拿单个 task。

        user_id 可选（design §9）：
        - 传：强制 task.user_id == user_id（save 端点用 / DAO 层 tenant 过滤兜底）
        - 不传：由 Service 层做 project accessibility 反查（GET endpoint 用，§8 双层校验
          第一层 creator + 第二层 project accessibility）
        """
        stmt = select(AISnapshotTask).where(AISnapshotTask.id == task_id)
        if user_id is not None:
            stmt = stmt.where(AISnapshotTask.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_idempotent(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        project_id: UUID,
        node_id: UUID,
        version_count: int,
    ) -> AISnapshotTask | None:
        """5 分钟内同 (user, project, node, version_count) 复用。

        status 限制 pending/running/succeeded（failed/cancelled 不复用——用户能立刻重发）。
        与 §11 advisory_xact_lock 配合避免并发 get-or-create 多跑（audit B1+M6 修复 /
        不再依赖 DB UniqueConstraint）。
        """
        threshold = datetime.now(UTC) - timedelta(minutes=5)
        stmt = (
            select(AISnapshotTask)
            .where(
                AISnapshotTask.user_id == user_id,
                AISnapshotTask.project_id == project_id,
                AISnapshotTask.node_id == node_id,
                AISnapshotTask.version_count == version_count,
                AISnapshotTask.created_at > threshold,
                AISnapshotTask.status.in_(["pending", "running", "succeeded"]),
            )
            .order_by(AISnapshotTask.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ─────────── 写（普通 INSERT；caller 事务内）───────────

    async def create(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        project_id: UUID,
        node_id: UUID,
        version_count: int,
        ai_provider: str,
        ai_model: str,
        status: str = "pending",
    ) -> AISnapshotTask:
        """新建任务（caller 事务内）。"""
        task = AISnapshotTask(
            user_id=user_id,
            project_id=project_id,
            node_id=node_id,
            version_count=version_count,
            ai_provider=ai_provider,
            ai_model=ai_model,
            status=status,
        )
        db.add(task)
        await db.flush()
        await db.refresh(task)
        return task

    # ─────────── CAS（顶层方法 / 内部 commit / 禁 Service 事务上下文）───────────

    async def cas_start_running(self, db: AsyncSession, *, task_id: UUID) -> bool:
        """runner 起跑 CAS UPDATE：仅当 status='pending' 才转 running。

        返回 True=拿到起跑权 / False=已被 cron 抢先转 failed。

        ⚠️ 内部 commit，禁止在 Service 事务上下文调用（仅供 runner 顶层）。
        """
        result = await db.execute(
            text(
                """
                UPDATE ai_snapshot_tasks
                SET status='running', updated_at=NOW()
                WHERE id=:tid AND status='pending'
                """
            ),
            {"tid": task_id},
        )
        await db.commit()
        return result.rowcount == 1

    async def cas_complete(
        self,
        db: AsyncSession,
        *,
        task_id: UUID,
        review_data: dict | None,
        status: str = "succeeded",
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> bool:
        """runner 完成 CAS UPDATE：仅当 status='running' 才转换。

        返回 True=真完成 / False=已被 cron 抢先转 failed，runner 应丢弃 activity_log
        写入避免双写（design §6 字面纪律）。

        ⚠️ 内部 commit，禁止在 Service 事务上下文调用（仅供 runner 顶层）。
        """
        import json

        result = await db.execute(
            text(
                """
                UPDATE ai_snapshot_tasks
                SET status=:status,
                    review_data=CAST(:rd AS JSONB),
                    error_code=:ec,
                    error_message=:em,
                    completed_at=NOW(),
                    expires_at=NOW() + INTERVAL '30 days',
                    updated_at=NOW()
                WHERE id=:tid AND status='running'
                """
            ),
            {
                "status": status,
                "rd": json.dumps(review_data) if review_data is not None else None,
                "ec": error_code,
                "em": error_message,
                "tid": task_id,
            },
        )
        await db.commit()
        return result.rowcount == 1

    async def cas_zombie_transition(
        self,
        db: AsyncSession,
        *,
        running_threshold_min: int = 11,
        pending_threshold_min: int = 2,
    ) -> list[UUID]:
        """zombie cron CAS UPDATE：单条 SQL 直接转 failed + 返回 id 清单（audit B3+M4+m6
        修复 / 避免读-改-写两步竞态 + 覆盖 pending 兜底）。

        - status='running' AND created_at < NOW-11min → failed/SNAPSHOT_ZOMBIE
        - status='pending' AND created_at < NOW-2min → failed/SNAPSHOT_ZOMBIE（add_task
          失败 / OOM 时孤儿 pending 也被抓）

        ⚠️ 内部 commit，禁止在 Service 事务上下文调用（仅供 cron 顶层）。
        zombie 转换的 activity_log 写入由 cron 入口在拿到 RETURNING ids 后批量补写
        （ADR-002 §1.1 cron user_id 边界：必须落 SYSTEM_USER_UUID）。
        """
        result = await db.execute(
            text(
                """
                UPDATE ai_snapshot_tasks
                SET status='failed',
                    error_code='snapshot_zombie',
                    error_message='任务执行异常退出',
                    completed_at=NOW(),
                    expires_at=NOW() + INTERVAL '30 days',
                    updated_at=NOW()
                WHERE (status='running' AND created_at < NOW() - make_interval(mins => :rt))
                   OR (status='pending' AND created_at < NOW() - make_interval(mins => :pt))
                RETURNING id
                """
            ),
            {"rt": running_threshold_min, "pt": pending_threshold_min},
        )
        ids = [row[0] for row in result.fetchall()]
        await db.commit()
        return ids

    # ─────────── 清理 cron（顶层；内部 commit）───────────

    async def delete_expired(self, db: AsyncSession) -> int:
        """清理 cron：物理删除 expires_at < NOW() 的任务行。返回删除行数。

        ⚠️ 内部 commit，禁止在 Service 事务上下文调用（仅供 cron 顶层）。
        """
        result = await db.execute(text("DELETE FROM ai_snapshot_tasks WHERE expires_at < NOW()"))
        await db.commit()
        return result.rowcount or 0
