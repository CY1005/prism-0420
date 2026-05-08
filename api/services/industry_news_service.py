"""M14 IndustryNewsService — design/02-modules/M14-industry-news/00-design.md §6。

⚠️ 全局豁免业务模块（首发，2026-05-08）：
- DAO 无 tenant 过滤（设计 §9 + 06-design-principles 清单 5）
- Router 层"已登录即可读 + 已登录即可写"（design §8）
- Service 层 _check_news_owner_or_admin：删除/编辑必须 created_by==user OR platform_admin

事务边界（M02-M13 范式延续）：Router 层管 commit；本 service 接受外部 AsyncSession，
不调 ``async with db.begin():`` / 不主动 commit / 不主动 rollback。

权限三层（design §8）：
- Server Action / Router require_user（已登录即可）
- Router 层不再细分 project role（M14 全局豁免无 project role）
- Service _check_news_owner_or_admin（删除/编辑写权限）
- Service _check_node_exists（关联时校验 node 存在；跨项目允许，design §1 灰区 2）
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.dao.industry_news_dao import IndustryNewsDAO, NewsNodeLinkDAO
from api.errors.exceptions import (
    NewsForbiddenError,
    NewsLinkDuplicateError,
    NewsLinkNotFoundError,
    NewsNotFoundError,
    NotFoundError,
)
from api.models.industry_news import IndustryNews, NewsNodeLink
from api.models.node import Node
from api.models.user import UserRole
from api.services.activity_log_service import write_event


class IndustryNewsService:
    def __init__(
        self,
        dao: IndustryNewsDAO | None = None,
        link_dao: NewsNodeLinkDAO | None = None,
    ) -> None:
        self.dao = dao or IndustryNewsDAO()
        self.link_dao = link_dao or NewsNodeLinkDAO()

    # ─── 内部校验 ───

    async def _get_or_raise(self, db: AsyncSession, news_id: UUID) -> IndustryNews:
        n = await self.dao.get_by_id(db, news_id)
        if n is None:
            raise NewsNotFoundError(news_id=str(news_id))
        return n

    async def _check_news_owner_or_admin(
        self, news: IndustryNews, *, actor_user_id: UUID, actor_role: str
    ) -> None:
        """删除/编辑权限：created_by==actor OR actor 是 platform_admin（design §8）。"""
        if news.created_by == actor_user_id:
            return
        if actor_role == UserRole.PLATFORM_ADMIN.value:
            return
        raise NewsForbiddenError(
            news_id=str(news.id),
            actor_user_id=str(actor_user_id),
        )

    async def _check_node_exists(self, db: AsyncSession, node_id: UUID) -> Node:
        """关联功能项时校验 node 存在（design §1 灰区 2 ack：跨项目允许）。

        node 不存在则抛 NotFoundError（404）；不校验 node.project_id 归属——M14 全局动态可关联任意 node。
        """
        result = await db.execute(select(Node).where(Node.id == node_id))
        node = result.scalar_one_or_none()
        if node is None:
            raise NotFoundError(node_id=str(node_id))
        return node

    # ─── 读 ───

    async def list_news(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        tag: str | None = None,
    ) -> tuple[list[IndustryNews], int]:
        items, total = await self.dao.list_all(db, page=page, page_size=page_size, tag=tag)
        return list(items), total

    async def get_news(self, db: AsyncSession, *, news_id: UUID) -> IndustryNews:
        return await self._get_or_raise(db, news_id)

    async def list_news_by_node(self, db: AsyncSession, *, node_id: UUID) -> list[IndustryNews]:
        return list(await self.dao.list_by_node(db, node_id))

    # ─── 写 ───

    async def create_news(
        self,
        db: AsyncSession,
        *,
        actor_user_id: UUID,
        title: str,
        summary: str | None = None,
        source_url: str | None = None,
        published_date: Any = None,
        tags: list[str] | None = None,
    ) -> IndustryNews:
        """design §10 create：1 条 activity_log 全局事件（project_id=None 走 stub "global"）。"""
        rec = IndustryNews(
            title=title,
            summary=summary,
            source_url=source_url,
            published_date=published_date,
            source_type="manual",  # service 层强制（design §3 灰区 1）
            tags=list(tags) if tags is not None else [],
            created_by=actor_user_id,
            updated_by=actor_user_id,
        )
        await self.dao.create(db, rec)
        await db.refresh(rec, attribute_names=["created_at", "updated_at"])
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=None,  # M14 全局豁免（首发，2026-05-08）
            action_type="create",
            target_type="industry_news",
            target_id=str(rec.id),
            summary=f"录入行业动态：{title}",
            metadata={
                "source_type": "manual",
                "tags_count": len(rec.tags),
            },
        )
        return rec

    async def update_news(
        self,
        db: AsyncSession,
        *,
        actor_user_id: UUID,
        actor_role: str,
        news_id: UUID,
        fields: dict[str, Any],
    ) -> IndustryNews:
        """design §10 update：fields 不含 source_type（不可改）/ updated_by 自动注入。

        R1-A P1-3 + R1-C P1-1 立修（2026-05-08）：
        - 改用 ORM mutate (setattr + flush) 替代 dao.update raw SQL + db.refresh，
          与 M02-M13 service 范式一致；避免 raw UPDATE 后 ORM identity map 不一致 + relationship expire。
        - 不再 ``v is not None`` 过滤——caller（Router）用 ``model_dump(exclude_unset=True)`` 控制
          字段集；显式传 ``summary=None`` 视为清空操作（`tags=[]` / `summary=None`）。
        - source_type 仍强滤（design §3 灰区 1 service 层强制）。
        """
        n = await self._get_or_raise(db, news_id)
        await self._check_news_owner_or_admin(n, actor_user_id=actor_user_id, actor_role=actor_role)
        sanitized = {k: v for k, v in fields.items() if k != "source_type"}
        if not sanitized:
            return n
        for k, v in sanitized.items():
            setattr(n, k, v)
        n.updated_by = actor_user_id
        await db.flush()
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=None,  # 全局
            action_type="update",
            target_type="industry_news",
            target_id=str(news_id),
            summary=f"更新行业动态：{n.title}",
            metadata={"updated_fields": sorted(sanitized.keys())},
        )
        return await self._get_or_raise(db, news_id)  # 重新带 selectinload(node_links→node)

    async def delete_news(
        self,
        db: AsyncSession,
        *,
        actor_user_id: UUID,
        actor_role: str,
        news_id: UUID,
    ) -> None:
        n = await self._get_or_raise(db, news_id)
        await self._check_news_owner_or_admin(n, actor_user_id=actor_user_id, actor_role=actor_role)
        title = n.title
        await self.dao.delete_by_id(db, news_id)
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=None,  # 全局
            action_type="delete",
            target_type="industry_news",
            target_id=str(news_id),
            summary=f"删除行业动态：{title}",
            metadata={"title": title},
        )

    # ─── 关联 ───

    async def link_node(
        self,
        db: AsyncSession,
        *,
        actor_user_id: UUID,
        actor_role: str,
        news_id: UUID,
        node_id: UUID,
    ) -> NewsNodeLink:
        """design §10 link：1 条 activity_log；UNIQUE 约束并发 → NewsLinkDuplicateError 409。

        权限（design §8）：已登录即可关联（不要求 owner，与 update/delete 不同）。
        node 跨项目允许（design §1 灰区 2）。
        """
        n = await self._get_or_raise(db, news_id)
        node = await self._check_node_exists(db, node_id)
        link = NewsNodeLink(news_id=news_id, node_id=node_id, linked_by=actor_user_id)
        try:
            await self.link_dao.create(db, link)
        except IntegrityError as e:
            # M05 P1-01 范式延续：区分约束名映射 NEWS_LINK_DUPLICATE 而非 INTERNAL_ERROR
            err_text = str(e.orig) if e.orig else str(e)
            if "uq_news_node_link" in err_text:
                raise NewsLinkDuplicateError(
                    news_id=str(news_id),
                    node_id=str(node_id),
                ) from e
            raise
        await db.refresh(link, attribute_names=["linked_at"])
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=None,
            action_type="link",
            target_type="news_node_link",
            target_id=str(news_id),
            summary=f"关联功能项：{node.name}",
            metadata={"node_id": str(node_id), "news_title": n.title},
        )
        return link

    async def unlink_node(
        self,
        db: AsyncSession,
        *,
        actor_user_id: UUID,
        news_id: UUID,
        node_id: UUID,
    ) -> None:
        """design §10 unlink：1 条 activity_log；不存在则 404 NEWS_LINK_NOT_FOUND。

        权限（design §8）：已登录即可解除关联（与 link 对称）。
        """
        # 校验 news 存在（统一与 link 错误层次）
        n = await self._get_or_raise(db, news_id)
        existing = await self.link_dao.get_by_pair(db, news_id, node_id)
        if existing is None:
            raise NewsLinkNotFoundError(
                news_id=str(news_id),
                node_id=str(node_id),
            )
        rc = await self.link_dao.delete_by_pair(db, news_id, node_id)
        if rc == 0:
            raise NewsLinkNotFoundError(
                news_id=str(news_id),
                node_id=str(node_id),
            )
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=None,
            action_type="unlink",
            target_type="news_node_link",
            target_id=str(news_id),
            summary=f"解除关联功能项 node={node_id}",
            metadata={"node_id": str(node_id), "news_title": n.title},
        )
