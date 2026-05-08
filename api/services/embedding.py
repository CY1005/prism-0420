"""EmbeddingService horizontal helper（M18 §6 line 578）。

# horizontal: 是
# owner: M18
# 位置: api/services/（横切层，对齐原则 6 + R-X6）
# 范畴: enqueue / enqueue_delete / get_or_compute_embedding / embed_query / batch_backfill /
#       check_payload_consistency / detect_and_resume_pending_backfill

禁挂业务模块名下——被 M03/M04/M06/M07 多模块调用（horizontal helper）。
"""

from __future__ import annotations

import hashlib
import logging
import os
from collections import OrderedDict
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.dao.embedding_dao import EmbeddingDAO
from api.dao.embedding_failure_dao import EmbeddingFailureDAO
from api.dao.embedding_task_dao import EmbeddingTaskDAO
from api.errors.exceptions import (
    EmbeddingProviderFailedError,
    EmbeddingTargetNotFoundError,
)
from api.models.embedding import Embedding, EmbeddingTask
from api.queue.base import SYSTEM_USER_UUID
from api.schemas.embedding_schema import EmbedSinglePayload
from api.services.embedding_provider import (
    EmbeddingProvider,
    EmbeddingProviderError,
    get_embedding_provider,
)
from api.services.embedding_provider import (
    EmbeddingProviderTimeoutError as ProviderTimeoutError,
)

log = logging.getLogger(__name__)

# ─── env 常量（design §6 line 591-606）─────────────────────────────────────

_EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "mock")
_EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "mock-default")
_EMBEDDING_MODEL_VERSION = os.getenv("EMBEDDING_MODEL_VERSION", "v1")
_QUERY_EMBEDDING_TIMEOUT_MS = int(os.getenv("QUERY_EMBEDDING_TIMEOUT_MS", "1000"))
_EMBEDDING_TASK_TIMEOUT_S = int(os.getenv("EMBEDDING_TASK_TIMEOUT_S", "60"))
_BACKFILL_BATCH_TIMEOUT_S = int(os.getenv("BACKFILL_BATCH_TIMEOUT_S", "900"))

# ─── 内存 debounce 占位（子片 4+ 接 Redis Pool 后真做）─────────────────────────
# TODO 子片 4+ 接 Redis Pool 后真做 Redis SET debounce（TTL=60s）
# 当前 key = f"embedding:debounce:{project_id}:{target_type}:{target_id}"
#
# R1 fix #14：OrderedDict + size cap 防止长跑 worker 内存无界增长
# 占位期单进程内存有限 OK；多 worker 接 Redis 后才真正正确（进程不共享 OrderedDict）
_DEBOUNCE_CACHE_MAX: int = 1000
_DEBOUNCE_CACHE: OrderedDict[str, float] = OrderedDict()
_DEBOUNCE_TTL_S: float = 60.0

# ─── 内存 query embedding cache 占位（子片 4+ 接 Redis Pool 后真做）─────────────
# TODO 子片 4+ 接 Redis Pool 后真做 Redis 短缓存（TTL=5min）
#
# R1 fix #14：OrderedDict + size cap 防止长跑 worker 内存无界增长
# 占位期单进程内存有限 OK；多 worker 接 Redis 后才真正正确（进程不共享 OrderedDict）
_QUERY_EMBED_CACHE_MAX: int = 1000
_QUERY_EMBED_CACHE: OrderedDict[str, tuple[list[float], int, str, str, str]] = OrderedDict()
_QUERY_CACHE_TTL_S: float = 300.0


def _debounce_key(project_id: UUID, target_type: str, target_id: UUID) -> str:
    return f"embedding:debounce:{project_id}:{target_type}:{target_id}"


def _is_debounced(key: str) -> bool:
    """检查内存 debounce（TTL=60s）。子片 4+ 改为 Redis SET。"""
    import time

    ts = _DEBOUNCE_CACHE.get(key)
    if ts is None:
        return False
    return (time.monotonic() - ts) < _DEBOUNCE_TTL_S


def _set_debounce(key: str) -> None:
    """设置内存 debounce（OrderedDict LRU 淘汰 / cap=1000）。子片 4+ 改为 Redis SET EX 60。"""
    import time

    _DEBOUNCE_CACHE[key] = time.monotonic()
    # LRU 淘汰：超过 cap 从最早（last=False）弹出
    while len(_DEBOUNCE_CACHE) > _DEBOUNCE_CACHE_MAX:
        _DEBOUNCE_CACHE.popitem(last=False)


