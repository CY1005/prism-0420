"""M10 项目全景图 router — design/02-modules/M10-overview/00-design.md §7 + §8.

2 endpoints（全 GET / viewer-only / 无写端点）:
  - GET /api/projects/{pid}/overview          (full tree + stats)
  - GET /api/projects/{pid}/overview/stats    (lightweight stats)

design §7 列了 GET /nodes/{nid}/completion 但实装走 M04 dimension_router 的
/completion endpoint（M04 已注册 / 路径冲突避免双注册 / 子片 5 audit 回写
disambiguation 注释）。M10 service.get_node_completion 保留作 folder 均值算法
单节点访问的内部接口，未来如有需要可由 M04 router 改委托过来。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.check_project_access import ProjectAccess, check_project_access
from api.core.db import get_db
from api.schemas.overview_schema import OverviewResponse, OverviewStatsResponse
from api.services.overview_service import OverviewService

overview_router = APIRouter(
    prefix="/api/projects/{project_id}/overview",
    tags=["overview"],
)


@overview_router.get("", response_model=OverviewResponse)
async def get_overview(
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> OverviewResponse:
    svc = OverviewService()
    data = await svc.get_overview(db, project_id=access.project.id)
    return OverviewResponse(**data)


@overview_router.get("/stats", response_model=OverviewStatsResponse)
async def get_overview_stats(
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> OverviewStatsResponse:
    svc = OverviewService()
    data = await svc.get_stats(db, project_id=access.project.id)
    return OverviewStatsResponse(**data)
