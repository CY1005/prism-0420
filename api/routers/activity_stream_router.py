"""M15 activity stream router — design §6 + §7 + §8。

GET /api/projects/{project_id}/activity-stream — 项目操作日志列表（分页 + 多维过滤）。

权限三层（design §8 R8-1）：
- Server Action：session 校验（FastAPI auth 中间件）
- Router：check_project_access(role="editor")（rank 系统：rank["editor"]=2 自动允许
  owner+editor 通过 / viewer rank=1 < 2 → PermissionDeniedError 403 / 等价 design §8
  C-5 候选 β "owner + editor 可审计"）
- Service：_check_activity_audit_access 二次校验（design §8 双重防御）

R-X3 横切表豁免（ADR-003 规则 3 / design §3）：M15 直查 activity_logs + JOIN users，
不调任何业务模块 service。

注：list_for_team helper DAO 已实装 / Router endpoint M20 sprint own（design §3 line 405
M20 baseline-patch F2.5）。本 sprint Router 仅暴露 list_stream 1 endpoint（design §7
endpoint 表字面）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.check_project_access import ProjectAccess, check_project_access
from api.core.db import get_db
from api.schemas.activity_stream_schema import (
    ActivityStreamFilter,
    ActivityStreamResponse,
)
from api.services.activity_stream_service import ActivityStreamService

activity_stream_router = APIRouter(
    prefix="/api/projects/{project_id}/activity-stream",
    tags=["activity-stream"],
)


@activity_stream_router.get("", response_model=ActivityStreamResponse)
async def get_activity_stream(
    filt: ActivityStreamFilter = Depends(),
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> ActivityStreamResponse:
    """项目操作日志列表（design §7 GET / C-5 owner+editor 可审计）。

    异常契约：
    - 401 未登录 → 由 auth 中间件统一处理
    - 403 viewer 读 → check_project_access PermissionDeniedError（design §8 三层第二层）
    - 404 non-member / project 不存在 → check_project_access ProjectNotFoundError
      （不泄露 project 存在性 / design §8 C-5 候选 β）
    - 422 from_dt > to_dt → ActivityStreamInvalidFilterError（schema model_validator）
    """
    svc = ActivityStreamService()
    return await svc.list_stream(
        db,
        actor_user_id=access.user.id,
        project_id=access.project.id,
        filt=filt,
    )
