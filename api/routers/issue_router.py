"""M07 问题沉淀 router — design/02-modules/M07-issue/00-design.md §7 + §8.

7 endpoints：
  - 项目级 list / get / create / update / transition / delete (6)
  - 节点级 list (1)

权限（design §8 R8-1 三层）：viewer 读 / editor 写 + transition；
Service _check_node_belongs_to_project + 状态机校验
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.check_project_access import ProjectAccess, check_project_access
from api.core.db import get_db
from api.models.issue import Issue
from api.schemas.issue_schema import (
    IssueCreate,
    IssueListResponse,
    IssueResponse,
    IssueTransition,
    IssueUpdate,
)
from api.services.issue_service import IssueService

# ─────────────── 项目级 router ───────────────

issue_router = APIRouter(
    prefix="/api/projects/{project_id}/issues",
    tags=["issues"],
)


def _resp(i: Issue) -> IssueResponse:
    return IssueResponse.model_validate(i, from_attributes=True)


@issue_router.get("", response_model=IssueListResponse)
async def list_issues(
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
    category: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    node_id: UUID | None = Query(None),
    tag: str | None = Query(None),
    limit: int | None = Query(None, ge=1, le=200),
) -> IssueListResponse:
    svc = IssueService()
    items = await svc.list_by_project(
        db,
        project_id=access.project.id,
        category=category,
        status=status_filter,
        node_id=node_id,
        tag=tag,
        limit=limit,
    )
    return IssueListResponse(items=[_resp(i) for i in items], total=len(items))


@issue_router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(
    issue_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> IssueResponse:
    svc = IssueService()
    i = await svc.get_by_id(db, project_id=access.project.id, issue_id=issue_id)
    return _resp(i)


@issue_router.post("", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
async def create_issue(
    payload: IssueCreate,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> IssueResponse:
    svc = IssueService()
    i = await svc.create(
        db,
        project_id=access.project.id,
        category=payload.category,
        title=payload.title,
        description=payload.description,
        node_id=payload.node_id,
        tags=payload.tags,
        assigned_to=payload.assigned_to,
        actor_user_id=access.user.id,
    )
    await db.commit()
    return _resp(i)


@issue_router.put("/{issue_id}", response_model=IssueResponse)
async def update_issue(
    issue_id: UUID,
    payload: IssueUpdate,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> IssueResponse:
    svc = IssueService()
    i = await svc.update(
        db,
        project_id=access.project.id,
        issue_id=issue_id,
        title=payload.title,
        description=payload.description,
        tags=payload.tags,
        node_id=payload.node_id,
        assigned_to=payload.assigned_to,
        actor_user_id=access.user.id,
    )
    await db.commit()
    return _resp(i)


@issue_router.post("/{issue_id}/transition", response_model=IssueResponse)
async def transition_issue(
    issue_id: UUID,
    payload: IssueTransition,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> IssueResponse:
    svc = IssueService()
    i = await svc.transition(
        db,
        project_id=access.project.id,
        issue_id=issue_id,
        target_status=payload.target_status,
        assigned_to=payload.assigned_to,
        note=payload.note,
        actor_user_id=access.user.id,
    )
    await db.commit()
    return _resp(i)


@issue_router.delete("/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_issue(
    issue_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    svc = IssueService()
    await svc.delete(
        db,
        project_id=access.project.id,
        issue_id=issue_id,
        actor_user_id=access.user.id,
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─────────────── 节点级 list router ───────────────

issue_node_router = APIRouter(
    prefix="/api/projects/{project_id}/nodes/{node_id}/issues",
    tags=["issues"],
)


@issue_node_router.get("", response_model=IssueListResponse)
async def list_issues_by_node(
    node_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
    category: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    tag: str | None = Query(None),
    limit: int | None = Query(None, ge=1, le=200),
) -> IssueListResponse:
    svc = IssueService()
    items = await svc.list_by_project(
        db,
        project_id=access.project.id,
        node_id=node_id,
        category=category,
        status=status_filter,
        tag=tag,
        limit=limit,
    )
    return IssueListResponse(items=[_resp(i) for i in items], total=len(items))
