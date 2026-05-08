"""M06 竞品参考 router — design/02-modules/M06-competitor/00-design.md §7 + §8.

8 endpoints：
  - Competitor 全局（项目级）4 个：GET list / POST / PUT / DELETE
  - CompetitorRef 节点级 4 个：GET list / POST / PUT / DELETE

权限（design §8 R8-1 三层）：
  - Server Action: session 校验
  - Router: check_project_access role="viewer"（读）/ "editor"（写）
  - Service: _check_node_belongs_to_project / cross-project competitor 校验
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.check_project_access import ProjectAccess, check_project_access
from api.core.db import get_db
from api.models.competitor import Competitor, CompetitorRef
from api.schemas.competitor_schema import (
    CompetitorCreate,
    CompetitorListResponse,
    CompetitorRefCreate,
    CompetitorRefListResponse,
    CompetitorRefResponse,
    CompetitorRefUpdate,
    CompetitorResponse,
    CompetitorUpdate,
)
from api.services.competitor_service import CompetitorService

# ─────────────── Competitor 全局 router ───────────────

competitor_router = APIRouter(
    prefix="/api/projects/{project_id}/competitors",
    tags=["competitors"],
)


def _competitor_response(c: Competitor) -> CompetitorResponse:
    return CompetitorResponse.model_validate(c, from_attributes=True)


def _ref_response(ref: CompetitorRef) -> CompetitorRefResponse:
    return CompetitorRefResponse.model_validate(ref, from_attributes=True)


@competitor_router.get("", response_model=CompetitorListResponse)
async def list_competitors(
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> CompetitorListResponse:
    svc = CompetitorService()
    items = await svc.list_competitors(db, project_id=access.project.id)
    return CompetitorListResponse(
        items=[_competitor_response(c) for c in items],
        total=len(items),
    )


@competitor_router.post("", response_model=CompetitorResponse, status_code=status.HTTP_201_CREATED)
async def create_competitor(
    payload: CompetitorCreate,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> CompetitorResponse:
    svc = CompetitorService()
    c = await svc.create_competitor(
        db,
        project_id=access.project.id,
        display_name=payload.display_name,
        website_url=payload.website_url,
        description=payload.description,
        actor_user_id=access.user.id,
    )
    await db.commit()
    return _competitor_response(c)


@competitor_router.put("/{competitor_id}", response_model=CompetitorResponse)
async def update_competitor(
    competitor_id: UUID,
    payload: CompetitorUpdate,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> CompetitorResponse:
    svc = CompetitorService()
    c = await svc.update_competitor(
        db,
        project_id=access.project.id,
        competitor_id=competitor_id,
        display_name=payload.display_name,
        website_url=payload.website_url,
        description=payload.description,
        actor_user_id=access.user.id,
    )
    await db.commit()
    return _competitor_response(c)


@competitor_router.delete("/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_competitor(
    competitor_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    svc = CompetitorService()
    await svc.delete_competitor(
        db,
        project_id=access.project.id,
        competitor_id=competitor_id,
        actor_user_id=access.user.id,
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─────────────── CompetitorRef 节点级 router ───────────────

competitor_ref_router = APIRouter(
    prefix="/api/projects/{project_id}/nodes/{node_id}/competitor-refs",
    tags=["competitor-refs"],
)


@competitor_ref_router.get("", response_model=CompetitorRefListResponse)
async def list_refs(
    node_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> CompetitorRefListResponse:
    svc = CompetitorService()
    items = await svc.list_refs_by_node(db, project_id=access.project.id, node_id=node_id)
    return CompetitorRefListResponse(
        items=[_ref_response(r) for r in items],
        total=len(items),
    )


@competitor_ref_router.post(
    "", response_model=CompetitorRefResponse, status_code=status.HTTP_201_CREATED
)
async def create_ref(
    node_id: UUID,
    payload: CompetitorRefCreate,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> CompetitorRefResponse:
    svc = CompetitorService()
    ref = await svc.create_ref(
        db,
        project_id=access.project.id,
        node_id=node_id,
        competitor_id=payload.competitor_id,
        actor_user_id=access.user.id,
        competitor_version=payload.competitor_version,
        feature_coverage=payload.feature_coverage,
        tech_approach=payload.tech_approach,
        pros_and_cons=(payload.pros_and_cons.model_dump() if payload.pros_and_cons else None),
    )
    await db.commit()
    return _ref_response(ref)


@competitor_ref_router.put("/{ref_id}", response_model=CompetitorRefResponse)
async def update_ref(
    node_id: UUID,
    ref_id: UUID,
    payload: CompetitorRefUpdate,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> CompetitorRefResponse:
    svc = CompetitorService()
    ref = await svc.update_ref(
        db,
        project_id=access.project.id,
        node_id=node_id,
        ref_id=ref_id,
        actor_user_id=access.user.id,
        competitor_version=payload.competitor_version,
        feature_coverage=payload.feature_coverage,
        tech_approach=payload.tech_approach,
        pros_and_cons=(payload.pros_and_cons.model_dump() if payload.pros_and_cons else None),
    )
    await db.commit()
    return _ref_response(ref)


@competitor_ref_router.delete("/{ref_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ref(
    node_id: UUID,
    ref_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    svc = CompetitorService()
    await svc.delete_ref(
        db,
        project_id=access.project.id,
        node_id=node_id,
        ref_id=ref_id,
        actor_user_id=access.user.id,
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
