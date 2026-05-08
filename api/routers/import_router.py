"""M17 AI 智能导入 router — design/02-modules/M17-ai-import/00-design.md §7 + §8。

7 REST endpoints + 1 WebSocket endpoint：
  - POST  /api/projects/{pid}/imports                         (multipart 提交 / editor 写)
  - GET   /api/projects/{pid}/imports                         (list / viewer 读)
  - GET   /api/projects/{pid}/imports/{task_id}               (detail / viewer 读)
  - GET   /api/projects/{pid}/imports/{task_id}/review        (review_data / viewer 读)
  - POST  /api/projects/{pid}/imports/{task_id}/confirm       (用户确认 review / editor 写)
  - POST  /api/projects/{pid}/imports/{task_id}/cancel        (取消 / editor 写)
  - POST  /api/projects/{pid}/imports/{task_id}/retry         (重试 partial_failed / editor 写)
  - WS    /api/projects/{pid}/imports/{task_id}/progress      (进度推送 + cancel 命令)

权限三层（design §8 R8-1）：
  - Server Action：require_user（FastAPI auth 中间件 / WS 走 Query Bearer 兜底）
  - Router：check_project_access(role="editor"/"viewer")
  - Service：_get_task_for_user 双层（tenant + owner）

事务边界（M11 cold_start_router 范式 / R-X1 失败补偿走 compensation_session）：
  - 成功：service 内 task 创建后立即 commit；router 调 db.commit() 落盘 items + activity_log
  - 失败：service 已通过 compensation_session 落 task=failed；router db.rollback() 丢业务事务

multipart 上传（M11 范式复用）：file.size 预检 + filename sanitize（路径穿越 / CRLF 注入防）
idempotency 命中（design §13 字面）：ImportTaskDuplicateError.http_status=200 走正常响应
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import re
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Query,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi import status as ws_status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.check_project_access import ProjectAccess, check_project_access
from api.auth.jwt_utils import decode_jwt
from api.core.db import get_db
from api.errors.exceptions import (
    ImportInvalidSourceError,
    ImportTaskDuplicateError,
    ImportTaskNotFoundError,
)
from api.models.import_task import ImportSourceType
from api.schemas.import_schema import (
    ImportSourceTypeEnum,
    ImportTaskDetailResponse,
    ImportTaskItemResponse,
    ImportTaskListResponse,
    ImportTaskResponse,
    ReviewConfirmRequest,
    ReviewDataResponse,
)
from api.services.import_service import ImportService
from api.ws.import_progress import handle_import_progress_ws

_FILENAME_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f\r\n]")
_MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100MB（zip / .git 包上限 / design §1 G6）


def _sanitize_filename(raw: str | None) -> str:
    """M11 范式复用：basename + 控制字符 strip + 长度截断。"""
    if not raw:
        return "upload.bin"
    base = os.path.basename(raw.replace("\\", "/"))
    base = _FILENAME_CONTROL_RE.sub("", base)
    base = base.strip(" .") or "upload.bin"
    return base[:255]


import_router = APIRouter(
    prefix="/api/projects/{project_id}/imports",
    tags=["import"],
)


@import_router.post(
    "",
    response_model=ImportTaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_import(
    source_type: Annotated[ImportSourceTypeEnum, Form()],
    file: Annotated[UploadFile | None, File()] = None,
    git_url: Annotated[str | None, Form()] = None,
    git_ref: Annotated[str | None, Form()] = None,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> ImportTaskResponse:
    """提交 AI 智能导入任务。

    异常契约（R2 P1-02 disambiguation 2026-05-09 / design §7 字面 413 与实装 422 漂移裁决）：
    - 401 未登录 / 403 viewer 写 → check_project_access
    - **422 文件过大 / zip 解析失败 / git URL 不可达 / 入参不合法 → ImportInvalidSourceError**
      （design §7 草案写 413，但 M17 选择统一 ImportInvalidSourceError 422 with reason=file_too_large；
       不单独立 ImportFileTooLargeError 413——与 M11 ColdStartFileTooLargeError 范式分化但
       业务语义一致：均"业务级输入参数无效"）
    - 200 idempotency 命中 → ImportTaskDuplicateError.http_status=200（design §13）

    multipart 范式：
    - source_type=zip / git_bundle：file 必填，走 file.size 预检 + filename sanitize
    - source_type=git_url：git_url 必填（git_ref 可选 / 默认 main）

    M02 ai_provider 配置：access.project.ai_provider / ai_model 直读（M16 范式延续）。
    """
    # 校验 ai_provider 配置
    project = access.project
    ai_provider = getattr(project, "ai_provider", None)
    ai_model = getattr(project, "ai_model", None)
    if not ai_provider:
        raise ImportInvalidSourceError(reason="ai_provider_unset")

    # 入参校验
    if source_type == ImportSourceTypeEnum.git_url:
        if not git_url:
            raise ImportInvalidSourceError(reason="git_url_required")
        source_uri = git_url
        source_hash_input = f"{git_url}:{git_ref or 'main'}".encode()
    else:
        if file is None:
            raise ImportInvalidSourceError(reason="file_required")
        # M11 R-X1 范式：file.size 预检（attacker 不能 chunked encoding 灌满 SpooledTemporaryFile）
        if file.size is not None and file.size > _MAX_UPLOAD_BYTES:
            raise ImportInvalidSourceError(
                reason="file_too_large",
                max_bytes=_MAX_UPLOAD_BYTES,
                actual_bytes=file.size,
            )
        raw = await file.read()
        if len(raw) > _MAX_UPLOAD_BYTES:
            raise ImportInvalidSourceError(
                reason="file_too_large",
                max_bytes=_MAX_UPLOAD_BYTES,
                actual_bytes=len(raw),
            )
        # M11 范式复用：filename sanitize（防 path traversal + CRLF 注入）
        safe_filename = _sanitize_filename(file.filename)
        # M17 sprint scaffold：实际 zip/.git 包内容 hash 落 storage_client（horizontal helper /
        # 后续 sprint 落地）；本期用文件内容 SHA256 + filename 作 source_uri 占位
        source_uri = f"upload://{safe_filename}"
        source_hash_input = raw

    source_hash = hashlib.sha256(source_hash_input).hexdigest()

    svc = ImportService()
    try:
        task = await svc.submit_import(
            db,
            user_id=access.user.id,
            project_id=access.project.id,
            source_type=ImportSourceType(source_type.value),
            source_hash=source_hash,
            source_uri=source_uri,
            ai_provider=ai_provider,
            ai_model=ai_model or "default",
        )
        await db.commit()
        return ImportTaskResponse.model_validate(task, from_attributes=True)
    except ImportTaskDuplicateError as e:
        # design §13 字面：idempotency 命中 = 200（不抛错）；router 改 200 + 复用 task。
        # 两条路径（R2 P1-04 注释）：
        # ① find_idempotent 命中：service 未做任何写，无需 rollback
        # ② IntegrityError race：service 内已 await db.rollback() + 再 select 拿 existing
        # 两条路径 caller（本 catch）都安全调 svc.get_task 走 SELECT
        existing_id = UUID(e.details["existing_task_id"])
        existing = await svc.get_task(db, task_id=existing_id, project_id=access.project.id)
        return Response(
            content=ImportTaskResponse.model_validate(
                existing, from_attributes=True
            ).model_dump_json(),
            media_type="application/json",
            status_code=200,
        )


@import_router.get("", response_model=ImportTaskListResponse)
async def list_imports(
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
) -> ImportTaskListResponse:
    svc = ImportService()
    items = await svc.list_by_project(
        db, project_id=access.project.id, user_id=access.user.id, limit=limit
    )
    resp = [ImportTaskResponse.model_validate(i, from_attributes=True) for i in items]
    return ImportTaskListResponse(items=resp, total=len(resp))


@import_router.get("/{task_id}", response_model=ImportTaskDetailResponse)
async def get_import(
    task_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> ImportTaskDetailResponse:
    svc = ImportService()
    # 双层防御：tenant + owner（design §8 第三层）
    task = await svc._get_task_for_user(  # noqa: SLF001
        db, task_id, access.project.id, access.user.id
    )
    items = await svc.item_dao.list_by_task(db, task_id=task.id)
    return ImportTaskDetailResponse.model_validate(
        {
            **{
                k: getattr(task, k)
                for k in (
                    "id",
                    "project_id",
                    "user_id",
                    "source_type",
                    "source_hash",
                    "source_uri",
                    "status",
                    "progress",
                    "error_message",
                    "ai_provider",
                    "ai_model",
                    "created_at",
                    "completed_at",
                    "expires_at",
                )
            },
            "items": [
                ImportTaskItemResponse.model_validate(i, from_attributes=True) for i in items
            ],
            "error_metadata": task.error_metadata,
        }
    )


@import_router.get("/{task_id}/review", response_model=ReviewDataResponse)
async def get_review_data(
    task_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> ReviewDataResponse:
    svc = ImportService()
    data = await svc.get_review_data(
        db, task_id=task_id, project_id=access.project.id, user_id=access.user.id
    )
    # design §7 字段名映射 + 空字段防御
    return ReviewDataResponse(
        proposed_nodes=data.get("proposed_nodes") or [],
        proposed_dimensions=data.get("proposed_dimensions") or [],
        proposed_competitors=data.get("proposed_competitors") or [],
        proposed_issues=data.get("proposed_issues") or [],
        confidence_scores=data.get("confidence_scores") or {},
    )


@import_router.post("/{task_id}/confirm", response_model=ImportTaskResponse)
async def confirm_review(
    task_id: UUID,
    body: ReviewConfirmRequest,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> ImportTaskResponse:
    """用户确认 review → ai_step3 → batch_insert。

    Router 层把 ReviewConfirmRequest 转 ConfirmedImportData（schema vs queue payload 子类
    平行 / R1-C P2-3 punt：后续可统一）。
    """
    from api.queue.import_tasks import (
        ConfirmedCompetitorData,
        ConfirmedDimensionData,
        ConfirmedImportData,
        ConfirmedIssueData,
        ConfirmedNodeData,
    )

    confirmed = ConfirmedImportData(
        nodes=[
            ConfirmedNodeData(
                proposed_id=n.proposed_id,
                name=n.name,
                type=n.type,
                parent_proposed_id=n.parent_proposed_id,
                skipped=n.skipped,
            )
            for n in body.nodes
        ],
        dimensions=[
            ConfirmedDimensionData(
                proposed_id=d.proposed_id,
                target_proposed_node_id=d.target_proposed_node_id,
                dimension_type_key=d.dimension_type_key,
                content=d.content,
            )
            for d in body.dimensions
        ],
        competitors=[
            ConfirmedCompetitorData(
                proposed_id=c.proposed_id,
                display_name=c.display_name,
                website_url=c.website_url,
                description=c.description,
            )
            for c in body.competitors
        ],
        issues=[
            ConfirmedIssueData(
                proposed_id=i.proposed_id,
                target_proposed_node_id=i.target_proposed_node_id,
                title=i.title,
                category=i.category,
                description=i.description,
            )
            for i in body.issues
        ],
        skip_proposed_ids=list(body.skip_proposed_ids),
    )
    svc = ImportService()
    task = await svc.confirm_review(
        db,
        task_id=task_id,
        project_id=access.project.id,
        user_id=access.user.id,
        confirmed=confirmed,
    )
    await db.commit()
    return ImportTaskResponse.model_validate(task, from_attributes=True)


@import_router.post(
    "/{task_id}/cancel",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cancel_import(
    task_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = ImportService()
    await svc.cancel_task(db, user_id=access.user.id, project_id=access.project.id, task_id=task_id)
    await db.commit()


@import_router.post("/{task_id}/retry", response_model=ImportTaskResponse)
async def retry_import(
    task_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> ImportTaskResponse:
    svc = ImportService()
    task = await svc.retry_task(
        db, user_id=access.user.id, project_id=access.project.id, task_id=task_id
    )
    await db.commit()
    return ImportTaskResponse.model_validate(task, from_attributes=True)


# ─────────────── WebSocket endpoint ───────────────


@import_router.websocket("/{task_id}/progress")
async def import_progress_ws(
    websocket: WebSocket,
    project_id: UUID,
    task_id: UUID,
    token: str = Query(
        ..., description="Bearer access JWT（WS 不能用 Authorization header / Query 兜底）"
    ),
) -> None:
    """WebSocket 进度推送（design §7 + §8）。

    握手鉴权（WS 不走 require_user Depends，因为 WS 端不读 Authorization header）：
    - Query token 必填 → decode_jwt → user_id
    - Service 层 check_task_access 校验 task 归属（user + project tenant 双层）
    - 任一失败 → close(1008) policy violation

    accept 后调 handle_import_progress_ws 主循环（broker subscribe + recv/send 双 task）。
    """

    from api.core.db import SessionLocal

    # 1) JWT 解码
    try:
        claims = decode_jwt(token)
    except Exception:
        await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
        return
    if claims.get("type") != "access":
        await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
        return
    sub = claims.get("sub")
    if not sub:
        await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
        return
    try:
        user_id = UUID(sub)
    except (ValueError, TypeError):
        await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
        return

    # 2) task 归属校验（service.check_task_access：tenant + owner 双层 / 任一失败 1008）
    svc = ImportService()
    try:
        async with SessionLocal() as db:
            await svc.check_task_access(db, user_id=user_id, project_id=project_id, task_id=task_id)
    except ImportTaskNotFoundError:
        await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
        return
    except Exception:
        await websocket.close(code=ws_status.WS_1011_INTERNAL_ERROR)
        return

    # 3) accept + 进入主循环
    await websocket.accept()
    with contextlib.suppress(WebSocketDisconnect):
        await handle_import_progress_ws(
            websocket,
            task_id=task_id,
            handshake_user_id=user_id,
            handshake_project_id=project_id,
        )


__all__ = ["import_router"]
