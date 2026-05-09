"""M04 维度记录 router — design/02-modules/M04-feature-archive/00-design.md §7 + §8.

6 endpoints (design §7):
    GET    /api/projects/{pid}/nodes/{nid}/dimensions                list_by_node + enabled types
    GET    /api/projects/{pid}/nodes/{nid}/dimensions/{type_id}      get_one
    POST   /api/projects/{pid}/nodes/{nid}/dimensions                create (201)
    PUT    /api/projects/{pid}/nodes/{nid}/dimensions/{type_id}      update_with_lock
    DELETE /api/projects/{pid}/nodes/{nid}/dimensions/{type_id}      delete (204)
    GET    /api/projects/{pid}/nodes/{nid}/completion                completion (filled/enabled)

权限 (design §8 R8-1 三层):
    - Server Action: session 校验
    - Router: check_project_access role="viewer" (read) / "editor" (write)
    - Service: _check_node_belongs_to_project + _check_dimension_type_enabled
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.check_project_access import ProjectAccess, check_project_access
from api.core.db import get_db
from api.models.dimension_record import DimensionRecord
from api.models.project import DimensionType, ProjectDimensionConfig
from api.schemas.dimension_schema import (
    CompletionResponse,
    DimensionCreate,
    DimensionListResponse,
    DimensionResponse,
    DimensionTypeRef,
    DimensionUpdate,
)
from api.services.dimension_service import DimensionService

router = APIRouter(
    prefix="/api/projects/{project_id}/nodes/{node_id}/dimensions",
    tags=["dimensions"],
)
completion_router = APIRouter(
    prefix="/api/projects/{project_id}/nodes/{node_id}",
    tags=["dimensions"],
)


def _record_response(rec: DimensionRecord) -> DimensionResponse:
    # Phase 2.2 子片 5 D 类 #15：装配 join 字段（DAO read paths 已 selectinload；model
    # lazy="raise" 保证 caller 漏 eager load 时直接抛 / 不做静默 None 兜底）
    return DimensionResponse(
        id=rec.id,
        node_id=rec.node_id,
        project_id=rec.project_id,
        dimension_type_id=rec.dimension_type_id,
        content=rec.content,
        version=rec.version,
        created_by=rec.created_by,
        updated_by=rec.updated_by,
        created_at=rec.created_at,
        updated_at=rec.updated_at,
        dimension_type_key=(rec.dimension_type.key if rec.dimension_type is not None else None),
        updated_by_name=(rec.updated_by_user.name if rec.updated_by_user is not None else None),
    )


async def _list_enabled_types(db: AsyncSession, project_id: UUID) -> list[DimensionTypeRef]:
    """档案页装配：拉取项目启用的维度类型 + 排序。

    R2 立修 B6.x：strict 仅返回 ``enabled=True`` 的行（与 design §7 出参
    "项目启用的维度（含未填的）" 字面一致 + 字段名 enabled_dimension_types 语义自洽）。
    禁用配置由 M02 项目维度配置 endpoint own，不通过本 endpoint 暴露。
    """
    stmt = (
        select(ProjectDimensionConfig, DimensionType)
        .join(DimensionType, DimensionType.id == ProjectDimensionConfig.dimension_type_id)
        .where(
            ProjectDimensionConfig.project_id == project_id,
            ProjectDimensionConfig.enabled.is_(True),
        )
        .order_by(ProjectDimensionConfig.sort_order.asc(), DimensionType.id.asc())
    )
    rows = (await db.execute(stmt)).all()
    return [
        DimensionTypeRef(
            id=dt.id,
            key=dt.key,
            name=dt.name,
            icon=dt.icon,
            sort_order=pdc.sort_order,
            enabled=pdc.enabled,
        )
        for pdc, dt in rows
    ]


# ─── Read ──────────────────────────────────────────────


@router.get("", response_model=DimensionListResponse)
async def list_by_node(
    node_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> DimensionListResponse:
    """档案页主查询：已有维度记录 + 项目启用类型清单。"""
    svc = DimensionService()
    # service 内部不校验 node 归属（只读不写也是个 P3 — 但越权读返回空 list 也安全）
    items = await svc.list_by_node(db, project_id=access.project.id, node_id=node_id)
    types = await _list_enabled_types(db, access.project.id)
    return DimensionListResponse(
        items=[_record_response(r) for r in items],
        enabled_dimension_types=types,
    )


@router.get("/{dimension_type_id}", response_model=DimensionResponse)
async def get_one(
    node_id: UUID,
    dimension_type_id: int,
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> DimensionResponse:
    svc = DimensionService()
    rec = await svc.get_one_record(
        db,
        project_id=access.project.id,
        node_id=node_id,
        dimension_type_id=dimension_type_id,
    )
    return _record_response(rec)


@completion_router.get("/completion", response_model=CompletionResponse)
async def completion(
    node_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> CompletionResponse:
    """完善度：filled / enabled rate。

    R2 P2 punt B2/B4 修：用 SELECT COUNT(*) 单查替代 JOIN+全字段拉取（B6.x 立修后
    _list_enabled_types 已 enabled 过滤；但 completion 仅需 count，免装配 Pydantic）。
    """
    from sqlalchemy import func

    count_result = await db.execute(
        select(func.count(ProjectDimensionConfig.id)).where(
            ProjectDimensionConfig.project_id == access.project.id,
            ProjectDimensionConfig.enabled.is_(True),
        )
    )
    enabled_count = int(count_result.scalar_one() or 0)
    svc = DimensionService()
    result = await svc.completion(
        db,
        project_id=access.project.id,
        node_id=node_id,
        enabled_count=enabled_count,
    )
    return CompletionResponse(**result)


# ─── Write ─────────────────────────────────────────────


@router.post("", response_model=DimensionResponse, status_code=status.HTTP_201_CREATED)
async def create_dimension(
    node_id: UUID,
    payload: DimensionCreate,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> DimensionResponse:
    svc = DimensionService()
    rec = await svc.create(
        db,
        project_id=access.project.id,
        node_id=node_id,
        dimension_type_id=payload.dimension_type_id,
        content=payload.content,
        actor_user_id=access.user.id,
    )
    await db.commit()
    return _record_response(rec)


@router.put("/{dimension_type_id}", response_model=DimensionResponse)
async def update_dimension(
    node_id: UUID,
    dimension_type_id: int,
    payload: DimensionUpdate,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> DimensionResponse:
    svc = DimensionService()
    rec = await svc.update_with_lock(
        db,
        project_id=access.project.id,
        node_id=node_id,
        dimension_type_id=dimension_type_id,
        content=payload.content,
        expected_version=payload.expected_version,
        actor_user_id=access.user.id,
    )
    await db.commit()
    return _record_response(rec)


@router.delete("/{dimension_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dimension(
    node_id: UUID,
    dimension_type_id: int,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    svc = DimensionService()
    await svc.delete(
        db,
        project_id=access.project.id,
        node_id=node_id,
        dimension_type_id=dimension_type_id,
        actor_user_id=access.user.id,
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
