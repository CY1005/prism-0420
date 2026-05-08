"""M14 子片 2 — IndustryNewsDAO + NewsNodeLinkDAO 单元测试。

⚠️ GLOBAL DATA — NO TENANT FILTER 路径覆盖（design §9 + 06-design-principles 清单 5）：
- list_all 无 tenant 过滤 → 不同 project 用户均可见全部
- get_by_id / list_by_news 无 tenant 过滤
- list_by_node 跨项目允许（design §1 灰区 2）
"""

from __future__ import annotations

from datetime import UTC
from uuid import uuid4

import pytest

from api.dao.industry_news_dao import IndustryNewsDAO, NewsNodeLinkDAO
from api.models.industry_news import IndustryNews, NewsNodeLink

# ─────────────── helpers ───────────────


async def _make_news(
    db_session,
    user,
    *,
    title: str = "t",
    tags: list[str] | None = None,
):
    n = IndustryNews(
        title=title,
        tags=tags if tags is not None else [],
        created_by=user.id,
        updated_by=user.id,
    )
    db_session.add(n)
    await db_session.flush()
    return n


# ─────────────── DAO list_all ───────────────


async def test_list_all_returns_global_no_tenant_filter(db_session, make_project):
    """全局豁免：不同 project 用户创建的动态均出现在列表中（无 project_id 过滤）。"""
    user_a, _ = await make_project(name_suffix="-A")
    user_b, _ = await make_project(name_suffix="-B")
    await _make_news(db_session, user_a, title="from-A")
    await _make_news(db_session, user_b, title="from-B")

    dao = IndustryNewsDAO()
    items, total = await dao.list_all(db_session)
    titles = {n.title for n in items}
    assert {"from-A", "from-B"} <= titles
    assert total >= 2


async def test_list_all_pagination_returns_empty_beyond_total(db_session, make_user):
    user = await make_user()
    await _make_news(db_session, user, title="x")
    dao = IndustryNewsDAO()
    items, total = await dao.list_all(db_session, page=999, page_size=20)
    assert items == []
    assert total >= 1


async def test_list_all_orders_by_created_at_desc(db_session, make_user):
    """ORDER BY created_at DESC（同事务内 created_at 由 server_default func.now() 取
    statement-level 时间戳，可能并列；本测试显式注入不同 created_at 验证排序方向）。"""
    from datetime import datetime, timedelta

    user = await make_user()
    n1 = await _make_news(db_session, user, title="first")
    n2 = await _make_news(db_session, user, title="second")
    n1.created_at = datetime.now(UTC) - timedelta(seconds=10)
    n2.created_at = datetime.now(UTC)
    await db_session.flush()
    dao = IndustryNewsDAO()
    items, _ = await dao.list_all(db_session, page_size=10)
    seen = [i for i in items if i.id in {n1.id, n2.id}]
    assert seen[0].id == n2.id
    assert seen[1].id == n1.id


async def test_list_all_filters_by_tag(db_session, make_user):
    user = await make_user()
    await _make_news(db_session, user, title="ai-news", tags=["AI", "监管"])
    await _make_news(db_session, user, title="hw-news", tags=["硬件"])
    dao = IndustryNewsDAO()
    items, _ = await dao.list_all(db_session, tag="AI")
    titles = {n.title for n in items}
    assert "ai-news" in titles
    assert "hw-news" not in titles


# ─────────────── DAO get_by_id ───────────────


async def test_get_by_id_finds_record(db_session, make_user):
    user = await make_user()
    n = await _make_news(db_session, user)
    dao = IndustryNewsDAO()
    found = await dao.get_by_id(db_session, n.id)
    assert found is not None
    assert found.id == n.id


async def test_get_by_id_returns_none_for_missing(db_session):
    dao = IndustryNewsDAO()
    assert await dao.get_by_id(db_session, uuid4()) is None


# ─────────────── DAO list_by_node ───────────────


async def test_list_by_node_returns_only_linked_news(
    db_session, make_project, make_node, make_user
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="x")
    n_linked = await _make_news(db_session, user, title="linked")
    await _make_news(db_session, user, title="other")
    db_session.add(NewsNodeLink(news_id=n_linked.id, node_id=node.id, linked_by=user.id))
    await db_session.flush()

    dao = IndustryNewsDAO()
    items = await dao.list_by_node(db_session, node.id)
    titles = {n.title for n in items}
    assert "linked" in titles
    assert "other" not in titles


