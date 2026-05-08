"""M14 子片 3 — IndustryNewsService 单元测试。

覆盖 design §6 / §8 / §10 / §13：
- create / update / delete / list / get / list_by_node
- _check_news_owner_or_admin（owner / non-owner 403 / platform_admin 豁免）
- node 存在校验（不存在 404 / 跨项目允许）
- link / unlink + UNIQUE 并发 → NewsLinkDuplicateError 409（M05 P1-01 范式）
- write_event 异常传播测试（M04+ 范式 / 元教训防御 actionable 主动复制）
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from api.errors.exceptions import (
    NewsForbiddenError,
    NewsLinkDuplicateError,
    NewsLinkNotFoundError,
    NewsNotFoundError,
    NotFoundError,
)
from api.models.user import UserRole
from api.services.industry_news_service import IndustryNewsService

# ─────────────── helpers ───────────────


async def _svc() -> IndustryNewsService:
    return IndustryNewsService()


# ─────────────── create ───────────────


async def test_create_news_persists_with_defaults(db_session, make_user):
    user = await make_user()
    svc = await _svc()
    n = await svc.create_news(db_session, actor_user_id=user.id, title="AI 监管新规", tags=["AI"])
    assert n.id is not None
    assert n.source_type == "manual"
    assert n.created_by == user.id
    assert n.updated_by == user.id
    assert n.tags == ["AI"]


async def test_create_news_writes_activity_log(db_session, make_user, monkeypatch):
    """write_event 调用契约：M14 全局豁免传 project_id=None + action_type='create' + summary 含 title。"""
    import api.services.industry_news_service as mod

    captured: list[dict] = []

    async def fake(**kwargs):
        captured.append(kwargs)

    monkeypatch.setattr(mod, "write_event", fake)
    user = await make_user()
    svc = await _svc()
    await svc.create_news(db_session, actor_user_id=user.id, title="Quantum")
    assert len(captured) == 1
    ev = captured[0]
    assert ev["project_id"] is None  # M14 全局豁免
    assert ev["action_type"] == "create"
    assert ev["target_type"] == "industry_news"
    assert "Quantum" in ev["summary"]


async def test_create_news_propagates_write_event_failure(db_session, make_user, monkeypatch):
    """元教训：write_event 异常必须向上传播（M04+ 范式）。"""
    import api.services.industry_news_service as mod

    async def boom(**kwargs):
        raise RuntimeError("activity log failed")

    monkeypatch.setattr(mod, "write_event", boom)
    user = await make_user()
    svc = await _svc()
    with pytest.raises(RuntimeError):
        await svc.create_news(db_session, actor_user_id=user.id, title="x")


# ─────────────── get / list ───────────────


async def test_get_news_not_found(db_session):
    svc = await _svc()
    with pytest.raises(NewsNotFoundError):
        await svc.get_news(db_session, news_id=uuid4())


async def test_list_news_returns_pagination(db_session, make_user):
    user = await make_user()
    svc = await _svc()
    for i in range(3):
        await svc.create_news(db_session, actor_user_id=user.id, title=f"n{i}")
    items, total = await svc.list_news(db_session, page=1, page_size=2)
    assert len(items) == 2
    assert total >= 3


async def test_list_news_by_node(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="x")
    svc = await _svc()
    n = await svc.create_news(db_session, actor_user_id=user.id, title="t1")
    await svc.link_node(
        db_session,
        actor_user_id=user.id,
        actor_role=UserRole.USER.value,
        news_id=n.id,
        node_id=node.id,
    )
    items = await svc.list_news_by_node(db_session, node_id=node.id)
    assert len(items) == 1


# ─────────────── update / delete 权限 ───────────────


async def test_update_news_by_owner_succeeds(db_session, make_user):
    user = await make_user()
    svc = await _svc()
    n = await svc.create_news(db_session, actor_user_id=user.id, title="old")
    fresh = await svc.update_news(
        db_session,
        actor_user_id=user.id,
        actor_role=UserRole.USER.value,
        news_id=n.id,
        fields={"title": "new"},
    )
    assert fresh.title == "new"
    assert fresh.updated_by == user.id


async def test_update_news_by_non_owner_returns_403(db_session, make_user):
    owner = await make_user()
    other = await make_user()
    svc = await _svc()
    n = await svc.create_news(db_session, actor_user_id=owner.id, title="x")
    with pytest.raises(NewsForbiddenError):
        await svc.update_news(
            db_session,
            actor_user_id=other.id,
            actor_role=UserRole.USER.value,
            news_id=n.id,
            fields={"title": "hijack"},
        )


async def test_update_news_by_platform_admin_succeeds(db_session, make_user):
    """platform_admin 豁免 owner 校验（design §8）。"""
    owner = await make_user()
    admin = await make_user(role=UserRole.PLATFORM_ADMIN.value)
    svc = await _svc()
    n = await svc.create_news(db_session, actor_user_id=owner.id, title="old")
    fresh = await svc.update_news(
        db_session,
        actor_user_id=admin.id,
        actor_role=UserRole.PLATFORM_ADMIN.value,
        news_id=n.id,
        fields={"title": "moderated"},
    )
    assert fresh.title == "moderated"


async def test_update_news_ignores_source_type_change(db_session, make_user):
    """design §3 灰区 1：source_type 不可被 update 修改。"""
    user = await make_user()
    svc = await _svc()
    n = await svc.create_news(db_session, actor_user_id=user.id, title="t")
    fresh = await svc.update_news(
        db_session,
        actor_user_id=user.id,
        actor_role=UserRole.USER.value,
        news_id=n.id,
        fields={"source_type": "rss", "title": "t2"},
    )
    assert fresh.source_type == "manual"
    assert fresh.title == "t2"


async def test_delete_news_by_non_owner_returns_403(db_session, make_user):
    owner = await make_user()
    other = await make_user()
    svc = await _svc()
    n = await svc.create_news(db_session, actor_user_id=owner.id, title="t")
    with pytest.raises(NewsForbiddenError):
        await svc.delete_news(
            db_session,
            actor_user_id=other.id,
            actor_role=UserRole.USER.value,
            news_id=n.id,
        )


async def test_delete_news_by_owner_succeeds(db_session, make_user):
    user = await make_user()
    svc = await _svc()
    n = await svc.create_news(db_session, actor_user_id=user.id, title="t")
    await svc.delete_news(
        db_session,
        actor_user_id=user.id,
        actor_role=UserRole.USER.value,
        news_id=n.id,
    )
    with pytest.raises(NewsNotFoundError):
        await svc.get_news(db_session, news_id=n.id)


async def test_delete_news_by_platform_admin_succeeds(db_session, make_user):
    owner = await make_user()
    admin = await make_user(role=UserRole.PLATFORM_ADMIN.value)
    svc = await _svc()
    n = await svc.create_news(db_session, actor_user_id=owner.id, title="t")
    await svc.delete_news(
        db_session,
        actor_user_id=admin.id,
        actor_role=UserRole.PLATFORM_ADMIN.value,
        news_id=n.id,
    )


async def test_delete_missing_news_returns_404(db_session, make_user):
    user = await make_user()
    svc = await _svc()
    with pytest.raises(NewsNotFoundError):
        await svc.delete_news(
            db_session,
            actor_user_id=user.id,
            actor_role=UserRole.USER.value,
            news_id=uuid4(),
        )


# ─────────────── link / unlink ───────────────


async def test_link_node_succeeds(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="x")
    svc = await _svc()
    n = await svc.create_news(db_session, actor_user_id=user.id, title="t")
    link = await svc.link_node(
        db_session,
        actor_user_id=user.id,
        actor_role=UserRole.USER.value,
        news_id=n.id,
        node_id=node.id,
    )
    assert link.news_id == n.id
    assert link.node_id == node.id


async def test_link_node_missing_node_returns_404(db_session, make_user):
    user = await make_user()
    svc = await _svc()
    n = await svc.create_news(db_session, actor_user_id=user.id, title="t")
    with pytest.raises(NotFoundError):
        await svc.link_node(
            db_session,
            actor_user_id=user.id,
            actor_role=UserRole.USER.value,
            news_id=n.id,
            node_id=uuid4(),
        )


async def test_link_node_cross_project_allowed(db_session, make_project, make_node):
    """design §1 灰区 2：全局动态可关联跨项目 node。"""
    user_a, _proj_a = await make_project(name_suffix="-A")
    _user_b, proj_b = await make_project(name_suffix="-B")
    node_b = await make_node(proj_b.id, name="b-node")
    svc = await _svc()
    n = await svc.create_news(db_session, actor_user_id=user_a.id, title="t")
    link = await svc.link_node(
        db_session,
        actor_user_id=user_a.id,
        actor_role=UserRole.USER.value,
        news_id=n.id,
        node_id=node_b.id,
    )
    assert link.id is not None


async def test_link_node_duplicate_returns_409(db_session, make_project, make_node):
    """M05 P1-01 范式延续：UNIQUE(news_id, node_id) → NewsLinkDuplicateError（区分约束名）。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="x")
    svc = await _svc()
    n = await svc.create_news(db_session, actor_user_id=user.id, title="t")
    await svc.link_node(
        db_session,
        actor_user_id=user.id,
        actor_role=UserRole.USER.value,
        news_id=n.id,
        node_id=node.id,
    )
    with pytest.raises(NewsLinkDuplicateError):
        await svc.link_node(
            db_session,
            actor_user_id=user.id,
            actor_role=UserRole.USER.value,
            news_id=n.id,
            node_id=node.id,
        )


