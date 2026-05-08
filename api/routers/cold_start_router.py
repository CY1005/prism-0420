"""M11 冷启动 router — design/02-modules/M11-cold-start/00-design.md §7 + §8。

4 endpoints：
  - POST /upload（multipart/form-data；editor 写）
  - GET   ""（list；viewer 读）
  - GET   /{task_id}（detail 含 error_report；viewer 读）
  - GET   /template（CSV 模板下载；viewer 读，公共）

权限（design §8 R8-1 三层）：
  - Server Action：session 校验（FastAPI auth 中间件，由 check_project_access 兜底）
  - Router：check_project_access(role="editor"/"viewer")
  - Service：tenant 过滤 + project 归属校验

事务边界：成功 commit / 失败 commit task 失败状态后 re-raise
（design §5 立修注释 / R-X1 orchestrator 完整性契约）。
"""

from __future__ import annotations

import os
import re
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.check_project_access import ProjectAccess, check_project_access
from api.core.db import get_db
from api.errors.exceptions import ColdStartFileTooLargeError
from api.schemas.cold_start_schema import (
    ColdStartTaskDetailResponse,
    ColdStartTaskListResponse,
    ColdStartTaskResponse,
)
from api.services.cold_start_service import (
    MAX_FILE_BYTES,
    ColdStartOrchestratorService,
)

_FILENAME_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f\r\n]")


def _sanitize_filename(raw: str | None) -> str:
    """R2 P1-03 立修：去 path traversal + CRLF 注入；basename + 控制字符 strip + 长度截断。"""
    if not raw:
        return "upload.csv"
    base = os.path.basename(raw.replace("\\", "/"))
    base = _FILENAME_CONTROL_RE.sub("", base)
    base = base.strip(" .") or "upload.csv"
    return base[:255]


cold_start_router = APIRouter(
    prefix="/api/projects/{project_id}/cold-start",
    tags=["cold-start"],
)


# CSV 模板（design §7 第 4 endpoint：公共资源；G6 固定列）
_CSV_TEMPLATE = (
    "node_path,node_type,competitor_name,competitor_url,"
    "issue_title,issue_category,issue_description\n"
    "/Example/A,folder,,,,,\n"
    "/Example/A/leaf,leaf,CompX,https://x.com,Bug-1,bug,description here\n"
)


@cold_start_router.get("/template", response_class=Response)
async def download_template(
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
) -> Response:
    """G6 固定模板下载（design §7）。viewer 可访问；模板内容公共。"""
    return Response(
        content=_CSV_TEMPLATE,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": ('attachment; filename="prism_cold_start_template.csv"')},
    )


@cold_start_router.post(
    "/upload",
    response_model=ColdStartTaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_cold_start_csv(
    file: UploadFile = File(...),
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> ColdStartTaskResponse:
    """触发 CSV 导入。multipart/form-data；editor 权限；同步 HTTP 路径完成。

    异常契约：
    - 401 未登录 / 403 viewer 写 → check_project_access
    - 413 文件过大 → ColdStartFileTooLargeError
    - 422 CSV 格式 / 行级校验 → ColdStartCsvInvalidError / ColdStartRowValidationFailedError
    - 500 batch 入库失败 → ColdStartBatchInsertFailedError

    事务边界（M17 sprint 子片 0 prep 重构 2026-05-09 / R2 P1-01 punt 关闭）：
    - 成功路径：service 在 task 创建后立即 commit；后续 status 扭转 + batch INSERT
      共享 request-scope db；router 调 db.commit() 把这些落盘。
    - 失败路径：service 已 await db.rollback() 丢业务写入，并通过 compensation_session
      helper 独立 connection 写 task=failed + cold_start_failed 事件并 commit；
      router 只需 db.rollback()（无需再 commit 失败状态——与 design §1 G6 + §4
      全量回滚契约一致；feedback_rx1_orchestrator_design L1）。
    """
    # R2 P1-02：file.size 预检（attacker 不能用 chunked encoding 把全部 body 灌进 SpooledTemporaryFile）
    if file.size is not None and file.size > MAX_FILE_BYTES:
        raise ColdStartFileTooLargeError(max_bytes=MAX_FILE_BYTES, actual_bytes=file.size)
    raw = await file.read()
    if len(raw) > MAX_FILE_BYTES:
        raise ColdStartFileTooLargeError(max_bytes=MAX_FILE_BYTES, actual_bytes=len(raw))

    # R2 P1-03 立修：filename sanitize（path traversal / CRLF 注入）
    safe_filename = _sanitize_filename(file.filename)
    svc = ColdStartOrchestratorService()
    try:
        task = await svc.process_csv(
            db,
            project_id=access.project.id,
            actor_user_id=access.user.id,
            content_bytes=raw,
            source_filename=safe_filename,
        )
        await db.commit()
        return ColdStartTaskResponse.model_validate(task, from_attributes=True)
    except Exception:
        # service 已通过 compensation_session 独立 connection 落盘 task=failed + 事件；
        # 这里只需 rollback 业务事务，让 typed exception 正常向 handler 传播。
        await db.rollback()
        raise


@cold_start_router.get("", response_model=ColdStartTaskListResponse)
async def list_cold_start_tasks(
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
) -> ColdStartTaskListResponse:
    svc = ColdStartOrchestratorService()
    items = await svc.list_by_project(
        db, project_id=access.project.id, user_id=access.user.id, limit=limit
    )
    resp_items = [ColdStartTaskResponse.model_validate(i, from_attributes=True) for i in items]
    return ColdStartTaskListResponse(items=resp_items, total=len(resp_items))


@cold_start_router.get("/{task_id}", response_model=ColdStartTaskDetailResponse)
async def get_cold_start_task(
    task_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> ColdStartTaskDetailResponse:
    svc = ColdStartOrchestratorService()
    t = await svc.get_by_id(db, project_id=access.project.id, task_id=task_id)
    return ColdStartTaskDetailResponse.model_validate(t, from_attributes=True)