async def test_list_by_node_empty_returns_empty_list(db_session, make_project, make_node):
    _, proj = await make_project()
    node = await make_node(proj.id, name="x")
    dao = IndustryNewsDAO()
    assert list(await dao.list_by_node(db_session, node.id)) == []


# ─────────────── DAO update / delete ───────────────


async def test_update_news_changes_fields(db_session, make_user):
    user = await make_user()
    n = await _make_news(db_session, user, title="old")
    dao = IndustryNewsDAO()
    n_updated = await dao.update(
        db_session, n.id, fields={"title": "new", "summary": "updated", "updated_by": user.id}
    )
    assert n_updated == 1
    fresh = await dao.get_by_id(db_session, n.id)
    assert fresh is not None
    assert fresh.title == "new"
    assert fresh.summary == "updated"


async def test_update_empty_fields_raises(db_session, make_user):
    user = await make_user()
    n = await _make_news(db_session, user)
    dao = IndustryNewsDAO()
    with pytest.raises(ValueError):
        await dao.update(db_session, n.id, fields={})


async def test_delete_by_id_removes_record(db_session, make_user):
    user = await make_user()
    n = await _make_news(db_session, user)
    dao = IndustryNewsDAO()
    rc = await dao.delete_by_id(db_session, n.id)
    assert rc == 1
    assert await dao.get_by_id(db_session, n.id) is None


async def test_delete_missing_returns_zero(db_session):
    dao = IndustryNewsDAO()
    rc = await dao.delete_by_id(db_session, uuid4())
    assert rc == 0


# ─────────────── NewsNodeLinkDAO ───────────────


async def test_link_create_and_get_by_pair(db_session, make_project, make_node, make_user):
    user, proj = await make_project()
    node = await make_node(proj.id, name="x")
    n = await _make_news(db_session, user)
    dao = NewsNodeLinkDAO()
    link = await dao.create(
        db_session, NewsNodeLink(news_id=n.id, node_id=node.id, linked_by=user.id)
    )
    assert link.id is not None
    got = await dao.get_by_pair(db_session, n.id, node.id)
    assert got is not None
    assert got.id == link.id


async def test_link_get_by_pair_missing_returns_none(db_session):
    dao = NewsNodeLinkDAO()
    assert await dao.get_by_pair(db_session, uuid4(), uuid4()) is None


async def test_link_list_by_news_returns_all_links(db_session, make_project, make_node, make_user):
    user, proj = await make_project()
    node1 = await make_node(proj.id, name="a")
    node2 = await make_node(proj.id, name="b")
    n = await _make_news(db_session, user)
    dao = NewsNodeLinkDAO()
    await dao.create(db_session, NewsNodeLink(news_id=n.id, node_id=node1.id, linked_by=user.id))
    await dao.create(db_session, NewsNodeLink(news_id=n.id, node_id=node2.id, linked_by=user.id))
    links = await dao.list_by_news(db_session, n.id)
    assert len(links) == 2


async def test_link_delete_by_pair_removes_one(db_session, make_project, make_node, make_user):
    user, proj = await make_project()
    node = await make_node(proj.id, name="x")
    n = await _make_news(db_session, user)
    dao = NewsNodeLinkDAO()
    await dao.create(db_session, NewsNodeLink(news_id=n.id, node_id=node.id, linked_by=user.id))
    rc = await dao.delete_by_pair(db_session, n.id, node.id)
    assert rc == 1
    assert await dao.get_by_pair(db_session, n.id, node.id) is None


async def test_link_delete_missing_returns_zero(db_session):
    dao = NewsNodeLinkDAO()
    rc = await dao.delete_by_pair(db_session, uuid4(), uuid4())
    assert rc == 0


async def test_link_cross_project_node_allowed(db_session, make_project, make_node, make_user):
    """全局动态可关联任意 node（design §1 灰区 2）：node 跨项目不阻挡 DAO 创建。

    DAO 层不校验 node 归属 project；service 层仅校验 node 存在。
    """
    user_a, proj_a = await make_project(name_suffix="-A")
    user_b, proj_b = await make_project(name_suffix="-B")
    node_b = await make_node(proj_b.id, name="b-node")
    n = await _make_news(db_session, user_a)
    dao = NewsNodeLinkDAO()
    link = await dao.create(
        db_session, NewsNodeLink(news_id=n.id, node_id=node_b.id, linked_by=user_a.id)
    )
    assert link.id is not None
