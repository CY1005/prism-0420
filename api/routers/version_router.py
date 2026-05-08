"""M05 版本时间线 router — design/02-modules/M05-version-timeline/00-design.md §7 + §8.

6 endpoints (design §7):
    GET    /api/projects/{pid}/nodes/{nid}/versions                list_by_node
    GET    /api/projects/{pid}/nodes/{nid}/versions/{vid}          get_one
    POST   /api/projects/{pid}/nodes/{nid}/versions                create (201)
    PUT    /api/projects/{pid}/nodes/{nid}/versions/{vid}          update_metadata
    DELETE /api/projects/{pid}/nodes/{nid}/versions/{vid}          delete (204)
    POST   /api/projects/{pid}/nodes/{nid}/versions/{vid}/set-current   set_current

权限 (design §8 R8-1 三层):
    - Server Action: session 校验
    - Router: check_project_access role="viewer"（读）/ "editor"（写）
    - Service: _check_node_belongs_to_project（防 cross-tenant node_id）
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.check_project_access import ProjectAccess, check_project_access
from api.core.db import get_db
from api.models.version_record import VersionRecord
from api.schemas.version_schema import (
    VersionCreate,
    VersionListResponse,
    VersionResponse,
    VersionUpdate,
)
from api.services.version_service import VersionService

router = APIRouter(
    prefix="/api/projects/{project_id}/nodes/{node_id}/versions",
    tags=["versions"],
)


def _record_response(rec: VersionRecord) -> VersionResponse:
    return VersionResponse.model_validate(rec, from_attributes=True)


# ─── Read ──────────────────────────────────────────────


@router.get("", response_model=VersionListResponse)
async def list_versions(
    node_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> VersionListResponse:
    """节点版本时间线（按 created_at DESC）。"""
    svc = VersionService()
    items = await svc.list_by_node(db, project_id=access.project.id, node_id=node_id)
    total = await svc.count_by_node(db, project_id=access.project.id, node_id=node_id)
    return VersionListResponse(
        items=[_record_response(r) for r in items],
        total=total,
    )


@router.get("/{version_id}", response_model=VersionResponse)
async def get_version(
    node_id: UUID,
    version_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> VersionResponse:
    svc = VersionService()
    rec = await svc.get_by_id(
        db,
        project_id=access.project.id,
        node_id=node_id,
        version_id=version_id,
    )
    return _record_response(rec)


# ─── Write ─────────────────────────────────────────────


@router.post("", response_model=VersionResponse, status_code=status.HTTP_201_CREATED)
async def create_version(
    node_id: UUID,
    payload: VersionCreate,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> VersionResponse:
    svc = VersionService()
    rec = await svc.create(
        db,
        project_id=access.project.id,
        node_id=node_id,
        version_label=payload.version_label,
        summary=payload.summary,
        details=payload.details,
        change_type=payload.change_type,
        release_mode=payload.release_mode,
        is_current=payload.is_current,
        snapshot_data=payload.snapshot_data,
        actor_user_id=access.user.id,
    )
    await db.commit()
    return _record_response(rec)


@router.put("/{version_id}", response_model=VersionResponse)
async def update_version(
    node_id: UUID,
    version_id: UUID,
    payload: VersionUpdate,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> VersionResponse:
    svc = VersionService()
    rec = await svc.update_metadata(
        db,
        project_id=access.project.id,
        node_id=node_id,
        version_id=version_id,
        summary=payload.summary,
        details=payload.details,
        change_type=payload.change_type,
        release_mode=payload.release_mode,
        actor_user_id=access.user.id,
    )
    await db.commit()
    return _record_response(rec)


@router.delete("/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_version(
    node_id: UUID,
    version_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    svc = VersionService()
    await svc.delete(
        db,
        project_id=access.project.id,
        node_id=node_id,
        version_id=version_id,
        actor_user_id=access.user.id,
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{version_id}/set-current", response_model=VersionResponse)
async def set_current_version(
    node_id: UUID,
    version_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> VersionResponse:
    svc = VersionService()
    rec = await svc.set_current(
        db,
        project_id=access.project.id,
        node_id=node_id,
        version_id=version_id,
        actor_user_id=access.user.id,
    )
    await db.commit()
    return _record_response(rec)
