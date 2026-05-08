"""M16 BackgroundTasks runner + cleanup_zombie_tasks cron entry。

design §6 字面（audit B3+verify 补强）：
- runner 自起 SessionLocal 与 FastAPI Depends(get_db) 请求级 session 隔离（请求级
  session 在 response 之前已 close）
- 任何路径都走 cas_complete（不直 UPDATE）
- activity_log 写入条件式（CAS affected=1 才写），保证与 zombie cron 不双写终态事件
- 异常逐项 wrap 为 Snapshot* + 走 cas_complete(status=failed, error_code, error_message)

cleanup_zombie_tasks（cron 入口）：
- 单条 CAS UPDATE 转 failed + RETURNING ids
- 拿到 ids 后批量补写 activity_log（user_id=SYSTEM_USER_UUID per ADR-002 §1.1）
"""

from __future__ import annotations

import logging
from uuid import UUID

from api.core.db import SessionLocal
from api.dao.ai_snapshot_task_dao import AISnapshotTaskDAO
from api.errors.exceptions import (
    SnapshotParseFailedError,
    SnapshotProviderError,
    SnapshotProviderNotConfiguredError,
    SnapshotQuotaExceededError,
    SnapshotTimeoutError,
)
from api.queue.base import SYSTEM_USER_UUID
from api.services.activity_log_service import write_event
from api.services.ai_snapshot_service import AISnapshotService

log = logging.getLogger(__name__)


async def run_snapshot_task(task_id: UUID) -> None:
    """FastAPI BackgroundTasks 拉起入口。请求级 Depends(get_db) session 已关闭，
    必须自起新 session（design §6 字面）。

    流程：
    1) cas_start_running（pending→running）；affected=0 表示已被 cron 抢先 → 退出
    2) execute_generate(task)
    3) success：cas_complete(succeeded, review_data)；written=True 才写 ai_snapshot_completed
    4) timeout / provider / parse / quota / config error：cas_complete(failed, error_*)；
       written=True 才写 ai_snapshot_failed
    5) 其他异常：兜底 cas_complete(failed, error_code='unexpected')
    """
    dao = AISnapshotTaskDAO()
    async with SessionLocal() as db:
        # 1) CAS start
        ok = await dao.cas_start_running(db, task_id=task_id)
        if not ok:
            log.info("snapshot task %s already finalized; runner exit", task_id)
            return
        task = await dao.get_by_id(db, task_id)
        if task is None:
            log.warning("snapshot task %s vanished after CAS; abort", task_id)
            return

        # 写 ai_snapshot_started（与 cas_start_running 同事务保证；R10-2 owner 维护）
        try:
            await write_event(
                db=db,
                actor_user_id=task.user_id,
                project_id=task.project_id,
                action_type="ai_snapshot_started",
                target_type="ai_snapshot_task",
                target_id=str(task.id),
                summary="AI 快照任务起跑",
                metadata={
                    "node_id": str(task.node_id),
                    "version_count": task.version_count,
                    "ai_provider": task.ai_provider,
                    "ai_model": task.ai_model,
                },
            )
            await db.commit()
        except Exception:
            log.exception("snapshot task %s start log failed; continue", task_id)

        # 2) execute（自起 service / 自管异常）
        service = AISnapshotService()
        try:
            review_data, elapsed_ms = await service.execute_generate(db, task)
        except SnapshotTimeoutError:
            await _finalize_failed(
                dao, db, task, error_code="snapshot_timeout", error_message="task timed out"
            )
            return
        except SnapshotProviderNotConfiguredError as e:
            await _finalize_failed(
                dao,
                db,
                task,
                error_code="snapshot_provider_not_configured",
                error_message=getattr(e, "message", "provider misconfigured"),
            )
            return
        except SnapshotProviderError as e:
            await _finalize_failed(
                dao,
                db,
                task,
                error_code="snapshot_provider_error",
                error_message=getattr(e, "message", "provider error"),
            )
            return
        except SnapshotQuotaExceededError as e:
            await _finalize_failed(
                dao,
                db,
                task,
                error_code="snapshot_quota_exceeded",
                error_message=getattr(e, "message", "quota exceeded"),
            )
            return
        except SnapshotParseFailedError as e:
            await _finalize_failed(
                dao,
                db,
                task,
                error_code="snapshot_parse_failed",
                error_message=getattr(e, "message", "parse failed"),
            )
            return
        except Exception as e:
            log.exception("snapshot task %s unexpected exception", task_id)
            await _finalize_failed(
                dao,
                db,
                task,
                error_code="snapshot_provider_error",
                error_message=str(e)[:500],
            )
            return

        # 3) success CAS（affected=0 表示已被 cron 抢先转 failed → 丢弃 activity_log）
        written = await dao.cas_complete(
            db, task_id=task.id, review_data=review_data, status="succeeded"
        )
        if written:
            try:
                await write_event(
                    db=db,
                    actor_user_id=task.user_id,
                    project_id=task.project_id,
                    action_type="ai_snapshot_completed",
                    target_type="ai_snapshot_task",
                    target_id=str(task.id),
                    summary="AI 快照生成完成",
                    metadata={
                        "node_id": str(task.node_id),
                        "version_count": task.version_count,
                        "ai_provider": task.ai_provider,
                        "ai_model": task.ai_model,
                        "generation_time_ms": elapsed_ms,
                        "dimensions_count": len(review_data.get("dimensions", [])),
                        "estimated_cost_usd": 0.0,  # 真实成本需 provider 返回 token usage 估算（后续 sprint）
                    },
                )
                await db.commit()
            except Exception:
                log.exception("snapshot task %s completion log failed", task_id)


