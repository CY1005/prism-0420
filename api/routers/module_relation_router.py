"""M08 模块关系图 router — design/02-modules/M08-module-relation/00-design.md §7 + §8.

5 endpoints（M03 级联走 R-X2 lifespan register_child_service 不暴露 HTTP）:
  - GET /projects/{pid}/relations
  - GET /projects/{pid}/nodes/{nid}/relations
  - POST /projects/{pid}/relations
  - PATCH /projects/{pid}/relations/{rid}
  - DELETE /projects/{pid}/relations/{rid}
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.check_project_access import ProjectAccess, check_project_access
from api.core.db import get_db
from api.models.module_relation import ModuleRelation
from api.schemas.module_relation_schema import (
    RelationCreate,
    RelationListResponse,
    RelationResponse,
    RelationUpdate,
)
from api.services.module_relation_service import ModuleRelationService

# 项目级 router
relation_router = APIRouter(
    prefix="/api/projects/{project_id}/relations",
    tags=["module-relations"],
)

# 节点级 list router
relation_node_router = APIRouter(
    prefix="/api/projects/{project_id}/nodes/{node_id}/relations",
    tags=["module-relations"],
)


def _resp(r: ModuleRelation) -> RelationResponse:
    return RelationResponse.model_validate(r, from_attributes=True)


@relation_router.get("", response_model=RelationListResponse)
async def list_relations(
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> RelationListResponse:
    svc = ModuleRelationService()
    items = await svc.list_by_project(db, project_id=access.project.id)
    return RelationListResponse(items=[_resp(r) for r in items], total=len(items))


@relation_node_router.get("", response_model=RelationListResponse)
async def list_relations_by_node(
    node_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> RelationListResponse:
    svc = ModuleRelationService()
    items = await svc.list_by_node(db, project_id=access.project.id, node_id=node_id)
    return RelationListResponse(items=[_resp(r) for r in items], total=len(items))


@relation_router.post("", response_model=RelationResponse, status_code=status.HTTP_201_CREATED)
async def create_relation(
    payload: RelationCreate,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> RelationResponse:
    svc = ModuleRelationService()
    r = await svc.create_relation(
        db,
        project_id=access.project.id,
        source_node_id=payload.source_node_id,
        target_node_id=payload.target_node_id,
        relation_type=payload.relation_type,
        notes=payload.notes,
        actor_user_id=access.user.id,
    )
    await db.commit()
    return _resp(r)


@relation_router.patch("/{relation_id}", response_model=RelationResponse)
async def update_relation(
    relation_id: UUID,
    payload: RelationUpdate,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> RelationResponse:
    svc = ModuleRelationService()
    r = await svc.update_notes(
        db,
        project_id=access.project.id,
        relation_id=relation_id,
        notes=payload.notes,
        actor_user_id=access.user.id,
    )
    await db.commit()
    return _resp(r)


@relation_router.delete("/{relation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_relation(
    relation_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    svc = ModuleRelationService()
    await svc.delete_relation(
        db,
        project_id=access.project.id,
        relation_id=relation_id,
        actor_user_id=access.user.id,
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
