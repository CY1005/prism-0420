"""M12 功能对比矩阵 router — design §7 + §8.

6 endpoints：
  - GET   /api/projects/{pid}/comparison/matrix       (viewer)
  - GET   /api/projects/{pid}/comparison/snapshots    (viewer)
  - POST  /api/projects/{pid}/comparison/snapshots    (editor)
  - GET   /api/projects/{pid}/comparison/snapshots/{snapshot_id}  (viewer)
  - PUT   /api/projects/{pid}/comparison/snapshots/{snapshot_id}  (editor)
  - DELETE /api/projects/{pid}/comparison/snapshots/{snapshot_id} (editor)

权限（design §8 R8-1 三层）：viewer 读 matrix + snapshots / editor 写 + rename + delete；
viewer 写所有写端点 403（M07 立 / M08+M11 应用 / M12 主动复制）。

事务边界（M02-M11 范式）：router 末 await db.commit()；异常由 FastAPI 不调 commit
→ implicit rollback 全量回滚（design §5）。
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.check_project_access import ProjectAccess, check_project_access
from api.core.db import get_db
from api.models.comparison_snapshot import ComparisonSnapshot
from api.schemas.comparison_schema import (
    ComparisonMatrixResponse,
    MatrixCell,
    SnapshotCreateRequest,
    SnapshotDetailResponse,
    SnapshotListResponse,
    SnapshotResponse,
    SnapshotUpdateRequest,
)
from api.services.comparison_service import ComparisonService

comparison_router = APIRouter(
    prefix="/api/projects/{project_id}/comparison",
    tags=["comparison"],
)


def _snap_resp(snap: ComparisonSnapshot) -> SnapshotResponse:
    return SnapshotResponse.model_validate(snap, from_attributes=True)


# ─────────────── 矩阵渲染（viewer 可读） ───────────────


@comparison_router.get("/matrix", response_model=ComparisonMatrixResponse)
async def get_matrix(
    node_ids: Annotated[list[UUID], Query(min_length=1)],
    dimension_type_ids: Annotated[list[int], Query(min_length=1)],
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> ComparisonMatrixResponse:
    svc = ComparisonService()
    records = await svc.get_matrix_data(
        db,
        project_id=access.project.id,
        node_ids=node_ids,
        dimension_type_ids=dimension_type_ids,
    )
    cells = [
        MatrixCell(
            node_id=rec.node_id,
            dimension_type_id=rec.dimension_type_id,
            content=rec.content,
        )
        for rec in records
    ]
    return ComparisonMatrixResponse(cells=cells)


# ─────────────── 快照 CRUD ───────────────


@comparison_router.get("/snapshots", response_model=SnapshotListResponse)
async def list_snapshots(
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
) -> SnapshotListResponse:
    svc = ComparisonService()
    items, total = await svc.list_snapshots(db, project_id=access.project.id, limit=limit)
    return SnapshotListResponse(items=[_snap_resp(s) for s in items], total=total)


@comparison_router.get("/snapshots/{snapshot_id}", response_model=SnapshotDetailResponse)
async def get_snapshot(
    snapshot_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> SnapshotDetailResponse:
    svc = ComparisonService()
    snap = await svc.get_snapshot_detail(db, project_id=access.project.id, snapshot_id=snapshot_id)
    return SnapshotDetailResponse.model_validate(snap, from_attributes=True)


@comparison_router.post(
    "/snapshots",
    response_model=SnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_snapshot(
    payload: SnapshotCreateRequest,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> SnapshotResponse:
    svc = ComparisonService()
    snap = await svc.create_snapshot(
        db,
        project_id=access.project.id,
        actor_user_id=access.user.id,
        name=payload.name,
        description=payload.description,
        node_ids=payload.node_ids,
        dimension_type_ids=payload.dimension_type_ids,
    )
    await db.commit()
    await db.refresh(snap)
    return _snap_resp(snap)


@comparison_router.put("/snapshots/{snapshot_id}", response_model=SnapshotResponse)
async def rename_snapshot(
    snapshot_id: UUID,
    payload: SnapshotUpdateRequest,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> SnapshotResponse:
    svc = ComparisonService()
    snap = await svc.rename_snapshot(
        db,
        project_id=access.project.id,
        snapshot_id=snapshot_id,
        actor_user_id=access.user.id,
        name=payload.name,
        description=payload.description,
        expected_version=payload.expected_version,
    )
    await db.commit()
    await db.refresh(snap)
    return _snap_resp(snap)


@comparison_router.delete("/snapshots/{snapshot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_snapshot(
    snapshot_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    svc = ComparisonService()
    await svc.delete_snapshot(
        db,
        project_id=access.project.id,
        snapshot_id=snapshot_id,
        actor_user_id=access.user.id,
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
