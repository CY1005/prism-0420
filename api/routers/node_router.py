"""M03 功能模块树 router (design §7 + §8 权限三层).

8 endpoints (design §7 表):
    GET    /api/projects/{pid}/nodes                       list_tree (NodeTreeResponse)
    POST   /api/projects/{pid}/nodes                       create_node
    GET    /api/projects/{pid}/nodes/{nid}                 get_node
    PUT    /api/projects/{pid}/nodes/{nid}                 update_node
    DELETE /api/projects/{pid}/nodes/{nid}                 delete_node (204)
    POST   /api/projects/{pid}/nodes/reorder               reorder_siblings
    POST   /api/projects/{pid}/nodes/{nid}/move            move_subtree
    GET    /api/projects/{pid}/nodes/{nid}/breadcrumb      breadcrumb

权限 (design §8 R8-1 三层):
    - Server Action: session 校验 (UNAUTHENTICATED)
    - Router: check_project_access role="viewer" (read) / "editor" (write)
    - Service: _check_node_belongs_to_project (DAO get_by_id 强制 project_id)
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.check_project_access import ProjectAccess, check_project_access
from api.core.db import get_db
from api.models.node import Node
from api.schemas.node_schema import (
    BreadcrumbItem,
    BreadcrumbResponse,
    NodeCreate,
    NodeListResponse,
    NodeMove,
    NodeReorder,
    NodeResponse,
    NodeTreeResponse,
    NodeUpdate,
    NodeWithChildrenResponse,
)
from api.services.node_service import NodeService

router = APIRouter(prefix="/api/projects/{project_id}/nodes", tags=["nodes"])


def _node_response(n: Node) -> NodeResponse:
    return NodeResponse.model_validate(n, from_attributes=True)


def _build_tree(nodes: list[Node]) -> list[NodeWithChildrenResponse]:
    """flat list → 嵌套 NodeWithChildrenResponse 列表（root 层只保留 parent_id is None）。

    nodes 已按 (depth, sort_order) 排序，单遍构建即可（父先于子）。

    注意：不能用 model_validate(from_attributes=True)——会触发 SQLAlchemy lazy load
    Node.children 异步关系，引发 MissingGreenlet。改为先 NodeResponse 字段抽取再
    构造 NodeWithChildrenResponse(children=[])。
    """
    by_id: dict[UUID, NodeWithChildrenResponse] = {}
    roots: list[NodeWithChildrenResponse] = []
    for n in nodes:
        flat = NodeResponse.model_validate(n, from_attributes=True).model_dump()
        wrapped = NodeWithChildrenResponse(**flat, children=[])
        by_id[n.id] = wrapped
        if n.parent_id is None:
            roots.append(wrapped)
        else:
            parent = by_id.get(n.parent_id)
            if parent is not None:
                parent.children.append(wrapped)
    return roots


# ─── Read ──────────────────────────────────────────────


@router.get("", response_model=NodeTreeResponse)
async def list_tree(
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> NodeTreeResponse:
    svc = NodeService()
    flat = await svc.list_tree(db, access.project.id)
    return NodeTreeResponse(roots=_build_tree(flat))


@router.get("/{node_id}", response_model=NodeResponse)
async def get_node(
    node_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> NodeResponse:
    svc = NodeService()
    node = await svc.get_node(db, node_id, access.project.id)
    return _node_response(node)


@router.get("/{node_id}/breadcrumb", response_model=BreadcrumbResponse)
async def breadcrumb(
    node_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> BreadcrumbResponse:
    svc = NodeService()
    chain = await svc.breadcrumb(db, node_id, access.project.id)
    return BreadcrumbResponse(
        items=[BreadcrumbItem(id=n.id, name=n.name, depth=n.depth) for n in chain]
    )


# ─── Write ─────────────────────────────────────────────


@router.post("", response_model=NodeResponse, status_code=status.HTTP_201_CREATED)
async def create_node(
    payload: NodeCreate,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> NodeResponse:
    svc = NodeService()
    node = await svc.create_node(
        db,
        project_id=access.project.id,
        actor_user_id=access.user.id,
        name=payload.name,
        type=payload.type.value,
        parent_id=payload.parent_id,
        sort_order=payload.sort_order,
        description=payload.description,
    )
    await db.commit()
    return _node_response(node)


@router.put("/{node_id}", response_model=NodeResponse)
async def update_node(
    node_id: UUID,
    payload: NodeUpdate,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> NodeResponse:
    svc = NodeService()
    # L1-α detach: description 显式 None 视为清空；name NOT NULL 不参与 detach
    fields = payload.model_dump(exclude_unset=True)
    node = await svc.update_node(
        db,
        project_id=access.project.id,
        node_id=node_id,
        actor_user_id=access.user.id,
        fields=fields,
    )
    await db.commit()
    return _node_response(node)


@router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(
    node_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    svc = NodeService()
    await svc.delete_node(
        db,
        project_id=access.project.id,
        node_id=node_id,
        actor_user_id=access.user.id,
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reorder", response_model=NodeListResponse)
async def reorder_siblings(
    payload: NodeReorder,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> NodeListResponse:
    """重排同级节点。返回受影响的同级节点最新 sort_order（design §7）。

    R2-1 修：原实装返回 NodeTreeResponse 整树是契约漂移（design §7 字面 NodeListResponse）；
    且 service 已返回 list[Node]，router 不再多调 svc.list_tree（R2-2 N+1 同合并修）。
    """
    svc = NodeService()
    updated = await svc.reorder_siblings(
        db,
        project_id=access.project.id,
        actor_user_id=access.user.id,
        parent_id=payload.parent_id,
        items=[(item.node_id, item.sort_order) for item in payload.items],
    )
    await db.commit()
    return NodeListResponse(items=[_node_response(n) for n in updated])


@router.post("/{node_id}/move", response_model=NodeResponse)
async def move_subtree(
    node_id: UUID,
    payload: NodeMove,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> NodeResponse:
    svc = NodeService()
    moved = await svc.move_subtree(
        db,
        project_id=access.project.id,
        node_id=node_id,
        actor_user_id=access.user.id,
        new_parent_id=payload.new_parent_id,
    )
    await db.commit()
    return _node_response(moved)