class EmbeddingService:
    """EmbeddingService horizontal helper（M18 design §6 line 578）。

    被 M03/M04/M06/M07 多模块 enqueue / enqueue_delete 调用；
    被 Queue worker 调 get_or_compute_embedding；
    被 SearchService 调 embed_query。

    事务边界：Service 层控制——worker/cron 自起 SessionLocal；
    不依赖请求级 Depends(get_db)（M16 范式）。
    """

    def __init__(
        self,
        embedding_dao: EmbeddingDAO | None = None,
        embedding_task_dao: EmbeddingTaskDAO | None = None,
        embedding_failure_dao: EmbeddingFailureDAO | None = None,
        provider: EmbeddingProvider | None = None,
    ) -> None:
        self._embedding_dao = embedding_dao or EmbeddingDAO()
        self._task_dao = embedding_task_dao or EmbeddingTaskDAO()
        self._failure_dao = embedding_failure_dao or EmbeddingFailureDAO()
        # provider 可注入（测试 / MockProvider）；None 时 embed_query 走 env 自构造
        self._provider = provider

    def _get_provider(self) -> EmbeddingProvider:
        if self._provider is not None:
            return self._provider
        return get_embedding_provider(
            provider_name=_EMBEDDING_PROVIDER,
            model_name=_EMBEDDING_MODEL_NAME,
        )

    # ─── enqueue（增量路径 / M03/M04/M06/M07 Service 在 commit 后调）─────────

    async def enqueue(
        self,
        db: AsyncSession,
        project_id: UUID,
        target_type: str,
        target_id: UUID,
        enqueued_by: str = "incremental",
    ) -> None:
        """Redis SET debounce 60s + arq enqueue_job（design §12D 字段①）。

        Redis 部分占位：TODO 子片 4+ 接 Redis Pool 后真做（当前用内存 dict）。
        debounce key = f"embedding:debounce:{project_id}:{target_type}:{target_id}"
        """
        key = _debounce_key(project_id, target_type, target_id)
        if _is_debounced(key):
            log.debug("enqueue debounced: %s/%s/%s", project_id, target_type, target_id)
            return

        _set_debounce(key)

        provider = self._get_provider()
        # 创建 EmbeddingTask 行（status=pending）
        # R1 fix #10：catch IntegrityError（CHECK 约束违反会原始 IntegrityError 穿透 500）
        from sqlalchemy.exc import IntegrityError

        from api.errors.exceptions import EmbeddingTaskInvalidTransitionError

        try:
            await self._task_dao.create(
                db,
                project_id=project_id,
                target_type=target_type,
                target_id=target_id,
                provider=provider.provider_name,
                model_name=provider.model_name,
                model_version=_EMBEDDING_MODEL_VERSION,
                enqueued_by=enqueued_by,
            )
        except IntegrityError as err:
            if "ck_embedding_tasks_" in str(err.orig):
                raise EmbeddingTaskInvalidTransitionError(
                    f"CHECK constraint violated on embedding_tasks for "
                    f"project={project_id} target={target_type}/{target_id}: {err.orig}"
                ) from err
            raise
        # TODO 子片 4+ 真接 arq pool：
        # await arq_pool.enqueue_job("embed_single", ...)
        log.debug(
            "enqueue task created: project=%s target=%s/%s enqueued_by=%s",
            project_id,
            target_type,
            target_id,
            enqueued_by,
        )

    # ─── enqueue_delete（audit B1 + C2=A：commit 后异步 enqueue）─────────────

    async def enqueue_delete(
        self,
        db: AsyncSession,
        project_id: UUID,
        target_type: str,
        target_id: UUID,
    ) -> None:
        """commit 后异步 delete enqueue（design §9 B1 修复 + C2=A）。

        占位期（子片 4+ 前）：同步直删；失败仅 logger.warning，不 raise。
        原因：SilentFailure(BaseException) 在业务 worker 的 except Exception 外冒泡
        会导致进程崩溃（R1 fix #2）。
        子片 4+ 接 arq 异步后再启用 SilentFailure 语义（届时改回 raise EmbeddingDeleteFailedError）。
        """
        try:
            # TODO 子片 4+ 真接 arq pool enqueue delete_embedding task
            # 当前占位：直接调 DAO 删除（无 arq）
            await self._embedding_dao.delete_by_target(
                db,
                project_id=project_id,
                target_type=target_type,
                target_id=target_id,
            )
            log.debug(
                "enqueue_delete: project=%s target=%s/%s",
                project_id,
                target_type,
                target_id,
            )
        except Exception as exc:
            # 占位期同步直删失败仅日志，不 raise SilentFailure（避免 BaseException 冒泡崩 worker）
            # 子片 4+ 接 arq 异步后再启用 SilentFailure 语义
            log.warning(
                "enqueue_delete failed (non-blocking, placeholder): project=%s target=%s/%s error=%s",
                project_id,
                target_type,
                target_id,
                exc,
            )

    # ─── get_or_compute_embedding（worker 内调）────────────────────────────

    async def get_or_compute_embedding(
        self,
        db: AsyncSession,
        project_id: UUID,
        target_type: str,
        target_id: UUID,
        provider: str,
        model_name: str,
        model_version: str,
        content_hash: str,
        source_text: str,
    ) -> Embedding:
        """worker 内调（design §6 line 578）。

        先 SELECT 兜底（7 字段 PK + content_hash 比对）→ 否则调 provider.embed_single → upsert。
        """
        # content_hash 幂等兜底（design §11 Q8=D / fix v4.3 verify F2）
        existing = await self._embedding_dao.find_by_target(
            db,
            project_id=project_id,
            target_type=target_type,
            target_id=target_id,
            provider=provider,
            model_name=model_name,
            model_version=model_version,
        )
        if existing is not None and existing.content_hash == content_hash:
            log.debug(
                "content_hash hit, skip recompute: target=%s/%s provider=%s",
                target_type,
                target_id,
                provider,
            )
            return existing

        # 调 provider.embed_single 获取向量
        # R1 fix #9：包 asyncio.timeout 防 provider 挂起导致 session 泄露 + zombie（同 embed_query 范式）
        embed_provider = self._get_provider()
        try:
            import asyncio

            async with asyncio.timeout(_EMBEDDING_TASK_TIMEOUT_S):
                vector = await embed_provider.embed_single(source_text)
        except TimeoutError as exc:
            from api.errors.exceptions import EmbeddingProviderTimeoutError

            raise EmbeddingProviderTimeoutError(
                f"provider={provider} timeout after {_EMBEDDING_TASK_TIMEOUT_S}s "
                f"computing embedding for {target_type}:{target_id}"
            ) from exc
        except ProviderTimeoutError as exc:
            from api.errors.exceptions import EmbeddingProviderTimeoutError

            raise EmbeddingProviderTimeoutError(
                f"provider={provider} timeout computing embedding for {target_type}:{target_id}"
            ) from exc
        except EmbeddingProviderError as exc:
            raise EmbeddingProviderFailedError(f"provider={provider} failed: {exc}") from exc

        dim = embed_provider.dim

        # upsert（ON CONFLICT DO UPDATE）—— DAO upsert_embedding 使用 vector 参数 + dim 路由
        result = await self._embedding_dao.upsert_embedding(
            db,
            project_id=project_id,
            modality="text",
            target_type=target_type,
            target_id=target_id,
            provider=provider,
            model_name=model_name,
            model_version=model_version,
            dim=dim,
            vector=vector,
            content_hash=content_hash,
        )
        return result

    # ─── embed_query（search 路由 / query path）──────────────────────────────

    async def embed_query(
        self,
        db: AsyncSession,
        query: str,
    ) -> tuple[list[float], int, str, str, str]:
        """query path embed（design §6 line 578）。

        返回 (vec, dim, provider, model_name, model_version)。
        Redis 短缓存 5min 占位（TODO 子片 4+ 接 Redis Pool 后真做）。
        超时 = QUERY_EMBEDDING_TIMEOUT_MS / 1000（M5 修复：1s）。
        """
        import time

        # R1 fix #16：cache_key 含 provider+model_name+model_version
        # 防切 model 后旧缓存命中返回旧维度向量 → vector_search 维度不匹配
        # design line 103 字面"Redis 5min (query+model→vector)"
        provider = self._get_provider()
        cache_key = (
            f"query_embed:{hashlib.sha256(query.encode()).hexdigest()}"
            f":{provider.provider_name}:{provider.model_name}:{_EMBEDDING_MODEL_VERSION}"
        )
        cached_ts_and_val = _QUERY_EMBED_CACHE.get(cache_key)
        if cached_ts_and_val is not None:
            ts, val = cached_ts_and_val  # type: ignore[misc]
            if (time.monotonic() - ts) < _QUERY_CACHE_TTL_S:
                log.debug("query_embed cache hit: query_prefix=%s", query[:20])
                return val  # type: ignore[return-value]
        try:
            import asyncio

            timeout_s = _QUERY_EMBEDDING_TIMEOUT_MS / 1000.0
            async with asyncio.timeout(timeout_s):
                vector = await provider.embed_single(query)
        except TimeoutError as exc:
            from api.errors.exceptions import EmbeddingProviderTimeoutError

            raise EmbeddingProviderTimeoutError(
                f"query embed timeout after {_QUERY_EMBEDDING_TIMEOUT_MS}ms"
            ) from exc
        except EmbeddingProviderError as exc:
            raise EmbeddingProviderFailedError(f"query embed failed: {exc}") from exc

        result = (
            vector,
            provider.dim,
            provider.provider_name,
            provider.model_name,
            _EMBEDDING_MODEL_VERSION,
        )
        _QUERY_EMBED_CACHE[cache_key] = (time.monotonic(), result)  # type: ignore[assignment]
        # LRU 淘汰：超过 cap 从最早（last=False）弹出
        while len(_QUERY_EMBED_CACHE) > _QUERY_EMBED_CACHE_MAX:
            _QUERY_EMBED_CACHE.popitem(last=False)
        return result

    # ─── batch_backfill（backfill path）──────────────────────────────────────

    async def batch_backfill(
        self,
        db: AsyncSession,
        project_id: UUID,
        target_ids: list[UUID],
        target_type: str,
        provider: str,
        model_name: str,
        model_version: str,
    ) -> int:
        """批量回填（design §6 line 578）。

        整批 timeout=BACKFILL_BATCH_TIMEOUT_S（15min）。
        返回成功 enqueue 数量。

        R1 fix #12 — N+1 影响边界说明：
        占位期 for-loop 逐条 enqueue() = N+1 INSERT pattern（名曰"batch"但实现非 batch）。
        5 万条回填 = 5 万次 DB 往返；当前仅适用 mock provider 测试（provider 不真调 OpenAI）。
        子片 4+ 改 INSERT INTO embedding_tasks SELECT FROM unnest(:ids) 批量 INSERT，
        或 EmbeddingTaskDAO.batch_create(ids) 批量形态。
        """
        import asyncio

        enqueued = 0

        async def _do_batch() -> None:
            nonlocal enqueued
            for target_id in target_ids:
                await self.enqueue(
                    db,
                    project_id=project_id,
                    target_type=target_type,
                    target_id=target_id,
                    enqueued_by="backfill",
                )
                enqueued += 1

        try:
            async with asyncio.timeout(_BACKFILL_BATCH_TIMEOUT_S):
                await _do_batch()
        except TimeoutError:
            log.error(
                "batch_backfill timeout after %ss: project=%s enqueued=%d/%d",
                _BACKFILL_BATCH_TIMEOUT_S,
                project_id,
                enqueued,
                len(target_ids),
            )

        return enqueued

    # ─── check_payload_consistency（worker 入口校验）─────────────────────────

    async def check_payload_consistency(
        self,
        db: AsyncSession,
        payload: EmbedSinglePayload,
    ) -> None:
        """worker 入口校验（design §8 L4 / ADR-002 cross-tenant 防御）。

        校验：target 仍存在 + project_id 与 EmbeddingTask 实际归属一致（cross-tenant 防御）。
        抛 EmbeddingTargetNotFoundError（noop）。
        """
        from sqlalchemy import select as sa_select

        # 通过 EmbeddingTask 表验 project_id 一致性（ADR-002 cross-tenant 防御）
        result = await db.execute(
            sa_select(EmbeddingTask).where(
                EmbeddingTask.project_id == payload.project_id,
                EmbeddingTask.target_type == payload.target_type.value,
                EmbeddingTask.target_id == payload.target_id,
            )
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise EmbeddingTargetNotFoundError(
                f"target {payload.target_type}:{payload.target_id} not found "
                f"in project {payload.project_id}"
            )


class EmbeddingBackfillService:
    """EmbeddingBackfillService（backfill recovery 形态 / design §12D fix v4.1 R5'=B）。

    detect_and_resume_pending_backfill：
    - FastAPI lifespan startup 钩子调一次
    - arq cron 每小时调一次
    """

    def __init__(
        self,
        task_dao: EmbeddingTaskDAO | None = None,
    ) -> None:
        self._task_dao = task_dao or EmbeddingTaskDAO()

    async def detect_and_resume_pending_backfill(
        self,
        db: AsyncSession,
        arq_pool: Any,
    ) -> int:
        """fix v4.1 R5'=B + fix v4 verify R6：检测残留 backfill task 并 re-enqueue。

        两层去重分工（design §12D line 1129-1131）：
        - 入队层：arq _job_id=f"backfill_recovery:{task.id}" 1 小时内幂等去重
        - 处理层：worker 入口 content_hash 比对兜底
        """
        stale = await self._task_dao.find_pending_for_recovery(db)
        if not stale:
            return 0

        resumed = 0
        for task in stale:
            try:
                if arq_pool is not None:
                    await arq_pool.enqueue_job(
                        "embed_single",
                        task_id=str(task.id),
                        project_id=str(task.project_id),
                        target_type=task.target_type,
                        target_id=str(task.target_id),
                        provider=task.provider,
                        model_name=task.model_name,
                        model_version=task.model_version,
                        user_id=str(SYSTEM_USER_UUID),
                        _job_id=f"backfill_recovery:{task.id}",
                    )
                resumed += 1
            except Exception as exc:  # noqa: BLE001
                log.warning("resume failed for task %s: %s", task.id, exc)

        log.info(
            "backfill_recovery: detected=%d, re-enqueued=%d",
            len(stale),
            resumed,
        )
        return resumed


__all__ = ["EmbeddingService", "EmbeddingBackfillService"]
