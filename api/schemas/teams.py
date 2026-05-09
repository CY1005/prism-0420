"""M20 团队 Pydantic schemas — design/02-modules/M20-team/00-design.md §7.2。

R7-1 强类型 + R7-2 Pydantic Literal 枚举 + R7-3 Queue payload N/A。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TeamCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class TeamUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    version: int = Field(..., ge=1)  # 乐观锁


class TeamMemberAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: UUID
    role: Literal["admin", "member"] = "member"  # 不能直接给 owner（schema 限）


class TeamMemberRoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # 不能直接改成 owner（必须走 transfer 流程 / state machine 禁止转换 #2）
    role: Literal["admin", "member"]


class TeamTransferOwnership(BaseModel):
    model_config = ConfigDict(extra="forbid")
    new_owner_id: UUID


class ProjectMoveTeam(BaseModel):
    """POST /api/projects/{pid}/move-team 入参（M20 own 独立端点 / F2.7）。"""

    model_config = ConfigDict(extra="forbid")
    target_team_id: UUID | None  # null = 移回个人；非 null = 加入 team


class TeamRead(BaseModel):
    """G10 列表 + GET /teams/{tid} 详情主响应。"""

    id: UUID
    creator_id: UUID
    name: str
    description: str | None
    version: int
    created_at: datetime
    updated_at: datetime
    member_count: int


class TeamMemberRemoveResponse(BaseModel):
    """Q3=A 软切断响应：附残留 ProjectMember 列表（前端提醒用）。"""

    removed_user_id: UUID
    residual_project_members: list[UUID]
    residual_count: int
