"""M14 行业动态 DAO (async) — design/02-modules/M14-industry-news/00-design.md §9.

⚠️ GLOBAL DATA — NO TENANT FILTER
M14 行业动态是全局共享数据（见 06-design-principles.md 清单 5 豁免条件：全局数据）。
本 DAO 所有查询均**无** project_id / user_id 过滤；访问控制在 Service 层（写权限）/
Router 层（已登录即可读）。
豁免理由：全局行业动态，所有已登录用户均可见。

R-X3 精神：DAO 接受外部 session，不自 commit / 不自 begin。事务由 Service / Router 控制。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.models.industry_news import IndustryNews, NewsNodeLink


class IndustryNewsDAO:
    """⚠️ GLOBAL DATA — NO TENANT FILTER（design §9 + 06-design-principles 清单 5）。"""

    # ─────────── 读 ───────────

    async def list_all(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        tag: str | None = None,
    ) -> tuple[Sequence[IndustryNews], int]:
        """全局列表 + 分页 + 可选 tag 过滤（design §7 GET /api/news）。

        ⚠️ 无 project_id 过滤——全局数据豁免（清单 5）。
        ORDER BY created_at DESC 走 ix_industry_news_created_at 索引。
        分页 page/page_size 越界时返回空 items + 真实 total（不报错，design §14 E4）。
        """
        base = select(IndustryNews)
        if tag is not None:
            base = base.where(IndustryNews.tags.contains([tag]))

        total_stmt = select(func.count(IndustryNews.id)).select_from(IndustryNews)
        if tag is not None:
            total_stmt = total_stmt.where(IndustryNews.tags.contains([tag]))
        total = int((await db.execute(total_stmt)).scalar_one())

        stmt = (
            base.options(selectinload(IndustryNews.node_links))
            .order_by(IndustryNews.created_at.desc(), IndustryNews.id.desc())
            .offset(max(0, (page - 1) * page_size))
            .limit(page_size)
        )
        items = (await db.execute(stmt)).scalars().all()
        return items, total

    async def get_by_id(self, db: AsyncSession, news_id: UUID) -> IndustryNews | None:
        """⚠️ 无 tenant 过滤——全局豁免。"""
        result = await db.execute(
            select(IndustryNews)
            .options(selectinload(IndustryNews.node_links))
            .where(IndustryNews.id == news_id)
        )
        return result.scalar_one_or_none()

    async def list_by_node(self, db: AsyncSession, node_id: UUID) -> Sequence[IndustryNews]:
        """反查某 node 关联的全部动态（design §7 GET /api/nodes/{node_id}/news）。

        ⚠️ 无 project_id 过滤——全局数据；node 存在则返回，跨项目查询允许（design §1 灰区 2）。
        """
        result = await db.execute(
            select(IndustryNews)
            .options(selectinload(IndustryNews.node_links))
            .join(NewsNodeLink, NewsNodeLink.news_id == IndustryNews.id)
            .where(NewsNodeLink.node_id == node_id)
            .order_by(IndustryNews.created_at.desc(), IndustryNews.id.desc())
        )
        return result.scalars().unique().all()

    # ─────────── 写 ───────────

    async def create(self, db: AsyncSession, record: IndustryNews) -> IndustryNews:
        db.add(record)
        await db.flush()
        return record

    async def update(
        self,
        db: AsyncSession,
        news_id: UUID,
        *,
        fields: dict[str, Any],
    ) -> int:
        """部分更新 industry_news 行（design §7 PUT /api/news/{news_id}）。

        ⚠️ 无 project_id 过滤；调用方（Service）负责权限校验。
        """
        if not fields:
            raise ValueError("fields cannot be empty")
        result = await db.execute(
            update(IndustryNews).where(IndustryNews.id == news_id).values(**fields)
        )
        return result.rowcount

    async def delete_by_id(self, db: AsyncSession, news_id: UUID) -> int:
        """⚠️ 无 project_id 过滤；调用方（Service）负责权限校验。"""
        result = await db.execute(delete(IndustryNews).where(IndustryNews.id == news_id))
        return result.rowcount


class NewsNodeLinkDAO:
    """关联表 DAO（M14 own）。⚠️ 无 tenant 过滤——M14 全局豁免。"""

    async def list_by_news(self, db: AsyncSession, news_id: UUID) -> Sequence[NewsNodeLink]:
        result = await db.execute(select(NewsNodeLink).where(NewsNodeLink.news_id == news_id))
        return result.scalars().all()

    async def get_by_pair(
        self, db: AsyncSession, news_id: UUID, node_id: UUID
    ) -> NewsNodeLink | None:
        result = await db.execute(
            select(NewsNodeLink).where(
                NewsNodeLink.news_id == news_id,
                NewsNodeLink.node_id == node_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, record: NewsNodeLink) -> NewsNodeLink:
        db.add(record)
        await db.flush()
        return record

    async def delete_by_pair(self, db: AsyncSession, news_id: UUID, node_id: UUID) -> int:
        result = await db.execute(
            delete(NewsNodeLink).where(
                NewsNodeLink.news_id == news_id,
                NewsNodeLink.node_id == node_id,
            )
        )
        return result.rowcount
