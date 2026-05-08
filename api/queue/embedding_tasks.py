"""M18 embedding arq Queue task（design §6 + §12D）。

横切归属（design §6 + R-X6 + 04-layer Q7）：业务 owner=M18，位置在 api/queue/ 横切目录下。

embed_single task：
1. EmbedSinglePayload.model_validate（extra='forbid' 防漂移）
2. check_payload_consistency（cross-tenant 防御 / ADR-002）
3. advisory_xact_lock 双 namespace（design §11 line 878 字面）
4. EmbeddingService.get_or_compute_embedding
5. 失败：record_failure + EmbeddingTaskDAO.cas_complete(failed)
6. 成功：cas_complete(succeeded)

事务边界（M16 范式）：worker 自起 SessionLocal，不依赖请求级 Depends(get_db)。
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from api.dao.embedding_failure_dao import EmbeddingFailureDAO
from api.dao.embedding_task_dao import EmbeddingTaskDAO
from api.errors.exceptions import (
    EmbeddingProviderFailedError,
    EmbeddingProviderTimeoutError,
    EmbeddingTargetNotFoundError,
)
from api.models.embedding import EmbeddingTaskStatus
from api.schemas.embedding_schema import EmbedSinglePayload
from api.services.embedding import EmbeddingService

log = logging.getLogger(__name__)


async def embed_single(
    ctx: dict[str, Any], *, raw: dict[str, Any] | None = None, **kwargs: Any
) -> None:
    """arq task：单条 embedding 计算（design §6 + §12D 字段①-⑥）。

    入口：
    1. EmbedSinglePayload.model_validate
    2. check_payload_consistency（cross-tenant 防御）
    3. advisory_xact_lock 双 namespace
    4. get_or_compute_embedding
    5. cas_complete(succeeded / failed)

    自起 SessionLocal（M16 范式）。
    """
    # ─── payload 解析 ──────────────────────────────────────────────────────
    if raw is None:
        raw = kwargs  # arq 可以用 kwargs 传参
    try:
        payload = EmbedSinglePayload.model_validate(raw)
    except Exception as exc:
        log.error("embed_single: payload validation failed: %s | raw=%s", exc, raw)
        return

    # ─── SessionLocal 自起（M16 范式 / 不依赖请求级 Depends(get_db)）────────
    from api.core.db import SessionLocal as AsyncSessionLocal  # type: ignore[import]

    task_dao = EmbeddingTaskDAO()
    failure_dao = EmbeddingFailureDAO()
    embedding_service = EmbeddingService(
        embedding_task_dao=task_dao,
        embedding_failure_dao=failure_dao,
    )

    async with AsyncSessionLocal() as db:
        # ─── check_payload_consistency（cross-tenant 防御 / ADR-002）────
        try:
            await embedding_service.check_payload_consistency(db, payload)
        except EmbeddingTargetNotFoundError:
            # target 已删 → noop（不写 failures）
            log.info(
                "embed_single: target not found (noop): %s/%s project=%s",
                payload.target_type,
                payload.target_id,
                payload.project_id,
            )
            return
        except Exception as exc:  # noqa: BLE001
            log.warning("embed_single: consistency check failed: %s", exc)
            return

        # ─── advisory_xact_lock 双 namespace（design §11 line 878 字面）────
        # pg_advisory_xact_lock(hashtext('m18_text_embedding'), hashtext(project_id||'/'||target_id))
        # 占位：pgvector 未安装时跳过真实 lock（子片 4+ 接真实 PG advisory lock）
        #
        # R1 fix #11 — Race window 说明：
        # SELECT pending → cas_start_running 之间，并发 worker 可同时 SELECT 同一 pending task。
        # CAS 兜底：cas_start_running 返 None 时表示 CAS race，静默 skip（见下方 logger.info）。
        # 数据正确性靠 content_hash 7字段PK 兜底（embeddings 表 ON CONFLICT DO UPDATE）。
        # 子片 4+ 加 advisory_xact_lock 双 namespace + project_id+target_id 复合 key 后 race 消除。
        #
        # TODO 子片 4+：
        # await db.execute(text(
        #     "SELECT pg_advisory_xact_lock("
        #     "  hashtext('m18_text_embedding'),"
        #     "  hashtext(:pid || '/' || :tid)"
        #     ")"
        # ), {"pid": str(payload.project_id), "tid": str(payload.target_id)})

        # ─── CAS pending → running ──────────────────────────────────────────
        # 找最新 pending task（按 created_at 排序）
        from sqlalchemy import select

        from api.models.embedding import EmbeddingTask

        result = await db.execute(
            select(EmbeddingTask)
            .where(
                EmbeddingTask.project_id == payload.project_id,
                EmbeddingTask.target_type == payload.target_type.value,
                EmbeddingTask.target_id == payload.target_id,
                EmbeddingTask.status == EmbeddingTaskStatus.pending.value,
            )
            .order_by(EmbeddingTask.created_at.asc())
            .limit(1)
        )
        task = result.scalar_one_or_none()

        if task is None:
            log.debug(
                "embed_single: no pending task found for %s/%s",
                payload.target_type,
                payload.target_id,
            )
            return

        # CAS start running
        # R1 fix #11：CAS miss 路径 logger.info（Race window 可见 / 不再 silent return）
        running_task = await task_dao.cas_start_running(db, task.id)
        if running_task is None:
            log.info(
                "embed_single: CAS race, skip task=%s (another worker already started it)",
                task.id,
            )
            return

        # ─── get_or_compute_embedding ────────────────────────────────────────
        # source_text：worker 内调上游拉取（design §12D line 954 / §9 规则 1）
        # 占位：当前用 target_type + target_id 拼凑测试用 source_text
        # TODO 子片 4+ 接真实上游 Service（NodeService / DimensionService 等）
        source_text = f"{payload.target_type.value}:{payload.target_id}"
        content_hash = hashlib.sha256(source_text.encode()).hexdigest()

        try:
            await embedding_service.get_or_compute_embedding(
                db,
                project_id=payload.project_id,
                target_type=payload.target_type.value,
                target_id=payload.target_id,
                provider=payload.provider,
                model_name=payload.model_name,
                model_version=payload.model_version,
                content_hash=content_hash,
                source_text=source_text,
            )

            # cas_complete → succeeded
            await task_dao.cas_complete(
                db,
                task.id,
                EmbeddingTaskStatus.succeeded,
            )
            log.info(
                "embed_single: succeeded task_id=%s target=%s/%s",
                task.id,
                payload.target_type,
                payload.target_id,
            )

        except EmbeddingTargetNotFoundError:
            # noop：target 已删，不写 failures，直接 succeeded（设计语义：noop = 成功）
            await task_dao.cas_complete(db, task.id, EmbeddingTaskStatus.succeeded)

        except (EmbeddingProviderFailedError, EmbeddingProviderTimeoutError) as exc:
            error_code = (
                "embedding_provider_timeout"
                if isinstance(exc, EmbeddingProviderTimeoutError)
                else "embedding_provider_failed"
            )
            await failure_dao.record_failure(
                db,
                project_id=payload.project_id,
                target_type=payload.target_type.value,
                target_id=payload.target_id,
                provider=payload.provider,
                model_name=payload.model_name,
                model_version=payload.model_version,
                error_code=error_code,
                error_message=str(exc),
            )
            await task_dao.cas_complete(
                db,
                task.id,
                EmbeddingTaskStatus.failed,
                error_code=error_code,
                error_message=str(exc),
            )
            log.error(
                "embed_single: provider error task_id=%s: %s",
                task.id,
                exc,
            )

        except Exception as exc:  # noqa: BLE001
            await failure_dao.record_failure(
                db,
                project_id=payload.project_id,
                target_type=payload.target_type.value,
                target_id=payload.target_id,
                provider=payload.provider,
                model_name=payload.model_name,
                model_version=payload.model_version,
                error_code="embedding_provider_failed",
                error_message=str(exc),
            )
            await task_dao.cas_complete(
                db,
                task.id,
                EmbeddingTaskStatus.failed,
                error_code="embedding_provider_failed",
                error_message=str(exc),
            )
            log.error(
                "embed_single: unexpected error task_id=%s: %s",
                task.id,
                exc,
            )


__all__ = ["embed_single"]
