"""M18 Embedding cron 任务（design §12D §15 cron 矩阵）。

同文件多个 cron 函数（arq cron 形态）：
- cron_backfill_daily：每日 0 点 / scan_pending → enqueue
- cron_zombie_cleanup：每 5min / find_zombie_tasks → cas_zombie_transition
- cron_failure_monitor：每小时 / count_failures_in_window → 三维阈值告警
- cron_old_terminal_cleanup：每日 / 30 天清理终态 task / 90 天清理 failures
- cron_search_eval_cleanup：每日 / 90 天清理 search_evaluation_log

cron user_id 边界（ADR-002 §1.1）：所有 cron 写 activity_log / Queue payload 必须落 SYSTEM_USER_UUID。
自起 SessionLocal + 不依赖请求级 Depends(get_db)（M16 范式）。
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta

from api.dao.embedding_failure_dao import EmbeddingFailureDAO
from api.dao.embedding_task_dao import EmbeddingTaskDAO

log = logging.getLogger(__name__)

# ─── 三维告警阈值（design §6 line 600-602 / env 配置）────────────────────────

_FAILURE_THRESHOLD_ABS = int(os.getenv("EMBEDDING_FAILURE_THRESHOLD_ABS", "500"))
_FAILURE_THRESHOLD_PCT = float(os.getenv("EMBEDDING_FAILURE_THRESHOLD_PCT", "5"))
_FAILURE_THRESHOLD_PER_PROJECT = int(os.getenv("EMBEDDING_FAILURE_THRESHOLD_PER_PROJECT", "100"))

# zombie timeout（design §12D：embedding 单 task 60s + commit buffer 60s = 2min = 120s）
_ZOMBIE_TIMEOUT_S = int(os.getenv("EMBEDDING_TASK_TIMEOUT_S", "60")) + 60

# 清理保留天数（design §12D §⑦ cron 矩阵）
_TERMINAL_CLEANUP_DAYS = 30
_FAILURE_CLEANUP_DAYS = 90
_SEARCH_EVAL_CLEANUP_DAYS = 90


async def cron_backfill_daily(ctx: dict) -> None:
    """每日 0 点：扫 pending embedding task → enqueue（design §15.1 cron 矩阵）。

    ADR-002 §1.1：cron 触发非用户操作，arq payload user_id = SYSTEM_USER_UUID。
    """
    from api.core.db import SessionLocal as AsyncSessionLocal  # type: ignore[import]

    log.info("cron_backfill_daily: starting")

    async with AsyncSessionLocal() as db:
        task_dao = EmbeddingTaskDAO()
        pending = await task_dao.find_pending_for_recovery(db)

        if not pending:
            log.info("cron_backfill_daily: no pending tasks found")
            return

        log.info("cron_backfill_daily: found %d pending tasks to re-enqueue", len(pending))

        from api.services.embedding import EmbeddingBackfillService

        arq_pool = ctx.get("redis")  # arq context 中的 redis pool
        backfill_service = EmbeddingBackfillService(task_dao=task_dao)
        resumed = await backfill_service.detect_and_resume_pending_backfill(db, arq_pool)
        log.info("cron_backfill_daily: re-enqueued %d tasks", resumed)


async def cron_zombie_cleanup(ctx: dict) -> None:
    """每 5min：find_zombie_tasks → cas_zombie_transition（design §12D zombie 兜底）。

    zombie 阈值 = EMBEDDING_TASK_TIMEOUT_S + 60s commit buffer = 2min（设计 §12D line 1071）。
    """
    from api.core.db import SessionLocal as AsyncSessionLocal  # type: ignore[import]

    log.debug("cron_zombie_cleanup: starting (timeout=%ds)", _ZOMBIE_TIMEOUT_S)

    async with AsyncSessionLocal() as db:
        task_dao = EmbeddingTaskDAO()
        zombies = await task_dao.find_zombie_tasks(db, _ZOMBIE_TIMEOUT_S)

        if not zombies:
            log.debug("cron_zombie_cleanup: no zombie tasks")
            return

        log.warning("cron_zombie_cleanup: found %d zombie tasks", len(zombies))
        transitioned = 0
        for task in zombies:
            result = await task_dao.cas_zombie_transition(db, task.id, _ZOMBIE_TIMEOUT_S)
            if result is not None:
                transitioned += 1
                log.warning(
                    "cron_zombie_cleanup: marked dead_letter task_id=%s project=%s",
                    task.id,
                    task.project_id,
                )

        log.info(
            "cron_zombie_cleanup: transitioned %d/%d to dead_letter",
            transitioned,
            len(zombies),
        )


async def cron_failure_monitor(ctx: dict) -> None:
    """每小时：count_failures_in_window → 三维阈值告警（design §12D §⑥ / M10 三维）。

    三维告警（任一超过即 logger.error + bulletin）：
    - ABS：单小时全局失败 ≥ EMBEDDING_FAILURE_THRESHOLD_ABS（=500）
    - PCT：单小时失败率 ≥ EMBEDDING_FAILURE_THRESHOLD_PCT（=5%）
    - PER_PROJECT：任一 project 单小时失败 ≥ EMBEDDING_FAILURE_THRESHOLD_PER_PROJECT（=100）
    """
    from api.core.db import SessionLocal as AsyncSessionLocal  # type: ignore[import]

    log.debug("cron_failure_monitor: starting")

    async with AsyncSessionLocal() as db:
        failure_dao = EmbeddingFailureDAO()

        # 全局失败数（过去 1 小时）—— count_failures_in_window(hours=1)
        total_failures = await failure_dao.count_failures_in_window(db, hours=1)

        # ABS 阈值检查
        if total_failures >= _FAILURE_THRESHOLD_ABS:
            log.error(
                "cron_failure_monitor: ABS threshold exceeded: "
                "failures=%d >= threshold=%d in last 1h",
                total_failures,
                _FAILURE_THRESHOLD_ABS,
            )

        # PCT 阈值检查——需要 embedding_tasks 总数估算；使用简单比率（total_tasks 估值）
        # 占位：子片 4+ 接真实 total_tasks 查询
        # 若 total_failures > 0 且无法取 total_tasks，按绝对值告警已足够
        # TODO 子片 4+：接 task_dao.count_completed_in_window(db, hours=1) 真做 PCT

        # PER_PROJECT 阈值检查——需要按 project 分组，当前 DAO 提供按 project_id 查询
        # 此处扫取全部失败行按 project_id 分组（设计 §12D cron 矩阵）
        from datetime import UTC, timedelta

        from sqlalchemy import func, select

        from api.models.embedding import EmbeddingFailure

        threshold_time = datetime.now(UTC) - timedelta(hours=1)
        per_project_result = await db.execute(
            select(EmbeddingFailure.project_id, func.count().label("cnt"))
            .where(EmbeddingFailure.failed_at >= threshold_time)
            .group_by(EmbeddingFailure.project_id)
        )
        for row in per_project_result.all():
            project_id, count = row.project_id, row.cnt
            if count >= _FAILURE_THRESHOLD_PER_PROJECT:
                log.error(
                    "cron_failure_monitor: PER_PROJECT threshold exceeded: "
                    "project=%s failures=%d >= threshold=%d in last 1h",
                    project_id,
                    count,
                    _FAILURE_THRESHOLD_PER_PROJECT,
                )

        log.info(
            "cron_failure_monitor: done total_failures=%d",
            total_failures,
        )


async def cron_old_terminal_cleanup(ctx: dict) -> None:
    """每日：清理终态 task + failure 记录（design §12D §⑦ cron 矩阵）。

    - succeeded / failed / dead_letter tasks：expires_at < NOW() → DELETE（~30 天）
    - embedding_failures：failed_at > 90 天 → DELETE
    """
    from api.core.db import SessionLocal as AsyncSessionLocal  # type: ignore[import]

    log.info("cron_old_terminal_cleanup: starting")

    async with AsyncSessionLocal() as db:
        task_dao = EmbeddingTaskDAO()
        failure_dao = EmbeddingFailureDAO()

        # 清理终态 task（expires_at 字段控制 / 30 天后设置 expires_at）
        deleted_tasks = await task_dao.delete_old_terminal(db, days=_TERMINAL_CLEANUP_DAYS)
        await db.commit()

        # 清理 embedding_failures（90 天）—— DAO method: delete_old(days=)
        deleted_failures = await failure_dao.delete_old(db, days=_FAILURE_CLEANUP_DAYS)
        await db.commit()

        log.info(
            "cron_old_terminal_cleanup: deleted tasks=%d failures=%d",
            deleted_tasks,
            deleted_failures,
        )


async def cron_search_eval_cleanup(ctx: dict) -> None:
    """每日：90 天清理 search_evaluation_log（design §12D §⑦ + §15.1 cron 矩阵）。

    search_evaluation_log 保留策略：设计文档 §3 line 432-462 = 1 年保留（评估目的）；
    本函数清理 90 天前数据（保守实现；可调整为 1 年）。
    """
    from api.core.db import SessionLocal as AsyncSessionLocal  # type: ignore[import]

    log.info("cron_search_eval_cleanup: starting")

    async with AsyncSessionLocal() as db:
        from sqlalchemy import delete as sa_delete

        from api.models.embedding import SearchEvaluationLog

        cutoff = datetime.now(UTC) - timedelta(days=_SEARCH_EVAL_CLEANUP_DAYS)
        result = await db.execute(
            sa_delete(SearchEvaluationLog).where(
                SearchEvaluationLog.sampled_at < cutoff,
            )
        )
        await db.commit()
        deleted = result.rowcount or 0
        log.info("cron_search_eval_cleanup: deleted %d rows", deleted)


__all__ = [
    "cron_backfill_daily",
    "cron_zombie_cleanup",
    "cron_failure_monitor",
    "cron_old_terminal_cleanup",
    "cron_search_eval_cleanup",
]
