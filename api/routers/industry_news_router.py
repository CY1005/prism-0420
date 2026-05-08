"""M14 行业动态 router — design/02-modules/M14-industry-news/00-design.md §7 + §8。

8 endpoints（design §7）：
- 全局 list / get / create / update / delete (5)
- 关联管理 link / unlink (2)
- 节点级反查 list_by_node (1)

⚠️ 全局豁免（design §9 + 06-design-principles 清单 5）：
- 无 project_id 路径参数（M14 全局共享数据）
- Router 层 require_user 鉴权（已登录即可读 + 已登录即可写，无 project role）
- Service 层 _check_news_owner_or_admin 校验删除/编辑（design §8）
- link/unlink 已登录即可（design §8 R1-A P1-2 立修 disambiguation）
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.db import get_db
from api.models.industry_news import IndustryNews, NewsNodeLink
from api.models.user import User
from api.routers.auth import current_user
from api.schemas.industry_news_schema import (
    NewsCreate,
    NewsListResponse,
    NewsNodeLinkCreate,
    NewsNodeLinkResponse,
    NewsResponse,
    NewsUpdate,
    NodeRef,
)
from api.services.industry_news_service import IndustryNewsService

# ─────────────── routers ───────────────

news_router = APIRouter(prefix="/api/news", tags=["industry-news"])
news_node_router = APIRouter(prefix="/api/nodes/{node_id}/news", tags=["industry-news"])


# ─────────────── helpers ───────────────


async def _to_response(db: AsyncSession, n: IndustryNews) -> NewsResponse:
    """构造 NewsResponse 含 linked_nodes（NodeRef 含 node_name + project_id；R1-A P1-1 链通）。"""
    creator = await db.get(User, n.created_by)
    return NewsResponse(
        id=n.id,
        title=n.title,
        summary=n.summary,
        source_url=n.source_url,
        published_date=n.published_date,
        source_type=n.source_type,
        tags=list(n.tags or []),
        linked_nodes=[
            NodeRef(
                node_id=link.node.id,
                node_name=link.node.name,
                project_id=link.node.project_id,
            )
            for link in n.node_links
            if link.node is not None
        ],
        created_by=n.created_by,
        created_by_name=creator.name if creator else None,
        created_at=n.created_at,
        updated_at=n.updated_at,
    )


async def _to_link_response(db: AsyncSession, link: NewsNodeLink) -> NewsNodeLinkResponse:
    """NewsNodeLinkResponse 含 node_name；R1-A P1-1 链通。"""
    if link.node is None:
        # 防御：link 对应 node 已被删除（race），重新查；通常 selectinload 已加载
        from api.models.node import Node

        node = (await db.execute(select(Node).where(Node.id == link.node_id))).scalar_one_or_none()
        node_name = node.name if node else ""
    else:
        node_name = link.node.name
    return NewsNodeLinkResponse(
        news_id=link.news_id,
        node_id=link.node_id,
        node_name=node_name,
        linked_by=link.linked_by,
        linked_at=link.linked_at,
    )


# ─────────────── 全局 news endpoints ───────────────


@news_router.get("", response_model=NewsListResponse)
async def list_news(
    user: User = Depends(current_user),  # noqa: ARG001 — 已登录即可读
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tag: str | None = Query(None),
) -> NewsListResponse:
    svc = IndustryNewsService()
    items, total = await svc.list_news(db, page=page, page_size=page_size, tag=tag)
    return NewsListResponse(
        items=[await _to_response(db, n) for n in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@news_router.get("/{news_id}", response_model=NewsResponse)
async def get_news(
    news_id: UUID,
    user: User = Depends(current_user),  # noqa: ARG001 — 已登录即可读
    db: AsyncSession = Depends(get_db),
) -> NewsResponse:
    svc = IndustryNewsService()
    n = await svc.get_news(db, news_id=news_id)
    return await _to_response(db, n)


@news_router.post("", response_model=NewsResponse, status_code=status.HTTP_201_CREATED)
async def create_news(
    payload: NewsCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> NewsResponse:
    svc = IndustryNewsService()
    n = await svc.create_news(
        db,
        actor_user_id=user.id,
        title=payload.title,
        summary=payload.summary,
        source_url=str(payload.source_url) if payload.source_url is not None else None,
        published_date=payload.published_date,
        tags=payload.tags,
    )
    await db.commit()
    fresh = await svc.get_news(db, news_id=n.id)
    return await _to_response(db, fresh)


@news_router.put("/{news_id}", response_model=NewsResponse)
async def update_news(
    news_id: UUID,
    payload: NewsUpdate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> NewsResponse:
    svc = IndustryNewsService()
    # exclude_unset=True：用户未传字段不参与 update（vs 显式传 None 视为清空，R1 立修后行为）
    fields = payload.model_dump(exclude_unset=True)
    if "source_url" in fields and fields["source_url"] is not None:
        fields["source_url"] = str(fields["source_url"])
    fresh = await svc.update_news(
        db,
        actor_user_id=user.id,
        actor_role=user.role,
        news_id=news_id,
        fields=fields,
    )
    await db.commit()
    fresh = await svc.get_news(db, news_id=news_id)
    return await _to_response(db, fresh)


@news_router.delete("/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_news(
    news_id: UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    svc = IndustryNewsService()
    await svc.delete_news(db, actor_user_id=user.id, actor_role=user.role, news_id=news_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─────────────── 关联管理 ───────────────


@news_router.post(
    "/{news_id}/links",
    response_model=NewsNodeLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def link_node(
    news_id: UUID,
    payload: NewsNodeLinkCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> NewsNodeLinkResponse:
    svc = IndustryNewsService()
    link = await svc.link_node(
        db,
        actor_user_id=user.id,
        actor_role=user.role,
        news_id=news_id,
        node_id=payload.node_id,
    )
    await db.commit()
    # 重新查 with selectinload(node) 拿 node_name
    from api.dao.industry_news_dao import NewsNodeLinkDAO

    fresh_link = await NewsNodeLinkDAO().get_by_pair(db, news_id, payload.node_id)
    if fresh_link is None:
        # 极端 race（关联刚建即被删）；返回原 link
        return await _to_link_response(db, link)
    # 显式 selectinload 重新查，确保 node 字段加载
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(NewsNodeLink)
        .options(selectinload(NewsNodeLink.node))
        .where(NewsNodeLink.id == fresh_link.id)
    )
    loaded = result.scalar_one()
    return await _to_link_response(db, loaded)


@news_router.delete("/{news_id}/links/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_node(
    news_id: UUID,
    node_id: UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    svc = IndustryNewsService()
    await svc.unlink_node(db, actor_user_id=user.id, news_id=news_id, node_id=node_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─────────────── 节点级反查 ───────────────


@news_node_router.get("", response_model=NewsListResponse)
async def list_news_by_node(
    node_id: UUID,
    user: User = Depends(current_user),  # noqa: ARG001 — 已登录即可读
    db: AsyncSession = Depends(get_db),
) -> NewsListResponse:
    svc = IndustryNewsService()
    items = await svc.list_news_by_node(db, node_id=node_id)
    responses = [await _to_response(db, n) for n in items]
    return NewsListResponse(
        items=responses, total=len(responses), page=1, page_size=len(responses) or 1
    )
