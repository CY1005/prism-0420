"""M18 搜索 router — design §6 line 575 / §7 line 616 / §8 line 674。

1 endpoint：
  - POST /api/projects/{project_id}/search  (viewer 读 / 同步 ≤3s)

权限三层（design §8）：
  - L2 Router：Depends(require_user) Bearer JWT
  - L2.5 Router：check_project_access(role="viewer") 粗粒度 project 访问
  - L3 Service：SearchService.check_project_access — 细粒度 cross-project 拒绝

错误契约（design §7 line 662-664）：
  - 400 INVALID_QUERY_LENGTH：query 超 200 char（Pydantic min_length/max_length 已拦）
  - 403 PROJECT_FORBIDDEN：非 project member viewer → check_project_access 返 404/403
  - 504 SEARCH_TIMEOUT：全路径超时（asyncio.timeout 覆盖）

pgvector 降级（PRD AC4）：
  - pgvector 不可用 → search_mode="keyword_only" + 200（不报错）
  - SearchService 内部处理 NotImplementedError 降级

R13-2 豁免：search 上游 ErrorCode 透传（audit M2 / 不 wrap SearchUpstreamError）

元教训（design §14.5）：
  - M18 search 无 multipart → file.size / sanitize N/A（显式）
  - M18 search 无 SSE 形态 → N/A（显式）
  - M18 search read-only → viewer 写 403 N/A（search 是 POST read）
  - R-X1 失败补偿：search 无写操作 / N/A（显式）
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.check_project_access import ProjectAccess, check_project_access
from api.core.db import get_db
from api.errors.exceptions import InvalidQueryLengthError
from api.schemas.search_schema import SearchRequest, SearchResponse
from api.services.search import SearchService

router = APIRouter(
    prefix="/api/projects/{project_id}/search",
    tags=["search"],
)


@router.post(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
)
async def search_project(
    project_id: UUID,
    body: SearchRequest,
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """POST /api/projects/{project_id}/search — 混合搜索（design §7 line 616）。

    权限：
    - L2 Router：check_project_access(role="viewer") Bearer JWT → 非 member 404
    - L3 Service：check_project_access → cross-project 403 PROJECT_FORBIDDEN

    错误：
    - 400 invalid_query_length：query 空 / 超 200 char（Pydantic 拦）
    - 403 permission_denied：project 非 member（check_project_access 抛 ProjectNotFoundError 404
      or PermissionDeniedError 403）
    - 504 search_timeout：全路径超时

    pgvector 不可用 → search_mode="keyword_only" + 200（PRD AC4 / 不报错）

    N/A 元教训声明（design §14.5）：
    - multipart/file.size/sanitize：search 无文件上传（M11 N/A）
    - SSE 形态：search 同步路由（M13 N/A）
    - R-X1 失败补偿：search read-only 无写操作（M11/M17 N/A）
    - viewer 写 403：search 是 read endpoint（POST 语义是 query / 非写操作，M07 N/A）
    """
    # design §7 line 663：query / limit 全部边界 → 400 INVALID_QUERY_LENGTH
    # （B-P2-M18-search-query-validation-returns-422 fix：原 Pydantic min_length/ge/le 走 422
    # 与 service 层 >200 走 400 不一致；schema 已删除约束，router 单点拦截全部边界）
    if len(body.query) < 1 or len(body.query) > 200:
        raise InvalidQueryLengthError(
            reason="query_length_out_of_range", query_length=len(body.query)
        )
    if body.limit < 1 or body.limit > 100:
        raise InvalidQueryLengthError(reason="limit_out_of_range", limit=body.limit)

    svc = SearchService()

    # L3 Service 层二次防御（cross-project 拒绝）
    await svc.check_project_access(db, user_id=access.user.id, project_id=project_id)

    return await svc.hybrid_search(
        db,
        query=body.query,
        project_id=project_id,
        user_id=access.user.id,
        target_types=body.target_types,
        limit=body.limit,
    )


__all__ = ["router"]
