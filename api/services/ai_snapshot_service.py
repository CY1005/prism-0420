"""M16 AISnapshotService — design §6/§8/§10/§11 实装。

编排：create_task / get_task_for_user / save_snapshot / execute_generate。
runner 入口在 api.services.ai_snapshot_runner（自起 SessionLocal / 与请求级 session 隔离）。
zombie cron 入口在 api.services.ai_snapshot_runner.cleanup_zombie_tasks（顶层 task）。

幂等：advisory_xact_lock + find_idempotent（design §11 / audit B1+M6 修复）。
权限：双层校验 GET endpoint（task.user_id == current_user_id 第一层 +
project accessibility 第二层），save endpoint user_id 强制 + path mismatch 校验
（audit B4+M5 修复 / M15 NEW 元教训"双层防御非 dead code"）。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.dao.ai_snapshot_task_dao import AISnapshotTaskDAO
from api.errors.exceptions import (
    AppError,
    SnapshotInsufficientVersionsError,
    SnapshotInvalidDimensionKeyError,
    SnapshotNodeNotFoundError,
    SnapshotNotReadyError,
    SnapshotParseFailedError,
    SnapshotProviderError,
    SnapshotProviderNotConfiguredError,
    SnapshotQuotaExceededError,
    SnapshotSaveFailedError,
    SnapshotTaskNotFoundError,
    SnapshotTaskPathMismatchError,
    SnapshotTimeoutError,
)
from api.models.ai_snapshot_task import AISnapshotTask
from api.schemas.ai_snapshot_schema import (
    AISnapshotContext,
    DimensionRecordSummary,
    SnapshotReviewData,
    VersionRecordSummary,
)
from api.services.ai.provider import (
    LLMProvider,
    ProviderConfigError,
    ProviderError,
    ProviderTimeoutError,
)
from api.services.ai.registry import get_provider
from api.services.ai_snapshot_prompts import build_prompt
from api.services.dimension_service import DimensionService
from api.services.node_service import NodeService
from api.services.project_service import ProjectService
from api.services.version_service import VersionService

_MIN_VERSIONS = 3  # AC1 边界：< 3 拒绝 (422 SNAPSHOT_INSUFFICIENT_VERSIONS)
_TIMEOUT_SECONDS = 600  # design §12B 字段⑤ 服务器硬超时 10min
_SUMMARY_DIMENSION_KEY = "snapshot_summary"


class AISnapshotService:
    """M16 编排（无自有 DAO 直 INSERT；通过 dao + 上游 service）。"""

    def __init__(
        self,
        project_service: ProjectService | None = None,
        node_service: NodeService | None = None,
        version_service: VersionService | None = None,
        dimension_service: DimensionService | None = None,
        dao: AISnapshotTaskDAO | None = None,
    ) -> None:
        self.projects = project_service or ProjectService()
        self.nodes = node_service or NodeService()
        self.versions = version_service or VersionService()
        self.dimensions = dimension_service or DimensionService()
        self.dao = dao or AISnapshotTaskDAO()

    # ─────────────── create_task（POST /generate）───────────────

    async def create_task(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        user_id: UUID,
    ) -> tuple[AISnapshotTask, bool]:
        """advisory_xact_lock + find_idempotent + create。返回 (task, is_idempotent_hit)。

        权限假设：caller (Router) 已通过 check_project_access(role=editor) 过滤；
        本方法不再校验 role，但仍校验 node ∈ project（防 cross-project node 攻击）。

        AC1 边界：version_count < 3 → SnapshotInsufficientVersionsError 422。
        AI provider 未配置 → SnapshotProviderNotConfiguredError 422（提前发现，不让任务
        悄悄进 pending 后被 zombie 转 failed）。
        """
        # 1) 校验 project access + 拿 ai_provider/ai_api_key/ai_model
        project = await self.projects.get_for_user(db, project_id, user_id)
        ai_provider_name = getattr(project, "ai_provider", None)
        if not ai_provider_name:
            raise SnapshotProviderNotConfiguredError(reason="ai_provider_unset")
        ai_model = getattr(project, "ai_model", None) or "default"

        # 2) 校验 node ∈ project（NodeService 抛 NotFoundError 时 wrap）
        try:
            await self.versions.count_by_node(db, project_id=project_id, node_id=node_id)
        except Exception as e:  # NodeNotFoundError / VersionNotFoundError 子类
            raise SnapshotNodeNotFoundError(node_id=str(node_id)) from e
        version_count = await self.versions.count_by_node(
            db, project_id=project_id, node_id=node_id
        )
        if version_count < _MIN_VERSIONS:
            raise SnapshotInsufficientVersionsError(actual=version_count, required=_MIN_VERSIONS)

        # 3) advisory_xact_lock + find_idempotent + create（事务内）
        lock_key = self._advisory_key(user_id, project_id, node_id)
        await db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": lock_key})

        existing = await self.dao.find_idempotent(
            db,
            user_id=user_id,
            project_id=project_id,
            node_id=node_id,
            version_count=version_count,
        )
        if existing is not None:
            return existing, True

        task = await self.dao.create(
            db,
            user_id=user_id,
            project_id=project_id,
            node_id=node_id,
            version_count=version_count,
            ai_provider=ai_provider_name,
            ai_model=ai_model,
            status="pending",
        )
        return task, False

    @staticmethod
    def _advisory_key(user_id: UUID, project_id: UUID, node_id: UUID) -> int:
        """64-bit signed bigint = blake2b(user|project|node)."""
        h = hashlib.blake2b(f"{user_id}:{project_id}:{node_id}".encode(), digest_size=8)
        return int.from_bytes(h.digest(), "big", signed=True)

    # ─────────────── get_task_for_user（GET /snapshot-tasks/{id}）───────────────

    async def get_task_for_user(
        self,
        db: AsyncSession,
        *,
        task_id: UUID,
        current_user_id: UUID,
    ) -> AISnapshotTask:
        """双层校验（design §8 / audit B4 修复 / M15 NEW 元教训"双层防御非 dead code"）：

        - 第一层：task.user_id == current_user_id（防同 project 同事截屏拿 task_id）
        - 第二层：current_user 对 task.project_id 仍有 viewer 权（防被踢出 project 后还能读旧 task）

        所有 404 统一 SnapshotTaskNotFoundError 打码（不区分"不存在 / 不是 creator /
        project 没了"）。
        """
        task = await self.dao.get_by_id(db, task_id)
        if task is None:
            raise SnapshotTaskNotFoundError()
        # 第一层
        if task.user_id != current_user_id:
            raise SnapshotTaskNotFoundError()
        # 第二层
        try:
            await self.projects.get_for_user(db, task.project_id, current_user_id)
        except Exception as e:  # ProjectNotFoundError / ForbiddenError 等
            raise SnapshotTaskNotFoundError() from e
        return task

    # ─────────────── save_snapshot（POST /save）───────────────

    async def save_snapshot(
        self,
        db: AsyncSession,
        *,
        task_id: UUID,
        path_project_id: UUID,
        path_node_id: UUID,
        current_user_id: UUID,
        save_summary: bool,
        selected_dimension_keys: list[str],
    ) -> dict[str, Any]:
        """N+? 次 M04.create_dimension_record（caller 事务 / M04 在内代写 activity_log）。

        校验顺序：
        1) DAO get_by_id(task_id, user_id=current_user_id) 强制 task.user_id 过滤
        2) path / task 一致性（防跨 node 攻击 / audit M5 修复）
        3) status == succeeded（否则 SnapshotNotReadyError 409）
        4) selected_dimension_keys 必须是 review_data.dimensions 子集
        """
        task = await self.dao.get_by_id(db, task_id, user_id=current_user_id)
        if task is None:
            raise SnapshotTaskNotFoundError()
        if task.project_id != path_project_id or task.node_id != path_node_id:
            raise SnapshotTaskPathMismatchError(
                expected_project_id=str(task.project_id),
                expected_node_id=str(task.node_id),
            )
        if task.status != "succeeded":
            raise SnapshotNotReadyError(actual_status=task.status)

        review = SnapshotReviewData(**(task.review_data or {}))
        valid_keys = {d.dimension_type_key for d in review.dimensions}
        invalid = set(selected_dimension_keys) - valid_keys
        if invalid:
            raise SnapshotInvalidDimensionKeyError(invalid=sorted(invalid))

        saved_ids: list[UUID] = []
        try:
            if save_summary:
                rec = await self.dimensions.create_dimension_record(
                    db,
                    project_id=task.project_id,
                    node_id=task.node_id,
                    dimension_type_key=_SUMMARY_DIMENSION_KEY,
                    content={"summary": review.summary},
                    user_id=current_user_id,
                    extra_activity_metadata={"source": "ai_snapshot", "task_id": str(task.id)},
                )
                saved_ids.append(rec.id)
            for dim in review.dimensions:
                if dim.dimension_type_key in selected_dimension_keys:
                    rec = await self.dimensions.create_dimension_record(
                        db,
                        project_id=task.project_id,
                        node_id=task.node_id,
                        dimension_type_key=dim.dimension_type_key,
                        content=dim.content,
                        user_id=current_user_id,
                        extra_activity_metadata={
                            "source": "ai_snapshot",
                            "task_id": str(task.id),
                        },
                    )
                    saved_ids.append(rec.id)
        except AppError:
            # 业务语义错（cross-project node / type 禁用 / 等）保留语义，不吞为 SaveFailed
            raise
        except Exception as e:
            raise SnapshotSaveFailedError() from e
        return {
            "saved_dimension_record_ids": saved_ids,
            "saved_count": len(saved_ids),
            "summary_saved": save_summary,
        }

    # ─────────────── execute_generate（runner 内调用）───────────────

    async def execute_generate(
        self,
        db: AsyncSession,
        task: AISnapshotTask,
    ) -> tuple[dict[str, Any], int]:
        """聚合上游 context + 调 provider + parse JSON。

        返回 (review_data dict, generation_time_ms)。

        异常逐项 wrap 为 Snapshot* 错误（design §13 R13-2）；runner cas_complete
        时根据异常 type 选 error_code（SNAPSHOT_TIMEOUT / SNAPSHOT_PROVIDER_ERROR /
        SNAPSHOT_PARSE_FAILED / SNAPSHOT_QUOTA_EXCEEDED / SNAPSHOT_PROVIDER_NOT_CONFIGURED）。
        """
        start = time.monotonic()

        # 1) 拿 project + 构 provider
        project = await self.projects.get_for_user(db, task.project_id, task.user_id)
        provider = self._build_provider_from_project(project)

        # 2) 聚合 context
        ctx = await self._fetch_context(db, task=task)

        # 3) 调 provider 流式 + collect chunks（M16 fire-and-forget 不需边 yield 边返回）
        system_context, user_prompt = build_prompt(ctx=ctx)
        stream = provider.analyze(user_prompt, context=system_context)
        full_text_parts: list[str] = []
        try:
            async with asyncio.timeout(_TIMEOUT_SECONDS):
                async for chunk in stream:
                    full_text_parts.append(chunk)
        except TimeoutError as e:
            raise SnapshotTimeoutError() from e
        except ProviderTimeoutError as e:
            raise SnapshotTimeoutError() from e
        except ProviderError as e:
            raise self._wrap_provider_error(e) from e
        finally:
            await stream.aclose()

        full_text = "".join(full_text_parts).strip()

        # 4) parse JSON（AI 输出非 JSON → SnapshotParseFailedError）
        try:
            review_obj = json.loads(full_text)
            # 严格 schema 校验
            review = SnapshotReviewData(**review_obj)
        except Exception as e:
            raise SnapshotParseFailedError(snippet=full_text[:200]) from e

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return review.model_dump(), elapsed_ms

    # ─────────────── 内部 helpers ───────────────

    def _build_provider_from_project(self, project: Any) -> LLMProvider:
        """与 M13 同款（拆字段 + AES 解密 + Registry 工厂）。"""
        from api.auth.crypto import CryptoDecryptError, decrypt

        ai_provider_name = getattr(project, "ai_provider", None)
        if not ai_provider_name:
            raise SnapshotProviderNotConfiguredError(reason="ai_provider_unset")

        api_key: str | None = None
        enc = getattr(project, "ai_api_key_enc", None)
        if enc:
            try:
                api_key = decrypt(enc)
            except CryptoDecryptError as e:
                raise SnapshotProviderNotConfiguredError(reason="api_key_decrypt_failed") from e

        model = getattr(project, "ai_model", None)
        try:
            return get_provider(ai_provider_name, api_key=api_key, model=model)
        except ProviderConfigError as e:
            raise SnapshotProviderNotConfiguredError(provider=e.provider, reason=e.reason) from e

    async def _fetch_context(self, db: AsyncSession, *, task: AISnapshotTask) -> AISnapshotContext:
        """聚合 node + versions + dimensions + dimension_keys。"""
        try:
            node = await self.nodes.get_node(db, task.node_id, task.project_id)
        except Exception as e:
            raise SnapshotNodeNotFoundError(node_id=str(task.node_id)) from e

        versions_raw = await self.versions.list_by_node(
            db, project_id=task.project_id, node_id=task.node_id
        )
        versions = [
            VersionRecordSummary(
                id=v.id,
                version_label=v.version_label,
                description=getattr(v, "details", None),
                created_at=v.created_at,
            )
            for v in versions_raw
        ]

        dims_raw = await self.dimensions.list_by_node(
            db, project_id=task.project_id, node_id=task.node_id
        )
        current_dims = [
            DimensionRecordSummary(
                dimension_type_key=getattr(d, "dimension_type_key", None)
                or self._resolve_dim_key(d),
                content=d.content or {},
            )
            for d in dims_raw
        ]
        dimension_keys = [d.dimension_type_key for d in current_dims if d.dimension_type_key]

        return AISnapshotContext(
            node_name=node.name,
            versions=versions,
            current_dimensions=current_dims,
            dimension_keys=dimension_keys,
        )

    @staticmethod
    def _resolve_dim_key(dim_record: Any) -> str:
        """fallback：从 dimension_type relationship 拿 key。"""
        dt = getattr(dim_record, "dimension_type", None)
        return getattr(dt, "key", "") if dt is not None else ""

    @staticmethod
    def _wrap_provider_error(e: ProviderError) -> Exception:
        """Provider* → Snapshot* 异常映射（design §13 R13-2）。"""
        if e.reason == "rate_limited":
            return SnapshotQuotaExceededError()
        return SnapshotProviderError()
