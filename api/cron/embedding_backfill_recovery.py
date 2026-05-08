"""M18 Embedding backfill 中断恢复 cron（fix v4.1 R5'=B）。

design §6 line 582 + §12D Backfill 中断恢复机制（line 1115-1165）：
- 每小时 arq cron 调 detect_and_resume_pending_backfill
- FastAPI lifespan startup 钩子调一次（防 cron 第一次 fire 前丢残留）

fix v4.1 R5'=B：async def + ArqRedis 形参。
fix v4.3 verify V2：enqueue "embed_single"（不再 embed_text）。
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


async def detect_and_resume_pending_backfill(
    db: Any,
    arq_pool: Any,
) -> dict[str, int]:
    """检测残留 backfill task 并 re-enqueue（arq cron + FastAPI startup 双触发）。

    fix v4.1 R5'=B：
    - async def（消除 sync 函数里 await 的 SyntaxError）
    - arq_pool: ArqRedis 形参（真 re-enqueue）

    两层去重（design §12D line 1129-1131）：
    1. 入队层：arq _job_id=f"backfill_recovery:{task.id}" 1h 内幂等去重
    2. 处理层：worker 入口 content_hash 7 字段 PK SELECT 比对兜底

    Returns:
        dict with 'detected' and 'resumed' counts.
    """
    from api.services.embedding import EmbeddingBackfillService

    service = EmbeddingBackfillService()
    resumed = await service.detect_and_resume_pending_backfill(db, arq_pool)
    return {"detected": resumed, "resumed": resumed}


async def cron_backfill_recovery(ctx: dict) -> None:
    """arq cron 每小时调 detect_and_resume_pending_backfill（design §12D line 1087）。

    cron user_id 边界（ADR-002 §1.1）：
    arq payload 使用 SYSTEM_USER_UUID——本 cron 不写 activity_log，
    enqueue 的 payload 内 user_id = SYSTEM_USER_UUID。
    """
    from api.core.db import SessionLocal as AsyncSessionLocal  # type: ignore[import]

    log.info("cron_backfill_recovery: starting")

    arq_pool = ctx.get("redis")

    async with AsyncSessionLocal() as db:
        result = await detect_and_resume_pending_backfill(db, arq_pool)

    log.info(
        "cron_backfill_recovery: done detected=%d resumed=%d",
        result.get("detected", 0),
        result.get("resumed", 0),
    )


__all__ = ["detect_and_resume_pending_backfill", "cron_backfill_recovery"]
