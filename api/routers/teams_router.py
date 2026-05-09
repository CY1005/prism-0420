"""M20 团队 router — design §7 + §8 (10 endpoints)。

10 endpoints:
  POST   /api/teams                                      创建 team (require_user)
  GET    /api/teams                                      列出 U 所在 team (require_user)
  GET    /api/teams/{tid}                                team 详情 (L1 require_team_access member)
  PATCH  /api/teams/{tid}                                改 name/description (L2 admin)
  DELETE /api/teams/{tid}                                删 team (L2 owner)
  POST   /api/teams/{tid}/members                        加成员 (L2 admin)
  PATCH  /api/teams/{tid}/members/{uid}                  改 role (L2 admin)
  DELETE /api/teams/{tid}/members/{uid}                  软切断移除 (L2 admin)
  POST   /api/teams/{tid}/transfer-ownership             转让 owner (L2 owner)
  POST   /api/projects/{pid}/move-team                   project 归属变更 (M20 own 独立)

权限三层（design §8.1 R8-1）：
  L1 require_user 解析 JWT；L2 assert_team_role 在 Service 内精校验（防 leak 404 / role 403）。
  team 不属于 project tenant，未走 check_project_access 路径；project 归属 endpoint 走
  Service 内 ProjectMember owner 校验。

事务边界（M02-M19 范式）：router 末 await db.commit()；异常由 FastAPI 不调 commit →
implicit rollback 全量回滚（design §8.7 R-X3 共享外部 session）。
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.db import get_db
from api.routers.auth import current_user
from api.schemas.teams import (
    ProjectMoveTeam,
    TeamCreate,
    TeamMemberAdd,
    TeamMemberRemoveResponse,
    TeamMemberRoleUpdate,
    TeamRead,
    TeamTransferOwnership,
    TeamUpdate,
)
from api.services.team_service import TeamService

teams_router = APIRouter(prefix="/api/teams", tags=["teams"])
project_team_router = APIRouter(prefix="/api/projects", tags=["teams"])


def _team_read(team, member_count: int) -> TeamRead:
    return TeamRead(
        id=team.id,
        creator_id=team.creator_id,
        name=team.name,
        description=team.description,
        version=team.version,
        created_at=team.created_at,
        updated_at=team.updated_at,
        member_count=member_count,
    )


# ─────────────── G1 / B11 创建 ───────────────


@teams_router.post("", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
async def create_team(
    payload: TeamCreate,
    user: Annotated[Any, Depends(current_user)],
    db: AsyncSession = Depends(get_db),
) -> TeamRead:
    svc = TeamService()
    team = await svc.create_team(db, user.id, payload.name, payload.description)
    await db.commit()
    await db.refresh(team)
    return _team_read(team, member_count=1)


# ─────────────── G10 列表 ───────────────


@teams_router.get("", response_model=list[TeamRead])
async def list_teams(
    user: Annotated[Any, Depends(current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[TeamRead]:
    svc = TeamService()
    rows = await svc.list_for_user(db, user.id)
    return [_team_read(t, c) for t, c in rows]


# ─────────────── T1 / GET 详情 ───────────────


@teams_router.get("/{team_id}", response_model=TeamRead)
async def get_team(
    team_id: UUID,
    user: Annotated[Any, Depends(current_user)],
    db: AsyncSession = Depends(get_db),
) -> TeamRead:
    svc = TeamService()
    team = await svc.get_team(db, team_id, user.id)
    count = await svc.team_dao.get_member_count(db, team.id)
    return _team_read(team, count)


# ─────────────── G5 PATCH ───────────────


@teams_router.patch("/{team_id}", response_model=TeamRead)
async def update_team(
    team_id: UUID,
    payload: TeamUpdate,
    user: Annotated[Any, Depends(current_user)],
    db: AsyncSession = Depends(get_db),
) -> TeamRead:
    svc = TeamService()
    team = await svc.update_team(
        db, user.id, team_id, payload.version, payload.name, payload.description
    )
    await db.commit()
    await db.refresh(team)
    count = await svc.team_dao.get_member_count(db, team.id)
    return _team_read(team, count)


# ─────────────── G8 DELETE ───────────────


@teams_router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: UUID,
    user: Annotated[Any, Depends(current_user)],
    db: AsyncSession = Depends(get_db),
) -> Response:
    svc = TeamService()
    await svc.delete_team(db, user.id, team_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─────────────── G2 加成员 ───────────────


@teams_router.post(
    "/{team_id}/members",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    team_id: UUID,
    payload: TeamMemberAdd,
    user: Annotated[Any, Depends(current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    from api.models.teams import TeamRole as _TeamRole

    svc = TeamService()
    member = await svc.add_member(db, user.id, team_id, payload.user_id, _TeamRole(payload.role))
    await db.commit()
    return {
        "id": str(member.id),
        "team_id": str(member.team_id),
        "user_id": str(member.user_id),
        "role": member.role,
    }


# ─────────────── G3 PATCH role ───────────────


@teams_router.patch("/{team_id}/members/{user_id}", response_model=dict)
async def update_member_role(
    team_id: UUID,
    user_id: UUID,
    payload: TeamMemberRoleUpdate,
    user: Annotated[Any, Depends(current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """R2-P1-3 立修：加 response_model=dict 与其他 endpoint 范式一致。"""
    from api.models.teams import TeamRole as _TeamRole

    svc = TeamService()
    member = await svc.update_member_role(db, user.id, team_id, user_id, _TeamRole(payload.role))
    await db.commit()
    return {"user_id": str(member.user_id), "role": member.role}


# ─────────────── G9 软切断 DELETE ───────────────


@teams_router.delete("/{team_id}/members/{user_id}", response_model=TeamMemberRemoveResponse)
async def remove_member(
    team_id: UUID,
    user_id: UUID,
    user: Annotated[Any, Depends(current_user)],
    db: AsyncSession = Depends(get_db),
) -> TeamMemberRemoveResponse:
    svc = TeamService()
    result = await svc.remove_member(db, user.id, team_id, user_id)
    await db.commit()
    return TeamMemberRemoveResponse(
        removed_user_id=result["removed_user_id"],
        residual_project_members=result["residual_project_members"],
        residual_count=result["residual_count"],
    )


# ─────────────── G4 transfer-ownership ───────────────


@teams_router.post("/{team_id}/transfer-ownership", status_code=status.HTTP_204_NO_CONTENT)
async def transfer_ownership(
    team_id: UUID,
    payload: TeamTransferOwnership,
    user: Annotated[Any, Depends(current_user)],
    db: AsyncSession = Depends(get_db),
) -> Response:
    svc = TeamService()
    await svc.transfer_ownership(db, user.id, team_id, payload.new_owner_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─────────────── G6/G7 move-team (M20 own 独立端点) ───────────────


@project_team_router.post("/{project_id}/move-team", status_code=status.HTTP_200_OK)
async def move_project_team(
    project_id: UUID,
    payload: ProjectMoveTeam,
    user: Annotated[Any, Depends(current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    svc = TeamService()
    proj = await svc.move_project_team(db, user.id, project_id, payload.target_team_id)
    await db.commit()
    return {"project_id": str(proj.id), "team_id": str(proj.team_id) if proj.team_id else None}