async def _finalize_failed(
    dao: AISnapshotTaskDAO,
    db,
    task,
    *,
    error_code: str,
    error_message: str,
) -> None:
    """统一 failed CAS + 条件 activity_log 写入（防与 zombie cron 双写终态事件）。"""
    written = await dao.cas_complete(
        db,
        task_id=task.id,
        review_data=None,
        status="failed",
        error_code=error_code,
        error_message=error_message,
    )
    if written:
        try:
            await write_event(
                db=db,
                actor_user_id=task.user_id,
                project_id=task.project_id,
                action_type="ai_snapshot_failed",
                target_type="ai_snapshot_task",
                target_id=str(task.id),
                summary=f"AI 快照失败：{error_code}",
                metadata={
                    "node_id": str(task.node_id),
                    "version_count": task.version_count,
                    "ai_provider": task.ai_provider,
                    "error_code": error_code,
                    "error_message_short": error_message[:200],
                },
            )
            await db.commit()
        except Exception:
            log.exception("snapshot task %s failed-log write failed", task.id)


# ─────────────── zombie cron + cleanup cron ───────────────


async def cleanup_zombie_tasks() -> int:
    """zombie cron 入口（每 5 分钟跑 / 服务部署时挂到 cron job）。

    单条 CAS UPDATE 把 running >11min / pending >2min 转 failed/snapshot_zombie。
    返回处理数。activity_log 用 SYSTEM_USER_UUID（ADR-002 §1.1）。
    """
    dao = AISnapshotTaskDAO()
    async with SessionLocal() as db:
        ids = await dao.cas_zombie_transition(db)
        if not ids:
            return 0
        for tid in ids:
            try:
                await write_event(
                    db=db,
                    actor_user_id=SYSTEM_USER_UUID,
                    project_id=None,  # cron 系统操作 / 无 project context
                    action_type="ai_snapshot_failed",
                    target_type="ai_snapshot_task",
                    target_id=str(tid),
                    summary="AI 快照任务被 zombie cron 清理",
                    metadata={
                        "error_code": "snapshot_zombie",
                        "trigger": "zombie_cron",
                    },
                )
            except Exception:
                log.exception("zombie cron log write failed task=%s", tid)
        await db.commit()
        return len(ids)


async def cleanup_expired_tasks() -> int:
    """清理 cron 入口（每日 0 点跑）：物理删除 expires_at < NOW() 行。"""
    dao = AISnapshotTaskDAO()
    async with SessionLocal() as db:
        return await dao.delete_expired(db)


__all__ = ["run_snapshot_task", "cleanup_zombie_tasks", "cleanup_expired_tasks"]
