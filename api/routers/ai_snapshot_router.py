"""M16 AI 快照 router — design §7 + §8 + §12B 字段③/④。

3 endpoints：
  - POST /api/projects/{project_id}/nodes/{node_id}/snapshot/generate（202 / editor 写）
  - GET  /api/snapshot-tasks/{task_id}（独立路径 / Q7 子 ack A / 双层 Service 反查 / viewer 可读）
  - POST /api/projects/{project_id}/nodes/{node_id}/snapshot/save（editor 写）

权限三层防御（design §8 R8-1 / M07 元教训"viewer 写所有写端点 403"全覆盖）：
  - Server Action：FastAPI auth 中间件（require_user）
  - Router：check_project_access(role="editor"/"viewer") for embedded path；GET 独立路径仅
    require_user，由 Service.get_task_for_user 双层校验（防同 project 同事截屏 + 被踢出后还能读旧 task）
  - Service：tenant 过滤 + path mismatch + status + selected keys

异步形态：BackgroundTasks fire-and-forget（design §12B 子模板首次实战 / 子片 0 prep §14.5
字面）。POST /generate 拿到 task 后 background_tasks.add_task(run_snapshot_task, task.id)；
事务 commit 后再排（避免 task 还没落库 runner 拉空）。
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.check_project_access import ProjectAccess, check_project_access
from api.core.db import get_db
from api.models.user import User
from api.routers.auth import current_user
from api.schemas.ai_snapshot_schema import (
    SnapshotSaveRequest,
    SnapshotSaveResponse,
    SnapshotTaskCreatedResponse,
    SnapshotTaskDetailResponse,
)
from api.services.ai_snapshot_runner import run_snapshot_task
from api.services.ai_snapshot_service import AISnapshotService

# 嵌套于 project/node 的 generate + save 端点
ai_snapshot_node_router = APIRouter(
    prefix="/api/projects/{project_id}/nodes/{node_id}/snapshot",
    tags=["ai-snapshot"],
)

# 独立路径的 GET task detail（Q7 子 ack A / 前端通用轮询组件友好）
ai_snapshot_task_router = APIRouter(
    prefix="/api/snapshot-tasks",
    tags=["ai-snapshot"],
)


@ai_snapshot_node_router.post(
    "/generate",
    response_model=SnapshotTaskCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_snapshot(
    project_id: UUID,
    node_id: UUID,
    background_tasks: BackgroundTasks,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> SnapshotTaskCreatedResponse:
    """POST /generate — 创建后台快照任务（202 Accepted / design §7 + §12B 字段③）。

    异常契约：
    - 401 未登录 / 403 viewer 写 → check_project_access
    - 404 node 不属于 project → SnapshotNodeNotFoundError
    - 422 version_count < 3 → SnapshotInsufficientVersionsError
    - 422 AI provider 未配置 → SnapshotProviderNotConfiguredError
    """
    svc = AISnapshotService()
    task, hit = await svc.create_task(
        db,
        project_id=project_id,
        node_id=node_id,
        user_id=access.user.id,
    )
    await db.commit()

    # 事务 commit 后再排 BackgroundTasks（避免 task 还没落库 runner 拉空）。
    # 幂等命中（hit=True）时不重复 dispatch（已有 runner 在跑或已完成）。
    if not hit:
        background_tasks.add_task(run_snapshot_task, task.id)

    return SnapshotTaskCreatedResponse(
        task_id=task.id,
        status=task.status,
        is_idempotent_hit=hit,
        poll_url=f"/api/snapshot-tasks/{task.id}",
        estimated_duration_seconds=90,
    )


@ai_snapshot_task_router.get(
    "/{task_id}",
    response_model=SnapshotTaskDetailResponse,
)
async def get_snapshot_task(
    task_id: UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> SnapshotTaskDetailResponse:
    """GET /snapshot-tasks/{task_id} — 独立路径 / 双层校验在 Service 层完成（design §8）。

    URL 不含 project_id 是设计选择（Q7 子 ack A / 前端通用轮询组件友好），但 Service 反查
    强制 task.user_id == current_user.id（第一层 / 防同 project 同事截屏）+ user 对
    task.project_id 仍有访问权（第二层 / 防被踢出后还能读旧 task）。所有 404 统一打码
    （不区分"不存在 / 不是 creator / project 没了"）。
    """
    svc = AISnapshotService()
    task = await svc.get_task_for_user(db, task_id=task_id, current_user_id=user.id)
    return SnapshotTaskDetailResponse.model_validate(task, from_attributes=True)


@ai_snapshot_node_router.post(
    "/save",
    response_model=SnapshotSaveResponse,
)
async def save_snapshot(
    project_id: UUID,
    node_id: UUID,
    payload: SnapshotSaveRequest,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> SnapshotSaveResponse:
    """POST /save — 用户 review 后追加 dimension_records（caller 事务 / N×M04
    create_dimension_record / M04 在内代写 activity_log）。

    异常契约：
    - 401 未登录 / 403 viewer 写 → check_project_access
    - 404 task 不存在 / 不是 creator → SnapshotTaskNotFoundError
    - 409 status != succeeded → SnapshotNotReadyError
    - 422 path mismatch（project_id/node_id 与 task 不一致，audit M5 修复）→
      SnapshotTaskPathMismatchError
    - 422 selected_dimension_keys 含 review_data 没有的 key → SnapshotInvalidDimensionKeyError
    """
    svc = AISnapshotService()
    result: dict[str, Any] = await svc.save_snapshot(
        db,
        task_id=payload.task_id,
        path_project_id=project_id,
        path_node_id=node_id,
        current_user_id=access.user.id,
        save_summary=payload.save_summary,
        selected_dimension_keys=payload.selected_dimension_keys,
    )
    await db.commit()
    return SnapshotSaveResponse(**result)
