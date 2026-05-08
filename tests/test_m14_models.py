"""M14 子片 1 — IndustryNews + NewsNodeLink model 单元测试。

覆盖 design §3 SQLAlchemy block：
- industry_news 持久化 + 默认 source_type='manual' + tags 默认空数组
- source_type CHECK 约束（仅 manual）
- news_node_links UNIQUE(news_id, node_id) 防重复
- IndustryNews→NewsNodeLink cascade='all, delete-orphan'
- nodes ON DELETE CASCADE 联动 news_node_links
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from api.models.industry_news import IndustryNews, NewsNodeLink
from api.models.node import Node

# ─────────────── M14-MODEL-T1 持久化基础 ───────────────


async def test_news_persists_with_defaults(db_session, make_user):
    user = await make_user()
    n = IndustryNews(
        title="AI 监管新规",
        created_by=user.id,
        updated_by=user.id,
    )
    db_session.add(n)
    await db_session.flush()
    await db_session.refresh(n)
    assert n.id is not None
    assert n.source_type == "manual"
    assert n.tags == []
    assert n.summary is None
    assert n.published_date is None


async def test_news_persists_full_fields(db_session, make_user):
    user = await make_user()
    n = IndustryNews(
        title="量子计算商业化",
        summary="某厂商发布 1000 量子位芯片",
        source_url="https://example.com/article/1",
        published_date=date(2026, 5, 1),
        tags=["AI", "硬件"],
        created_by=user.id,
        updated_by=user.id,
    )
    db_session.add(n)
    await db_session.flush()
    await db_session.refresh(n)
    assert n.tags == ["AI", "硬件"]
    assert n.published_date == date(2026, 5, 1)
    assert n.source_url == "https://example.com/article/1"


# ─────────────── M14-MODEL-T2 source_type CHECK ───────────────


async def test_news_source_type_rss_violates_check(db_session, make_user):
    """source_type 仅允许 'manual'；rss/ai 预留但 CHECK 拦截。"""
    user = await make_user()
    n = IndustryNews(
        title="t",
        source_type="rss",
        created_by=user.id,
        updated_by=user.id,
    )
    db_session.add(n)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M14-MODEL-T3 NewsNodeLink ───────────────


async def test_news_node_link_persists(db_session, make_project, make_node, make_user):
    user, proj = await make_project()
    node = await make_node(proj.id, name="login")
    n = IndustryNews(
        title="auth update",
        created_by=user.id,
        updated_by=user.id,
    )
    db_session.add(n)
    await db_session.flush()
    link = NewsNodeLink(news_id=n.id, node_id=node.id, linked_by=user.id)
    db_session.add(link)
    await db_session.flush()
    await db_session.refresh(link)
    assert link.id is not None
    assert link.linked_at is not None


async def test_news_node_link_unique_pair_violates(db_session, make_project, make_node, make_user):
    """UNIQUE(news_id, node_id) 防重复关联。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="x")
    n = IndustryNews(title="t", created_by=user.id, updated_by=user.id)
    db_session.add(n)
    await db_session.flush()
    db_session.add(NewsNodeLink(news_id=n.id, node_id=node.id, linked_by=user.id))
    await db_session.flush()
    db_session.add(NewsNodeLink(news_id=n.id, node_id=node.id, linked_by=user.id))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_news_node_link_same_news_different_nodes_allowed(
    db_session, make_project, make_node, make_user
):
    user, proj = await make_project()
    node1 = await make_node(proj.id, name="a")
    node2 = await make_node(proj.id, name="b")
    n = IndustryNews(title="t", created_by=user.id, updated_by=user.id)
    db_session.add(n)
    await db_session.flush()
    db_session.add_all(
        [
            NewsNodeLink(news_id=n.id, node_id=node1.id, linked_by=user.id),
            NewsNodeLink(news_id=n.id, node_id=node2.id, linked_by=user.id),
        ]
    )
    await db_session.flush()  # OK


# ─────────────── M14-MODEL-T4 cascade 行为 ───────────────


async def test_news_delete_cascades_node_links(db_session, make_project, make_node, make_user):
    """IndustryNews delete → NewsNodeLink cascade='all, delete-orphan' 删除关联行。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="x")
    n = IndustryNews(title="t", created_by=user.id, updated_by=user.id)
    db_session.add(n)
    await db_session.flush()
    db_session.add(NewsNodeLink(news_id=n.id, node_id=node.id, linked_by=user.id))
    await db_session.flush()

    await db_session.delete(n)
    await db_session.flush()
    rows = (
        (await db_session.execute(select(NewsNodeLink).where(NewsNodeLink.news_id == n.id)))
        .scalars()
        .all()
    )
    assert rows == []


async def test_node_delete_cascades_news_node_link(db_session, make_project, make_node, make_user):
    """nodes ON DELETE CASCADE → news_node_links 行级联删除。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="x")
    n = IndustryNews(title="t", created_by=user.id, updated_by=user.id)
    db_session.add(n)
    await db_session.flush()
    db_session.add(NewsNodeLink(news_id=n.id, node_id=node.id, linked_by=user.id))
    await db_session.flush()

    # 走 SQL 级 DELETE 触发 ON DELETE CASCADE（ORM 删除会先 emit 子表 DELETE）
    await db_session.execute(delete(Node).where(Node.id == node.id))
    await db_session.flush()
    rows = (
        (await db_session.execute(select(NewsNodeLink).where(NewsNodeLink.news_id == n.id)))
        .scalars()
        .all()
    )
    assert rows == []


# ─────────────── M14-MODEL-T5 不同 news 可关联同一 node ───────────────


async def test_different_news_same_node_allowed(db_session, make_project, make_node, make_user):
    user, proj = await make_project()
    node = await make_node(proj.id, name="x")
    n1 = IndustryNews(title="t1", created_by=user.id, updated_by=user.id)
    n2 = IndustryNews(title="t2", created_by=user.id, updated_by=user.id)
    db_session.add_all([n1, n2])
    await db_session.flush()
    db_session.add_all(
        [
            NewsNodeLink(news_id=n1.id, node_id=node.id, linked_by=user.id),
            NewsNodeLink(news_id=n2.id, node_id=node.id, linked_by=user.id),
        ]
    )
    await db_session.flush()  # OK
