"""M02 项目 + 成员 + 维度配置 router (design §7 + §8 权限三层).

11 endpoints (design §7 表):
    GET    /api/projects                      list_projects
    POST   /api/projects                      create_project
    GET    /api/projects/{pid}                get_project
    PUT    /api/projects/{pid}                update_project
    POST   /api/projects/{pid}/archive        archive_project
    GET    /api/projects/{pid}/members        list_members
    POST   /api/projects/{pid}/members        invite_member
    PUT    /api/projects/{pid}/members/{uid}  update_member_role
    DELETE /api/projects/{pid}/members/{uid}  remove_member
    GET    /api/projects/{pid}/dimension-configs   list_dimension_configs
    PUT    /api/projects/{pid}/dimension-configs   batch_update_dimension_configs (R10-1 写独立事件)

# Scaffold 简化决策 (2026-05-07, 子片 4)
# ① 决策内容: M02 sprint 期 POST /api/projects/{pid}/move-team endpoint 不实装
# ② 简化理由: 依赖 teams 表 (M20 own), B 路径 caller 主动写 teams 不可行;
#              R-X5 子选项实证决: 不实装 router → OpenAPI 不含 (避免占位 501 误导前端 codegen)
# ③ 由 M20 sprint 扩齐: POST /api/projects/{pid}/move-team
#    含 require_user + check_project_access(role=owner) + ProjectArchivedError raise
# ④ 触发回写动作: M20 sprint add 路由实装 + raise ProjectArchivedError caller +
#    回写 M02 design §7 endpoint 表对应行 + design §3.X A3.2 status=已落地
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.check_project_access import ProjectAccess, check_project_access
from api.core.db import get_db
from api.errors.exceptions import DimensionConfigInvalidError
from api.models.user import User
from api.routers.auth import current_user
from api.schemas.project_schema import (
    AiProviderUpdate,
    DimensionConfigBatchUpdate,
    DimensionConfigListResponse,
    DimensionConfigResponse,
    MemberInvite,
    MemberListResponse,
    MemberResponse,
    MemberRoleUpdate,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from api.services.activity_log_service import write_event
from api.services.project_service import MemberService, ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _project_response(proj) -> ProjectResponse:
    return ProjectResponse.model_validate(proj, from_attributes=True)


def _member_response(m) -> MemberResponse:
    return MemberResponse.model_validate(m, from_attributes=True)


# ─── Project CRUD ────────────────────────────────────


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    include_archived: bool = False,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectListResponse:
    svc = ProjectService()
    rows = await svc.list_for_user(db, user.id, include_archived=include_archived)
    items = [_project_response(p) for p in rows]
    return ProjectListResponse(items=items, total=len(items))


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    svc = ProjectService()
    proj = await svc.create_project(
        db,
        owner_id=user.id,
        name=payload.name,
        description=payload.description,
        template_type=payload.template_type,
        hierarchy_labels=payload.hierarchy_labels,
    )
    await db.commit()
    return _project_response(proj)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
) -> ProjectResponse:
    return _project_response(access.project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    payload: ProjectUpdate,
    access: ProjectAccess = Depends(check_project_access(role="owner")),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    svc = ProjectService()
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    proj = await svc.update_project(
        db,
        project_id=access.project.id,
        actor_user_id=access.user.id,
        changes=changes,
    )
    await db.commit()
    return _project_response(proj)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    access: ProjectAccess = Depends(check_project_access(role="owner")),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    svc = ProjectService()
    proj = await svc.archive_project(db, project_id=access.project.id, actor_user_id=access.user.id)
    await db.commit()
    return _project_response(proj)


@router.put("/{project_id}/ai-provider", response_model=ProjectResponse)
async def update_ai_provider(
    payload: AiProviderUpdate,
    access: ProjectAccess = Depends(check_project_access(role="owner")),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    svc = ProjectService()
    proj = await svc.update_ai_provider(
        db,
        project_id=access.project.id,
        actor_user_id=access.user.id,
        ai_provider=payload.ai_provider,
        ai_api_key=payload.ai_api_key,
    )
    await db.commit()
    return _project_response(proj)


# ─── Members ──────────────────────────────────────────


@router.get("/{project_id}/members", response_model=MemberListResponse)
async def list_members(
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> MemberListResponse:
    msvc = MemberService()
    rows = await msvc.list_members(db, project_id=access.project.id, actor_user_id=access.user.id)
    return MemberListResponse(items=[_member_response(m) for m in rows])


@router.post(
    "/{project_id}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED
)
async def invite_member(
    payload: MemberInvite,
    access: ProjectAccess = Depends(check_project_access(role="owner")),
    db: AsyncSession = Depends(get_db),
) -> MemberResponse:
    msvc = MemberService()
    m = await msvc.invite_member(
        db,
        project_id=access.project.id,
        actor_user_id=access.user.id,
        invited_user_id=payload.user_id,
        role=payload.role,
    )
    await db.commit()
    return _member_response(m)


@router.put("/{project_id}/members/{user_id}", response_model=MemberResponse)
async def update_member_role(
    user_id: UUID,
    payload: MemberRoleUpdate,
    access: ProjectAccess = Depends(check_project_access(role="owner")),
    db: AsyncSession = Depends(get_db),
) -> MemberResponse:
    msvc = MemberService()
    m = await msvc.update_member_role(
        db,
        project_id=access.project.id,
        actor_user_id=access.user.id,
        target_user_id=user_id,
        new_role=payload.role,
    )
    await db.commit()
    return _member_response(m)


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="owner")),
    db: AsyncSession = Depends(get_db),
) -> None:
    msvc = MemberService()
    await msvc.remove_member(
        db,
        project_id=access.project.id,
        actor_user_id=access.user.id,
        target_user_id=user_id,
    )
    await db.commit()


# ─── Dimension Configs ────────────────────────────────


@router.get("/{project_id}/dimension-configs", response_model=DimensionConfigListResponse)
async def list_dimension_configs(
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> DimensionConfigListResponse:
    svc = ProjectService()
    rows = await svc.dim_configs.list_by_project(db, access.project.id)
    items = [
        DimensionConfigResponse(
            id=r.id,
            project_id=r.project_id,
            dimension_type_id=r.dimension_type_id,
            enabled=r.enabled,
            sort_order=r.sort_order,
        )
        for r in rows
    ]
    return DimensionConfigListResponse(items=items)


@router.put("/{project_id}/dimension-configs", response_model=DimensionConfigListResponse)
async def batch_update_dimension_configs(
    payload: DimensionConfigBatchUpdate,
    access: ProjectAccess = Depends(check_project_access(role="owner")),
    db: AsyncSession = Depends(get_db),
) -> DimensionConfigListResponse:
    """R10-1 batch3 基线补丁: 每个 config 写独立 activity_log 事件 (R1-A P0→R2 修)."""
    svc = ProjectService()
    pid = access.project.id
    actor = access.user.id

    # 简化策略: 全删后插入 (上层 PUT 替换语义); 每个 INSERT 独立 audit 事件
    existing = await svc.dim_configs.list_by_project(db, pid)
    existing_map = {r.dimension_type_id: r for r in existing}
    incoming_ids = {item.dimension_type_id for item in payload.configs}

    # 校验所有 dimension_type_id 都存在
    for item in payload.configs:
        dt = await svc.dim_types.get_by_id(db, item.dimension_type_id)
        if dt is None:
            raise DimensionConfigInvalidError(
                dimension_type_id=item.dimension_type_id, reason="unknown_dimension_type"
            )

    written: list = []
    for item in payload.configs:
        prev = existing_map.get(item.dimension_type_id)
        if prev is None:
            cfg = await svc.dim_configs.create(
                db,
                project_id=pid,
                dimension_type_id=item.dimension_type_id,
                enabled=item.enabled,
                sort_order=item.sort_order,
            )
            await write_event(
                db=db,
                actor_user_id=actor,
                project_id=pid,
                action_type="update_dimension_config",
                target_type="project_dimension_config",
                target_id=str(cfg.id),
                summary=(
                    f"Created dimension config (type={item.dimension_type_id}, "
                    f"enabled={item.enabled})"
                ),
                metadata={
                    "project_id": str(pid),
                    "dimension_type_id": item.dimension_type_id,
                    "old_enabled": None,
                    "new_enabled": item.enabled,
                    "old_sort_order": None,
                    "new_sort_order": item.sort_order,
                },
            )
            written.append(cfg)
        else:
            # 仅在变化时写事件 (避免无意义 audit)
            if prev.enabled != item.enabled or prev.sort_order != item.sort_order:
                old_enabled, old_sort = prev.enabled, prev.sort_order
                prev.enabled = item.enabled
                prev.sort_order = item.sort_order
                await db.flush()
                await write_event(
                    db=db,
                    actor_user_id=actor,
                    project_id=pid,
                    action_type="update_dimension_config",
                    target_type="project_dimension_config",
                    target_id=str(prev.id),
                    summary=(f"Updated dimension config (type={item.dimension_type_id})"),
                    metadata={
                        "project_id": str(pid),
                        "dimension_type_id": item.dimension_type_id,
                        "old_enabled": old_enabled,
                        "new_enabled": item.enabled,
                        "old_sort_order": old_sort,
                        "new_sort_order": item.sort_order,
                    },
                )
            written.append(prev)

    # 删除缺失的 (R10-1: 删除也写独立事件; 简化为 update_dimension_config disabled 语义可换)
    for prev_id, prev in existing_map.items():
        if prev_id not in incoming_ids:
            from sqlalchemy import delete as _del

            from api.models.project import ProjectDimensionConfig

            await db.execute(
                _del(ProjectDimensionConfig).where(ProjectDimensionConfig.id == prev.id)
            )
            await write_event(
                db=db,
                actor_user_id=actor,
                project_id=pid,
                action_type="update_dimension_config",
                target_type="project_dimension_config",
                target_id=str(prev.id),
                summary=f"Removed dimension config (type={prev_id})",
                metadata={
                    "project_id": str(pid),
                    "dimension_type_id": prev_id,
                    "old_enabled": prev.enabled,
                    "new_enabled": None,
                    "old_sort_order": prev.sort_order,
                    "new_sort_order": None,
                },
            )
            await db.flush()

    await db.commit()

    items = [
        DimensionConfigResponse(
            id=r.id,
            project_id=r.project_id,
            dimension_type_id=r.dimension_type_id,
            enabled=r.enabled,
            sort_order=r.sort_order,
        )
        for r in written
    ]
    return DimensionConfigListResponse(items=items)
