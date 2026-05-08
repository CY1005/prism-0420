"""M17 AI 智能导入 Service（design/02-modules/M17-ai-import/00-design.md §6/§8/§10/§11/§12）。

R-X1 第二实例（M11 ColdStart 第一实例 / Queue 异步形态）：
- 业务路径走 Queue worker 自起 SessionLocal（请求级 Depends(get_db) 隔离）
- 失败补偿走 compensation_session helper（独立 connection / 与业务事务隔离）
- 任务创建后立即 commit（让独立 connection 能看到任务）
- batch_insert 阶段 M17 不直 INSERT 跨模块表，调 M03/M04/M06/M07 batch_create_in_transaction

idempotency（design §11 / B1 修复）：
- key = (user_id, project_id, source_hash) 7 天内复用 status ∈ {completed, awaiting_review, partial_failed}
- service 层先 find_idempotent → 未命中再 INSERT；INSERT 端到端 catch IntegrityError 转
  ImportTaskDuplicateError（design-principles 清单 6 落地 / IMPORT_TASK_DUPLICATE 落地）

权限三层（design §8）：
- Router：check_project_access(role="editor") 粗粒度
- Service：check_task_access(user_id, project_id, task_id) 细粒度（worker 自起入口必调）
- WS 握手：handle_import_progress_ws 在 accept 前调 check_task_access

10 类失败路径全经 _mark_failed（compensation_session 独立 connection）。
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.dao.import_task_dao import (
    DEAD_LETTER_RETENTION_DAYS,
    ImportTaskDAO,
    ImportTaskItemDAO,
)
from api.errors.exceptions import (
    ImportAIProviderError,
    ImportBatchInsertFailedError,
    ImportInvalidSourceError,
    ImportInvalidStateTransitionError,
    ImportTaskDuplicateError,
    ImportTaskFinalizedError,
    ImportTaskNotFoundError,
)
from api.models.import_task import (
    ImportSourceType,
    ImportTask,
    ImportTaskItem,
    ImportTaskItemStatus,
    ImportTaskStatus,
)
from api.queue.import_tasks import ConfirmedImportData
from api.schemas.import_schema import ProgressEvent
from api.services.activity_log_service import write_event
from api.services.ai_orchestration_service import AIOrchestrationService
from api.services.competitor_service import CompetitorService
from api.services.dimension_service import DimensionService
from api.services.issue_service import IssueService
from api.services.node_service import NodeService
from api.services.orchestrator_helpers import compensation_session
from api.services.project_service import ProjectService
from api.ws.import_progress import publish_progress

log = logging.getLogger(__name__)

# 终态 / 半终态（design §4 字面）
_FINAL_STATUSES = frozenset(
    {
        ImportTaskStatus.completed.value,
        ImportTaskStatus.failed.value,
        ImportTaskStatus.cancelled.value,
    }
)
# partial_failed 是半终态：可循环回 ai_step3（R4-3a）
# IMPL-NOTE（R1-A P1-1）：design §10 列 import_partial_failed 事件 + R4-3a 入边
# ① importing 部分 item 失败 ② ai_step2 部分文件失败。本期 design §4 决策
# importing = 整任务 single transaction（all-or-nothing），任何 batch_insert 路径
# 异常一律 _mark_failed → status=failed（不写 partial_failed）；ai_step2 当前未做
# chunk 化，整步失败也走 failed。partial_failed 仅保留：① 入边 enum 字面（防 ALTER
# TABLE 改 CHECK）② retry 出边（partial_failed → ai_step3）以备 ai_step2 chunk 化或
# importing per-step 拆分时启用。R1-A P1-1 实证：本期不发射，retry_task 路径靠 fixture
# 直造状态测试，不依赖业务可达。
_RESUMABLE_STATUSES = frozenset({ImportTaskStatus.partial_failed.value})

# idempotency 复用范围（design §11）
_IDEMPOTENT_REUSE_STATUSES = frozenset(
    {
        ImportTaskStatus.completed.value,
        ImportTaskStatus.awaiting_review.value,
        ImportTaskStatus.partial_failed.value,
    }
)


class ImportService:
    """M17 编排——任务状态机 + idempotency + R-X1 batch_insert 跨模块 orchestrator。"""

    def __init__(
        self,
        dao: ImportTaskDAO | None = None,
        item_dao: ImportTaskItemDAO | None = None,
        ai_orchestration: AIOrchestrationService | None = None,
        project_service: ProjectService | None = None,
        node_service: NodeService | None = None,
        dimension_service: DimensionService | None = None,
        competitor_service: CompetitorService | None = None,
        issue_service: IssueService | None = None,
    ) -> None:
        self.dao = dao or ImportTaskDAO()
        self.item_dao = item_dao or ImportTaskItemDAO()
        self.ai = ai_orchestration or AIOrchestrationService()
        self.projects = project_service or ProjectService()
        self.nodes = node_service or NodeService()
        self.dimensions = dimension_service or DimensionService()
        self.competitors = competitor_service or CompetitorService()
        self.issues = issue_service or IssueService()

    # ─────────────── 提交导入任务 ───────────────

    async def submit_import(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        project_id: UUID,
        source_type: ImportSourceType,
        source_hash: str,
        source_uri: str,
        ai_provider: str,
        ai_model: str,
        items_metadata: Sequence[dict[str, Any]] = (),
    ) -> ImportTask:
        """提交新导入任务。

        idempotency 路径（design §11）：
        - 先 find_idempotent；命中 → raise ImportTaskDuplicateError(existing_task)
          （router 层 catch 后改返 200；http_status=200 by design §13 字面）
        - 未命中 → INSERT；端到端 catch IntegrityError（race 时 UNIQUE 触发）转
          ImportTaskDuplicateError（清单 6 / B1 修复）

        副作用：
        - 创建 ImportTask（status=pending）+ N 条 ImportTaskItem
        - 写 import_created activity_log
        - 立即 db.commit()（让 task 行脱离批量入库事务，R-X1 失败补偿可见性前提）
        - 把 import_extract 任务塞 Queue（caller 拿到 task 后由 router/queue worker 真 enqueue）
        """
        # 1) idempotency 检查（命中 → raise duplicate）
        existing = await self.dao.find_idempotent(
            db, user_id=user_id, project_id=project_id, source_hash=source_hash
        )
        if existing is not None:
            raise ImportTaskDuplicateError(
                existing_task_id=str(existing.id),
                existing_status=existing.status,
            )

        # 2) INSERT 端到端 catch IntegrityError（清单 6 / B1 修复）
        task = ImportTask(
            project_id=project_id,
            user_id=user_id,
            source_type=source_type.value
            if isinstance(source_type, ImportSourceType)
            else str(source_type),
            source_hash=source_hash,
            source_uri=source_uri,
            status=ImportTaskStatus.pending.value,
            progress=0,
            ai_provider=ai_provider,
            ai_model=ai_model,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        try:
            await self.dao.create(db, task)
        except IntegrityError as e:
            # R1 P1 立修（M05 P1-01 立规延续）：区分 uq_import_user_project_hash UNIQUE
            # vs 其他约束（CHECK / FK），不再统一走 select 兜底（防误转误分类）。
            await db.rollback()
            constraint_str = str(getattr(e.orig, "args", "")) + str(e.orig)
            if "uq_import_user_project_hash" in constraint_str:
                # UNIQUE(user_id, project_id, source_hash) 命中：race 或 failed/cancelled
                # 仍占用 key（design §11："failed/cancelled 不复用"但 DB UNIQUE 没分 status）
                stmt = select(ImportTask).where(
                    ImportTask.user_id == user_id,
                    ImportTask.project_id == project_id,
                    ImportTask.source_hash == source_hash,
                )
                result = await db.execute(stmt)
                existing2 = result.scalar_one_or_none()
                if existing2 is not None:
                    raise ImportTaskDuplicateError(
                        existing_task_id=str(existing2.id),
                        existing_status=existing2.status,
                    ) from e
            # 非 UNIQUE 撞（CHECK / FK / 其他）→ 422 业务参数无效
            raise ImportInvalidSourceError(reason="db_constraint_failed") from e

        # 3) bulk insert items（解压 / clone 阶段才知道全部文件，提交时仅 metadata 占位）
        if items_metadata:
            items = [
                ImportTaskItem(
                    task_id=task.id,
                    file_path=str(m["file_path"]),
                    file_size=int(m.get("file_size", 0)),
                    status=ImportTaskItemStatus.pending.value,
                )
                for m in items_metadata
            ]
            await self.item_dao.bulk_create(db, items)

        # 4) activity_log 创建事件
        await write_event(
            db=db,
            actor_user_id=user_id,
            project_id=project_id,
            action_type="import_created",
            target_type="import_task",
            target_id=str(task.id),
            summary="创建了 AI 智能导入任务",
            metadata={
                "source_type": task.source_type,
                "source_hash": source_hash,
                "ai_provider": ai_provider,
                "ai_model": ai_model,
                "items_count": len(items_metadata),
            },
        )

        # 5) ★ 立即 commit（M11 R-X1 第一实例同款；让 task 行脱离批量入库事务）
        await db.commit()
        await db.refresh(task)
        return task

    # ─────────────── 读 ───────────────

    async def get_task(
        self,
        db: AsyncSession,
        *,
        task_id: UUID,
        project_id: UUID,
    ) -> ImportTask:
        """单任务（404 → ImportTaskNotFoundError；强制 project tenant 过滤）。"""
        t = await self.dao.get_by_id(db, task_id, project_id)
        if t is None:
            raise ImportTaskNotFoundError(task_id=str(task_id))
        return t

    async def list_by_project(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        user_id: UUID,
        limit: int = 50,
    ) -> Sequence[ImportTask]:
        return await self.dao.list_by_project(db, project_id, user_id, limit=limit)

    async def get_review_data(
        self,
        db: AsyncSession,
        *,
        task_id: UUID,
        project_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        """拉取 review 阶段数据（status 必须 awaiting_review / partial_failed）。"""
        task = await self._get_task_for_user(db, task_id, project_id, user_id)
        if task.status not in (
            ImportTaskStatus.awaiting_review.value,
            ImportTaskStatus.partial_failed.value,
        ):
            raise ImportInvalidStateTransitionError(
                actual_status=task.status,
                allowed=("awaiting_review", "partial_failed"),
            )
        return task.review_data or {}

    # ─────────────── 用户确认 review ───────────────

    async def confirm_review(
        self,
        db: AsyncSession,
        *,
        task_id: UUID,
        project_id: UUID,
        user_id: UUID,
        confirmed: ConfirmedImportData,
    ) -> ImportTask:
        """awaiting_review → ai_step3（→ importing）。

        副作用：
        - review_data 写入 confirmed dict（覆盖原 AI 输出）
        - 状态 awaiting_review → ai_step3
        - 写 import_review_confirmed activity_log
        - caller 接到 task 后由 router 真 enqueue import_ai_step3 + import_batch_insert
        """
        task = await self._get_task_for_user(db, task_id, project_id, user_id)
        if task.status in _FINAL_STATUSES:
            raise ImportTaskFinalizedError(actual_status=task.status)
        if task.status != ImportTaskStatus.awaiting_review.value:
            raise ImportInvalidStateTransitionError(
                actual_status=task.status,
                allowed=("awaiting_review",),
            )

        await self.dao.update(
            db,
            task.id,
            project_id,
            fields={
                "status": ImportTaskStatus.ai_step3.value,
                "progress": 70,
                "review_data": confirmed.model_dump(mode="json"),
            },
        )
        await write_event(
            db=db,
            actor_user_id=user_id,
            project_id=project_id,
            action_type="import_review_confirmed",
            target_type="import_task",
            target_id=str(task.id),
            summary="用户确认 review",
            metadata={
                "nodes_count": len(confirmed.nodes),
                "skip_count": len(confirmed.skip_proposed_ids)
                + sum(1 for n in confirmed.nodes if n.skipped),
                "dimensions_count": len(confirmed.dimensions),
                "competitors_count": len(confirmed.competitors),
                "issues_count": len(confirmed.issues),
            },
        )
        await db.refresh(task)
        return task

    # ─────────────── 取消 / 重试 ───────────────

    async def cancel_task(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        project_id: UUID,
        task_id: UUID,
    ) -> ImportTask:
        """任意非终态 → cancelled（Q5 选 a：取消即删，接受 AI token 浪费）。

        权限三层第三层（design §8）：tenant + owner 双层校验；任一失败 → 404 打码。
        """
        task = await self._get_task_for_user(db, task_id, project_id, user_id)
        if task.status in _FINAL_STATUSES:
            raise ImportTaskFinalizedError(actual_status=task.status)

        await self.dao.update(
            db,
            task.id,
            task.project_id,
            fields={"status": ImportTaskStatus.cancelled.value, "progress": 100},
        )
        await write_event(
            db=db,
            actor_user_id=user_id,
            project_id=task.project_id,
            action_type="import_canceled",
            target_type="import_task",
            target_id=str(task.id),
            summary="用户取消导入任务",
            metadata={"at_status": task.status},
        )
        await db.refresh(task)
        with contextlib.suppress(Exception):
            await publish_progress(
                ProgressEvent(
                    type="status_change",
                    task_id=task.id,
                    progress=100,
                    status=ImportTaskStatus.cancelled.value,
                    message="cancelled",
                )
            )
        return task

    async def retry_task(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        project_id: UUID,
        task_id: UUID,
    ) -> ImportTask:
        """partial_failed → ai_step3（半终态出边唯一合法转换）。"""
        task = await self._get_task_for_user(db, task_id, project_id, user_id)
        if task.status not in _RESUMABLE_STATUSES:
            raise ImportInvalidStateTransitionError(
                actual_status=task.status,
                allowed=("partial_failed",),
            )
        await self.dao.update(
            db,
            task.id,
            project_id,
            fields={"status": ImportTaskStatus.ai_step3.value, "progress": 70},
        )
        await write_event(
            db=db,
            actor_user_id=user_id,
            project_id=project_id,
            action_type="import_status_changed",
            target_type="import_task",
            target_id=str(task.id),
            summary="重试 partial_failed 任务",
            metadata={"old_status": "partial_failed", "new_status": "ai_step3"},
        )
        await db.refresh(task)
        return task

    # ─────────────── worker re-auth ───────────────

    async def check_task_access(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        project_id: UUID,
        task_id: UUID,
    ) -> ImportTask:
        """Queue worker / WS 握手入口的 P2 二次校验（ADR-002 §1）。

        三选一返回 ImportTaskNotFoundError（不区分 not-found vs cross-tenant vs 越权）：
        - task 不存在
        - task.project_id != project_id
        - task.user_id != user_id
        """
        task = await self.dao.get_by_id(db, task_id, project_id)
        if task is None or task.user_id != user_id:
            raise ImportTaskNotFoundError(task_id=str(task_id))
        return task

    # ─────────────── Queue worker entry: extract ───────────────

    async def run_extract(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        project_id: UUID,
        task_id: UUID,
    ) -> None:
        """import_extract Queue task 入口（pending → extracting → ai_step1）。

        M17 sprint 范围：解压 zip / git clone 实际逻辑由 storage_client 实现（horizontal
        helper / 后续 sprint 落地）；本方法仅状态扭转 + 触发下一步 enqueue。
        """
        task = await self.check_task_access(
            db, user_id=user_id, project_id=project_id, task_id=task_id
        )
        if task.status in _FINAL_STATUSES:
            return  # cancelled/completed/failed 已终态，幂等退出
        try:
            await self._transition(
                db, task, new_status=ImportTaskStatus.extracting.value, progress=10
            )
            # M17 sprint scaffold：实际解压由 storage_client 落地（future sprint）
            # 当前路径 caller 已在 submit 时把 items_metadata 写好；此处仅完成 transition
            await self._transition(
                db, task, new_status=ImportTaskStatus.ai_step1.value, progress=20
            )
            await db.commit()
        except ImportInvalidSourceError:
            await self._mark_failed(
                task,
                project_id,
                user_id,
                stage="extract",
                error_code="import_invalid_source",
                error_message="extract failed (corrupted source)",
            )
            raise
        except Exception as e:
            log.exception("import_extract task=%s unexpected", task.id)
            await self._mark_failed(
                task,
                project_id,
                user_id,
                stage="extract",
                error_code="import_invalid_source",
                error_message=str(e)[:500],
            )
            raise

    # ─────────────── Queue worker entry: ai_step ───────────────

    async def run_ai_step(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        project_id: UUID,
        task_id: UUID,
        step: int,
    ) -> None:
        """import_ai_step{1,2,3} Queue task 入口。

        - step 1: ai_step1 → ai_step2（拆分+归类）
        - step 2: ai_step2 → awaiting_review（提取+补全 / 推 review_ready 事件）
        - step 3: ai_step3 → importing（关联+去重，consolidate_step3 不调 LLM）
        """
        task = await self.check_task_access(
            db, user_id=user_id, project_id=project_id, task_id=task_id
        )
        if task.status in _FINAL_STATUSES:
            return

        try:
            if step in (1, 2):
                project = await self.projects.get_for_user(db, project_id, user_id)
                provider = AIOrchestrationService.build_provider_from_project(project)
                items = await self.item_dao.list_by_task(db, task_id=task.id)
                items_summary = [
                    {"file_path": i.file_path, "file_size": i.file_size} for i in items
                ]
                if step == 1:
                    out = await self.ai.run_step1(provider=provider, items_summary=items_summary)
                    review_data = {"proposed_nodes": out.get("nodes", [])}
                    await self._transition(
                        db,
                        task,
                        new_status=ImportTaskStatus.ai_step2.value,
                        progress=40,
                        review_data=review_data,
                    )
                    await self._write_step_complete(
                        db, task, project_id, user_id, step=1, items_count=len(items)
                    )
                else:  # step 2
                    existing_review = task.review_data or {}
                    out = await self.ai.run_step2(
                        provider=provider,
                        proposed_nodes=existing_review.get("proposed_nodes", []),
                        items_summary=items_summary,
                    )
                    review_data = {
                        **existing_review,
                        "proposed_dimensions": out.get("dimensions", []),
                        "proposed_competitors": out.get("competitors", []),
                        "proposed_issues": out.get("issues", []),
                    }
                    await self._transition(
                        db,
                        task,
                        new_status=ImportTaskStatus.awaiting_review.value,
                        progress=60,
                        review_data=review_data,
                    )
                    await self._write_step_complete(
                        db, task, project_id, user_id, step=2, items_count=len(items)
                    )
                    with contextlib.suppress(Exception):
                        await publish_progress(
                            ProgressEvent(
                                type="review_ready",
                                task_id=task.id,
                                progress=60,
                                status=ImportTaskStatus.awaiting_review.value,
                                message="review ready",
                            )
                        )
            elif step == 3:
                # 不调 LLM；仅 consolidate confirmed_data
                review_data = task.review_data or {}
                # confirm_review 已把 ConfirmedImportData 落到 review_data；此处仅 consolidate
                confirmed_dict = review_data
                consolidated = AIOrchestrationService.consolidate_step3(confirmed_dict)
                await self._transition(
                    db,
                    task,
                    new_status=ImportTaskStatus.importing.value,
                    progress=80,
                    review_data=consolidated,
                )
                await self._write_step_complete(
                    db,
                    task,
                    project_id,
                    user_id,
                    step=3,
                    items_count=len(consolidated.get("nodes", [])),
                )
            else:
                raise ValueError(f"invalid step={step}")

            await db.commit()
        except (ImportAIProviderError, ImportInvalidSourceError) as e:
            await self._mark_failed(
                task,
                project_id,
                user_id,
                stage=f"ai_step{step}",
                error_code=getattr(e, "code", "import_ai_provider_error").value
                if hasattr(getattr(e, "code", None), "value")
                else "import_ai_provider_error",
                error_message=str(getattr(e, "message", str(e)))[:500],
            )
            raise
        except Exception as e:
            log.exception("import_ai_step%s task=%s unexpected", step, task.id)
            await self._mark_failed(
                task,
                project_id,
                user_id,
                stage=f"ai_step{step}",
                error_code="import_ai_provider_error",
                error_message=str(e)[:500],
            )
            raise

    # ─────────────── Queue worker entry: batch_insert ───────────────

    async def run_batch_insert(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        project_id: UUID,
        task_id: UUID,
        confirmed: ConfirmedImportData,
    ) -> None:
        """import_batch_insert Queue task 入口（importing → completed/partial_failed）。

        R-X1 第二实例（M11 ColdStart 同款）：
        - M17 不直 INSERT 跨模块表
        - 调 4 个 service.batch_create_in_transaction（共享 db；任一失败回滚）
        - 失败补偿走 compensation_session（独立 connection）
        """
        task = await self.check_task_access(
            db, user_id=user_id, project_id=project_id, task_id=task_id
        )
        if task.status in _FINAL_STATUSES:
            return
        if task.status not in (
            ImportTaskStatus.importing.value,
            ImportTaskStatus.ai_step3.value,
        ):
            raise ImportInvalidStateTransitionError(
                actual_status=task.status,
                allowed=("importing", "ai_step3"),
            )

        # 确保进入 importing
        if task.status != ImportTaskStatus.importing.value:
            await self._transition(
                db, task, new_status=ImportTaskStatus.importing.value, progress=80
            )

        # consolidate（防 confirm 阶段未跑过；幂等）
        confirmed_dict = confirmed.model_dump(mode="json")
        consolidated = AIOrchestrationService.consolidate_step3(confirmed_dict)

        try:
            # ① M03 nodes — 拓扑顺序由 batch_create_in_transaction 内部保证
            nodes_data = [
                {
                    "name": n["name"],
                    "type": n.get("type", "leaf"),
                    "parent_temp_id": n.get("parent_proposed_id"),
                    "temp_id": n["proposed_id"],
                }
                for n in consolidated.get("nodes", [])
            ]
            created_nodes = await self.nodes.batch_create_in_transaction(
                db,
                project_id=project_id,
                actor_user_id=user_id,
                nodes_data=nodes_data,
            )
            temp_to_real: dict[Any, UUID] = {}
            for raw, real in zip(nodes_data, created_nodes, strict=True):
                if "temp_id" in raw:
                    temp_to_real[raw["temp_id"]] = real.id

            # ② M04 dimensions
            # R1-C P1-01 立修：批量预查 dimension_types（防 N+1 / N 条 dimensions 200 次 SELECT）
            # M04 batch_create_in_transaction 接 dimension_type_id 而非 key；M17 sprint scaffold：
            # dimension_type_key → upsert 在 service 层做（与 M13 baseline-patch 同款逻辑）。
            dim_keys_unique = list(
                {
                    d["dimension_type_key"]
                    for d in consolidated.get("dimensions", [])
                    if temp_to_real.get(d["target_proposed_node_id"]) is not None
                }
            )
            dim_type_cache: dict[str, Any] = {}
            for k in dim_keys_unique:
                dim_type_cache[k] = await self.dimensions._upsert_dimension_type(  # noqa: SLF001
                    db, k
                )
            dimensions_data: list[dict[str, Any]] = []
            for d in consolidated.get("dimensions", []):
                node_real_id = temp_to_real.get(d["target_proposed_node_id"])
                if node_real_id is None:
                    continue
                dt = dim_type_cache[d["dimension_type_key"]]
                dimensions_data.append(
                    {
                        "node_id": node_real_id,
                        "dimension_type_id": dt.id,
                        "content": d.get("content") or {},
                    }
                )
            if dimensions_data:
                await self.dimensions.batch_create_in_transaction(
                    db,
                    project_id=project_id,
                    actor_user_id=user_id,
                    dimensions_data=dimensions_data,
                )

            # ③ M06 competitors
            competitors_data = [
                {
                    "display_name": c["display_name"],
                    "website_url": c.get("website_url"),
                    "description": c.get("description"),
                }
                for c in consolidated.get("competitors", [])
            ]
            if competitors_data:
                await self.competitors.batch_create_in_transaction(
                    db,
                    project_id=project_id,
                    actor_user_id=user_id,
                    competitors_data=competitors_data,
                )

            # ④ M07 issues
            issues_data: list[dict[str, Any]] = []
            for i in consolidated.get("issues", []):
                node_real_id = (
                    temp_to_real.get(i["target_proposed_node_id"])
                    if i.get("target_proposed_node_id")
                    else None
                )
                issues_data.append(
                    {
                        "category": i["category"],
                        "title": i["title"],
                        "description": i.get("description") or i["title"],
                        "node_id": node_real_id,
                    }
                )
            if issues_data:
                await self.issues.batch_create_in_transaction(
                    db,
                    project_id=project_id,
                    actor_user_id=user_id,
                    issues_data=issues_data,
                )

        except Exception as e:
            await self._mark_failed(
                task,
                project_id,
                user_id,
                stage="batch_insert",
                error_code="import_batch_insert_failed",
                error_message=str(e)[:500],
            )
            raise ImportBatchInsertFailedError(reason=str(e)) from e

        # 全成功 → completed
        completed_at = datetime.now(UTC)
        await self.dao.update(
            db,
            task.id,
            project_id,
            fields={
                "status": ImportTaskStatus.completed.value,
                "progress": 100,
                "completed_at": completed_at,
            },
        )
        await write_event(
            db=db,
            actor_user_id=user_id,
            project_id=project_id,
            action_type="import_batch_inserted",
            target_type="import_task",
            target_id=str(task.id),
            summary="批量入库完成",
            metadata={
                "nodes": len(consolidated.get("nodes", [])),
                "dimensions": len(consolidated.get("dimensions", [])),
                "competitors": len(consolidated.get("competitors", [])),
                "issues": len(consolidated.get("issues", [])),
            },
        )
        await db.commit()
        await db.refresh(task)
        with contextlib.suppress(Exception):
            await publish_progress(
                ProgressEvent(
                    type="completed",
                    task_id=task.id,
                    progress=100,
                    status=ImportTaskStatus.completed.value,
                    message="completed",
                )
            )

    # ─────────────── 死信清理 ───────────────

    async def cleanup_dead_letter(
        self,
        db: AsyncSession,
        *,
        system_user_id: UUID,
        retention_days: int = DEAD_LETTER_RETENTION_DAYS,
    ) -> int:
        """物理删 status=failed 且 created_at < NOW - retention_days 的死信任务。

        ADR-002 §1.1：cron user_id 必须 = SYSTEM_USER_UUID（caller 在 Queue payload
        强制；本 service 仅信任入参）。housekeeping 不写 activity_log（design §12 字面）。
        """
        orphans = await self.dao.find_dead_letter_orphans(db, retention_days=retention_days)
        count = 0
        for t in orphans:
            n = await self.dao.delete(db, t.id, t.project_id)
            count += n
        return count

    # ─────────────── 内部 helpers ───────────────

    async def _get_task_for_user(
        self,
        db: AsyncSession,
        task_id: UUID,
        project_id: UUID,
        user_id: UUID,
    ) -> ImportTask:
        """tenant + owner 双层校验（design §8 第三层）。"""
        task = await self.dao.get_by_id(db, task_id, project_id)
        if task is None or task.user_id != user_id:
            raise ImportTaskNotFoundError(task_id=str(task_id))
        return task

    async def _transition(
        self,
        db: AsyncSession,
        task: ImportTask,
        *,
        new_status: str,
        progress: int,
        review_data: dict[str, Any] | None = None,
    ) -> None:
        """状态扭转 + progress + 推 progress_update 事件。

        终态 / 半终态校验放 caller 处（不同入口规则不同）。
        """
        fields: dict[str, Any] = {"status": new_status, "progress": progress}
        if review_data is not None:
            fields["review_data"] = review_data
        old_status = task.status
        await self.dao.update(db, task.id, task.project_id, fields=fields)
        # 同步本地对象（caller 后续逻辑可能读 task.status）
        task.status = new_status
        task.progress = progress
        if review_data is not None:
            task.review_data = review_data

        # 写 import_status_changed
        try:
            await write_event(
                db=db,
                actor_user_id=task.user_id,
                project_id=task.project_id,
                action_type="import_status_changed",
                target_type="import_task",
                target_id=str(task.id),
                summary=f"任务状态：{old_status}→{new_status}",
                metadata={
                    "old_status": old_status,
                    "new_status": new_status,
                    "progress": progress,
                },
            )
        except Exception:
            log.exception("import status_change log failed task=%s", task.id)

        await publish_progress(
            ProgressEvent(
                type="status_change",
                task_id=task.id,
                progress=progress,
                status=new_status,
                message=f"{old_status}→{new_status}",
            )
        )

    @staticmethod
    async def _write_step_complete(
        db: AsyncSession,
        task: ImportTask,
        project_id: UUID,
        user_id: UUID,
        *,
        step: int,
        items_count: int,
    ) -> None:
        try:
            await write_event(
                db=db,
                actor_user_id=user_id,
                project_id=project_id,
                action_type="import_ai_step_completed",
                target_type="import_task",
                target_id=str(task.id),
                summary=f"AI 步骤 {step} 完成",
                metadata={"step": step, "items_processed": items_count},
            )
        except Exception:
            log.exception("import_ai_step%s log failed task=%s", step, task.id)

    async def _mark_failed(
        self,
        task: ImportTask,
        project_id: UUID,
        actor_user_id: UUID,
        *,
        stage: str,
        error_code: str,
        error_message: str,
    ) -> None:
        """task=failed + import_failed 事件落盘（compensation_session 独立 connection）。

        立规来源（M11 R-X1 第一实例 / M17 第二实例 docstring 字面对照）：
        feedback_rx1_orchestrator_design L1 + design-principles 清单 6（commit boundary 隔离）。
        """
        async with compensation_session() as comp_db:
            await self.dao.update(
                comp_db,
                task.id,
                project_id,
                fields={
                    "status": ImportTaskStatus.failed.value,
                    "progress": task.progress or 0,
                    "error_message": error_message,
                    "error_metadata": {
                        "stage": stage,
                        "error_code": error_code,
                        "dead_letter": False,
                    },
                },
            )
            try:
                await write_event(
                    db=comp_db,
                    actor_user_id=actor_user_id,
                    project_id=project_id,
                    action_type="import_failed",
                    target_type="import_task",
                    target_id=str(task.id),
                    summary=f"导入任务失败：{stage}",
                    metadata={
                        "stage": stage,
                        "error_code": error_code,
                    },
                )
            except Exception as log_err:
                log.warning(
                    "import._mark_failed.write_event_failed task=%s code=%s err=%s",
                    task.id,
                    error_code,
                    log_err,
                )
            await comp_db.commit()
        with contextlib.suppress(Exception):
            await publish_progress(
                ProgressEvent(
                    type="error",
                    task_id=task.id,
                    progress=task.progress or 0,
                    status=ImportTaskStatus.failed.value,
                    message=error_message,
                    metadata={"stage": stage, "error_code": error_code},
                )
            )


__all__ = [
    "ImportService",
]
