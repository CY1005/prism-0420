"""M18 Embedding Admin router — design §6 line 576 / §7 line 617-619 / §8 line 675。

3 endpoints（platform_admin only）：
  - POST /api/admin/embedding/backfill        → BackfillResponse 202 异步
  - POST /api/admin/embedding/model-upgrade   → ModelUpgradeResponse 202 异步
  - GET  /api/admin/embedding/stats           → EmbeddingStatsResponse 同步

权限（design §8 line 675）：
  - 全部 endpoints：Depends(require_platform_admin)  ADR-004 P1

activity_log（design §10 line 828-829）：
  - backfill_triggered：write_event(action_type="embedding_backfill_triggered",
      target_type="project", target_id=project_id,
      metadata={trigger_reason, affected_count})
  - model_upgrade_triggered：write_event(action_type="embedding_model_upgrade_triggered",
      target_type="project", target_id=project_id,
      metadata={old_model, new_model, affected_count})

元教训（design §14.5）：
  - viewer 写 403：admin endpoint require_platform_admin 守护（M07 立 / M18 应用立规）
    non-platform_admin 调任意 admin endpoint → 403 permission_denied
  - write_event 异常传播：write_event raise → backfill/model-upgrade 应回滚 + 500（M16 立）
  - cross-tenant 404：admin endpoint 不走 project_member check
    （platform_admin 可操作任意 project；但 project_id 不存在 → EmbeddingBackfillNotFoundError）
  - M16 CAS UPDATE 顶层方法内部 commit / 禁 Service 事务上下文：admin endpoint 不开 begin（N/A）
  - M16 BackgroundTasks / Queue runner 自起 SessionLocal：backfill 走 BackgroundTasks 范式
  - R-X1 失败补偿：admin endpoint 无补偿形态（M17 N/A 显式）
  - M11 file.size / sanitize：admin endpoint 无 multipart（M11 N/A 显式）
  - M13 SSE 形态：admin endpoint 同步/202（M13 N/A 显式）
  - M17 compensation_session helper：M18 不触（N/A 显式）
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.db import SessionLocal, get_db
from api.errors.exceptions import PermissionDeniedError
from api.models.user import User
from api.routers.auth import current_user
from api.schemas.embedding_schema import (
    BackfillRequest,
    BackfillResponse,
    EmbeddingStatsResponse,
    ModelUpgradeRequest,
    ModelUpgradeResponse,
)
from api.services.activity_log_service import write_event
from api.services.embedding import EmbeddingBackfillService

log = logging.getLogger(__name__)


async def require_platform_admin(user: User = Depends(current_user)) -> User:
    """ADR-004 P1 platform_admin 限定 endpoint 守护。

    仿 api/routers/auth.py:185 require_admin 内联 check 模式（相同模式 / M18 admin router 首发）。
    非 platform_admin → 403 permission_denied。
    """
    if user.role != "platform_admin":
        raise PermissionDeniedError()
    return user


router = APIRouter(
    prefix="/api/admin/embedding",
    tags=["embedding-admin"],
)


# ─── POST /api/admin/embedding/backfill ────────────────────────────────────


@router.post(
    "/backfill",
    response_model=BackfillResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_backfill(
    body: BackfillRequest,
    background_tasks: BackgroundTasks,
    admin=Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> BackfillResponse:
    """POST /api/admin/embedding/backfill — 手动触发 backfill（design §7 line 617）。

    权限：Depends(require_platform_admin)（ADR-004 P1 / 非 platform_admin → 403）

    activity_log（design §10 line 829）：
      write_event(action_type="embedding_backfill_triggered", target_type="project",
        target_id=project_id, metadata={trigger_reason, affected_count})
    注：write_event 异常传播测试（M16 立规 / M18 复用）：write_event raise → 500。

    元教训声明（design §14.5）：
    - viewer 写 403：require_platform_admin 守护（M07 立 / M18 admin endpoint 应用）
    - write_event 异常传播：write_event raise → 回滚 + 500（M16 立 / M18 backfill 路径）
    - R-X1 N/A：backfill 无补偿形态（M17 N/A 显式声明）
    - multipart N/A：admin endpoint 无文件上传（M11 N/A 显式声明）
    - SSE N/A：admin endpoint 同步 202（M13 N/A 显式声明）
    """
    # 占位：EmbeddingBackfillService.scan_pending 接口（子片 3 已有 detect_and_resume / 本期用占位）
    # TODO 子片 4+ 接真实 scan_pending + prevent_concurrent_backfill（EMBEDDING_BACKFILL_ALREADY_RUNNING）
    backfill_svc = EmbeddingBackfillService()

    # 防并发：占位检查（真实场景: 查 embedding_tasks WHERE enqueued_by='backfill' AND status IN ('pending','running')）
    # 当前返回 0 pending（子片 3 未接真 scan_pending）
    pending_count = 0  # placeholder — 子片 4+ 接真实 scan

    # 防并发冲突（design §14.5 + tests.md tc_M18_error_06）
    # 若 pending_count > 0: raise EmbeddingBackfillAlreadyRunningError()
    _ = backfill_svc  # suppress unused

    # affected_count 占位（scan_pending 真实接通后替换）
    affected_count = pending_count

    # ★ R14 守护：action_type 必须 _ACTION_TYPES 字面（"embedding_backfill_triggered"）
    # write_event 异常传播：若 write_event raise → 事务回滚 → 500（M16 立规 / M18 backfill 路径复用）
    await write_event(
        db=db,
        actor_user_id=admin.id,
        project_id=body.project_id,
        action_type="embedding_backfill_triggered",
        target_type="project",
        target_id=str(body.project_id),
        summary=f"手动触发 embedding backfill（project_id={body.project_id}）",
        metadata={
            "trigger_reason": "manual_admin_trigger",
            "affected_count": affected_count,
        },
    )
    await db.commit()

    # BackgroundTasks 范式（design §14.5 M16 M18 复用）：fire-and-forget 真实 enqueue
    # 子片 4+ 接真实 arq enqueue；当前占位 pass（不阻塞 202 响应）
    async def _do_backfill(
        project_id: UUID, provider: str | None, model_name: str | None, model_version: str | None
    ) -> None:
        """M16 BackgroundTasks 范式：自起 SessionLocal（不共享 HTTP request session）。"""
        async with SessionLocal() as bg_db:
            try:
                # TODO 子片 4+ 真实接 EmbeddingBackfillService.scan_pending + arq enqueue
                log.info(
                    "backfill.background.started",
                    project_id=project_id,
                    provider=provider,
                    model_name=model_name,
                    model_version=model_version,
                )
            except Exception as exc:  # noqa: BLE001
                log.error("backfill.background.failed", project_id=project_id, error=str(exc))
            finally:
                await bg_db.close()

    background_tasks.add_task(
        _do_backfill,
        body.project_id,
        body.provider,
        body.model_name,
        body.model_version,
    )

    return BackfillResponse(
        enqueued_count=0,  # 占位；子片 4+ 接 scan_pending 返真实数
        message="Backfill enqueued",
    )


# ─── POST /api/admin/embedding/model-upgrade ───────────────────────────────


@router.post(
    "/model-upgrade",
    response_model=ModelUpgradeResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_model_upgrade(
    body: ModelUpgradeRequest,
    background_tasks: BackgroundTasks,
    admin=Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> ModelUpgradeResponse:
    """POST /api/admin/embedding/model-upgrade — 触发模型升级回填（design §7 line 618）。

    权限：Depends(require_platform_admin)（ADR-004 P1 / 非 platform_admin → 403）

    activity_log（design §10 line 828）：
      write_event(action_type="embedding_model_upgrade_triggered", target_type="project",
        target_id=project_id, metadata={old_model, new_model, affected_count})
    注：metadata 字段集必须字面完整（M13 立规 / M18 复用）。

    元教训声明（design §14.5）：
    - viewer 写 403：require_platform_admin 守护（M07 立 / M18 admin endpoint 应用）
    - write_event 异常传播：write_event raise → 回滚 + 500（M16 立 / M18 model-upgrade 路径）
    - R-X1 N/A：model-upgrade 无补偿形态（M17 N/A 显式声明）
    - multipart N/A：admin endpoint 无文件上传（M11 N/A 显式声明）
    - SSE N/A：admin endpoint 同步 202（M13 N/A 显式声明）
    - M17 compensation_session helper N/A：M18 不触（显式声明）
    """
    import os

    # 获取当前 (old) model triple（从 env 读；upgrade 前的值）
    old_provider = os.getenv("EMBEDDING_PROVIDER", "mock")
    old_model_name = os.getenv("EMBEDDING_MODEL_NAME", "mock-default")
    old_model_version = os.getenv("EMBEDDING_MODEL_VERSION", "v1")

    old_triple = (old_provider, old_model_name, old_model_version)
    new_triple = (body.new_provider, body.new_model_name, body.new_model_version)

    # affected_count 占位（子片 4+ 接真实 EmbeddingDAO.count_by_project_model）
    affected_count = 0

    # ★ R14 守护：action_type 必须 _ACTION_TYPES 字面（"embedding_model_upgrade_triggered"）
    # M13 立规：metadata 字段集必须完整（old_model, new_model, affected_count）
    # write_event 异常传播：若 write_event raise → 事务回滚 → 500（M16 立规 / M18 model-upgrade 路径复用）
    await write_event(
        db=db,
        actor_user_id=admin.id,
        project_id=body.project_id,
        action_type="embedding_model_upgrade_triggered",
        target_type="project",
        target_id=str(body.project_id),
        summary=f"触发模型升级回填 {old_triple} → {new_triple}（project_id={body.project_id}）",
        metadata={
            "old_model": f"{old_provider}/{old_model_name}/{old_model_version}",
            "new_model": f"{body.new_provider}/{body.new_model_name}/{body.new_model_version}",
            "affected_count": affected_count,
        },
    )
    await db.commit()

    # BackgroundTasks 范式（design §14.5 M16 M18 复用）
    async def _do_upgrade(
        project_id: UUID,
        new_provider: str,
        new_model_name: str,
        new_model_version: str,
    ) -> None:
        """M16 BackgroundTasks 范式：自起 SessionLocal（不共享 HTTP request session）。"""
        async with SessionLocal() as bg_db:
            try:
                # TODO 子片 4+ 真实接 EmbeddingService.batch_backfill（new model triple）
                log.info(
                    "model_upgrade.background.started",
                    project_id=project_id,
                    new_provider=new_provider,
                    new_model_name=new_model_name,
                    new_model_version=new_model_version,
                )
            except Exception as exc:  # noqa: BLE001
                log.error("model_upgrade.background.failed", project_id=project_id, error=str(exc))
            finally:
                await bg_db.close()

    background_tasks.add_task(
        _do_upgrade,
        body.project_id,
        body.new_provider,
        body.new_model_name,
        body.new_model_version,
    )

    return ModelUpgradeResponse(
        enqueued_count=0,  # 占位；子片 4+ 接真实数
        old_triple=old_triple,
        new_triple=new_triple,
        message="Model upgrade enqueued",
    )


# ─── GET /api/admin/embedding/stats ────────────────────────────────────────


@router.get(
    "/stats",
    response_model=EmbeddingStatsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_embedding_stats(
    admin=Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> EmbeddingStatsResponse:
    """GET /api/admin/embedding/stats — 返 failure 率 / pending task 数 / model_version 分布（design §7 line 619）。

    权限：Depends(require_platform_admin)（ADR-004 P1 / 非 platform_admin → 403）

    元教训声明（design §14.5）：
    - viewer 写 403（read 端点）：stats 是 GET read；require_platform_admin 守护（M07 精神）
    - M14 endpoint 形态特殊不免除契约纪律：stats GET 仍受 platform_admin 守护（M14 立）
    """
    # TODO 子片 4+ 接真实 EmbeddingDAO / EmbeddingTaskDAO / EmbeddingFailureDAO 统计
    # 当前占位返 0（子片 3 已建 DAO 但本 router 子片不调真 DB）
    _ = admin  # suppress unused（admin 已在 Depends 校验）
    _ = db

    return EmbeddingStatsResponse(
        total_embeddings=0,
        pending_tasks=0,
        failed_last_hour=0,
        model_version_distribution={},
    )


__all__ = ["router"]