async def test_link_node_missing_news_returns_404(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="x")
    svc = await _svc()
    with pytest.raises(NewsNotFoundError):
        await svc.link_node(
            db_session,
            actor_user_id=user.id,
            actor_role=UserRole.USER.value,
            news_id=uuid4(),
            node_id=node.id,
        )


async def test_unlink_node_succeeds(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="x")
    svc = await _svc()
    n = await svc.create_news(db_session, actor_user_id=user.id, title="t")
    await svc.link_node(
        db_session,
        actor_user_id=user.id,
        actor_role=UserRole.USER.value,
        news_id=n.id,
        node_id=node.id,
    )
    await svc.unlink_node(db_session, actor_user_id=user.id, news_id=n.id, node_id=node.id)


async def test_unlink_missing_link_returns_404(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="x")
    svc = await _svc()
    n = await svc.create_news(db_session, actor_user_id=user.id, title="t")
    with pytest.raises(NewsLinkNotFoundError):
        await svc.unlink_node(db_session, actor_user_id=user.id, news_id=n.id, node_id=node.id)


async def test_unlink_missing_news_returns_404(db_session, make_user):
    user = await make_user()
    svc = await _svc()
    with pytest.raises(NewsNotFoundError):
        await svc.unlink_node(db_session, actor_user_id=user.id, news_id=uuid4(), node_id=uuid4())


async def test_link_propagates_write_event_failure(
    db_session, make_project, make_node, monkeypatch
):
    """元教训：link write_event 异常必须向上传播（M04+ 范式 / link 端点 3 端点全覆盖）。"""
    import api.services.industry_news_service as mod

    async def boom(**kwargs):
        if kwargs.get("action_type") == "link":
            raise RuntimeError("activity log failed")
        # create / update / delete 不触发，本测试只验 link 路径

    monkeypatch.setattr(mod, "write_event", boom)
    user, proj = await make_project()
    node = await make_node(proj.id, name="x")
    svc = await _svc()
    # create_news 走 monkeypatched write_event 的"create"分支被吞掉 → 跳过 patch
    monkeypatch.undo()
    n = await svc.create_news(db_session, actor_user_id=user.id, title="t")
    monkeypatch.setattr(mod, "write_event", boom)
    with pytest.raises(RuntimeError):
        await svc.link_node(
            db_session,
            actor_user_id=user.id,
            actor_role=UserRole.USER.value,
            news_id=n.id,
            node_id=node.id,
        )
