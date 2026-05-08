"""M06 子片 3 — CompetitorService 测试。

覆盖 design §6 service 业务规则 + §10 activity_log + §13 ErrorCode +
R-X2 第二真注入 (delete_by_node_id 4 参) + M18 baseline-patch get_for_embedding。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from api.errors.exceptions import (
    CompetitorCrossProjectError,
    CompetitorNotFoundError,
    CompetitorRefDuplicateError,
    CompetitorRefNotFoundError,
)
from api.services.competitor_service import CompetitorService


@pytest.fixture
def svc():
    return CompetitorService()


# ─────────────── M06-SVC-T1 Competitor CRUD ───────────────


async def test_svc_create_competitor(db_session, svc, make_project):
    user, proj = await make_project()
    c = await svc.create_competitor(
        db_session,
        project_id=proj.id,
        display_name="Notion",
        website_url="https://notion.so",
        description="all-in-one",
        actor_user_id=user.id,
    )
    assert c.id is not None
    assert c.display_name == "Notion"


async def test_svc_get_competitor_not_found(db_session, svc, make_project):
    _, proj = await make_project()
    with pytest.raises(CompetitorNotFoundError):
        await svc.get_competitor(db_session, project_id=proj.id, competitor_id=uuid4())


async def test_svc_get_competitor_blocks_cross_tenant(db_session, svc, make_project):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    cA = await svc.create_competitor(
        db_session,
        project_id=projA.id,
        display_name="X",
        actor_user_id=user.id,
    )
    with pytest.raises(CompetitorNotFoundError):
        await svc.get_competitor(db_session, project_id=projB.id, competitor_id=cA.id)


async def test_svc_update_competitor(db_session, svc, make_project):
    user, proj = await make_project()
    c = await svc.create_competitor(
        db_session, project_id=proj.id, display_name="Old", actor_user_id=user.id
    )
    updated = await svc.update_competitor(
        db_session,
        project_id=proj.id,
        competitor_id=c.id,
        display_name="New",
        actor_user_id=user.id,
    )
    assert updated.display_name == "New"


async def test_svc_update_competitor_no_op_returns_existing(db_session, svc, make_project):
    user, proj = await make_project()
    c = await svc.create_competitor(
        db_session, project_id=proj.id, display_name="X", actor_user_id=user.id
    )
    result = await svc.update_competitor(
        db_session,
        project_id=proj.id,
        competitor_id=c.id,
        actor_user_id=user.id,
    )
    assert result.id == c.id


async def test_svc_delete_competitor(db_session, svc, make_project):
    user, proj = await make_project()
    c = await svc.create_competitor(
        db_session, project_id=proj.id, display_name="X", actor_user_id=user.id
    )
    await svc.delete_competitor(
        db_session,
        project_id=proj.id,
        competitor_id=c.id,
        actor_user_id=user.id,
    )
    with pytest.raises(CompetitorNotFoundError):
        await svc.get_competitor(db_session, project_id=proj.id, competitor_id=c.id)


async def test_svc_list_competitors(db_session, svc, make_project):
    user, proj = await make_project()
    await svc.create_competitor(
        db_session, project_id=proj.id, display_name="A", actor_user_id=user.id
    )
    await svc.create_competitor(
        db_session, project_id=proj.id, display_name="B", actor_user_id=user.id
    )
    rows = await svc.list_competitors(db_session, project_id=proj.id)
    assert len(rows) == 2


# ─────────────── M06-SVC-T2 CompetitorRef CRUD ───────────────


async def test_svc_create_ref_golden(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    c = await svc.create_competitor(
        db_session, project_id=proj.id, display_name="X", actor_user_id=user.id
    )

    ref = await svc.create_ref(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        competitor_id=c.id,
        actor_user_id=user.id,
        feature_coverage="覆盖",
    )
    assert ref.id is not None
    assert ref.feature_coverage == "覆盖"


async def test_svc_create_ref_duplicate_raises(db_session, svc, make_project, make_node):
    """A9 同款 race：UNIQUE(node, competitor) 命中 → CompetitorRefDuplicateError。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    c = await svc.create_competitor(
        db_session, project_id=proj.id, display_name="X", actor_user_id=user.id
    )
    await svc.create_ref(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        competitor_id=c.id,
        actor_user_id=user.id,
    )
    with pytest.raises(CompetitorRefDuplicateError):
        await svc.create_ref(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            competitor_id=c.id,
            actor_user_id=user.id,
        )


async def test_svc_create_ref_cross_project_competitor_raises(
    db_session, svc, make_project, make_node
):
    """竞品属于他项目 → CompetitorCrossProjectError (422)。"""
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nB = await make_node(projB.id, name="B")
    cA = await svc.create_competitor(
        db_session, project_id=projA.id, display_name="X", actor_user_id=user.id
    )

    with pytest.raises(CompetitorCrossProjectError):
        await svc.create_ref(
            db_session,
            project_id=projB.id,
            node_id=nB.id,
            competitor_id=cA.id,  # A 项目的竞品
            actor_user_id=user.id,
        )


async def test_svc_create_ref_blocks_cross_tenant_node(db_session, svc, make_project, make_node):
    """节点不属于该 project → CompetitorRefNotFoundError 不暴露 forbidden。"""
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    cB = await svc.create_competitor(
        db_session, project_id=projB.id, display_name="X", actor_user_id=user.id
    )

    with pytest.raises(CompetitorRefNotFoundError):
        await svc.create_ref(
            db_session,
            project_id=projB.id,
            node_id=nA.id,
            competitor_id=cB.id,
            actor_user_id=user.id,
        )


async def test_svc_list_refs_by_node(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    c1 = await svc.create_competitor(
        db_session, project_id=proj.id, display_name="C1", actor_user_id=user.id
    )
    c2 = await svc.create_competitor(
        db_session, project_id=proj.id, display_name="C2", actor_user_id=user.id
    )
    await svc.create_ref(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        competitor_id=c1.id,
        actor_user_id=user.id,
    )
    await svc.create_ref(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        competitor_id=c2.id,
        actor_user_id=user.id,
    )
    rows = await svc.list_refs_by_node(db_session, project_id=proj.id, node_id=node.id)
    assert len(rows) == 2


async def test_svc_get_ref_wrong_node_raises(db_session, svc, make_project, make_node):
    """ref 存在但属于另一节点 → CompetitorRefNotFoundError。"""
    user, proj = await make_project()
    node1 = await make_node(proj.id, name="N1")
    node2 = await make_node(proj.id, name="N2")
    c = await svc.create_competitor(
        db_session, project_id=proj.id, display_name="X", actor_user_id=user.id
    )
    ref = await svc.create_ref(
        db_session,
        project_id=proj.id,
        node_id=node1.id,
        competitor_id=c.id,
        actor_user_id=user.id,
    )
    with pytest.raises(CompetitorRefNotFoundError):
        await svc.get_ref(db_session, project_id=proj.id, node_id=node2.id, ref_id=ref.id)


async def test_svc_update_ref(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    c = await svc.create_competitor(
        db_session, project_id=proj.id, display_name="X", actor_user_id=user.id
    )
    ref = await svc.create_ref(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        competitor_id=c.id,
        actor_user_id=user.id,
    )
    updated = await svc.update_ref(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        ref_id=ref.id,
        actor_user_id=user.id,
        feature_coverage="新",
    )
    assert updated.feature_coverage == "新"


async def test_svc_delete_ref(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    c = await svc.create_competitor(
        db_session, project_id=proj.id, display_name="X", actor_user_id=user.id
    )
    ref = await svc.create_ref(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        competitor_id=c.id,
        actor_user_id=user.id,
    )
    await svc.delete_ref(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        ref_id=ref.id,
        actor_user_id=user.id,
    )
    with pytest.raises(CompetitorRefNotFoundError):
        await svc.get_ref(db_session, project_id=proj.id, node_id=node.id, ref_id=ref.id)


# ─────────────── M06-SVC-T3 R-X2 delete_by_node_id ───────────────


async def test_svc_delete_by_node_id_clears_all_refs(db_session, svc, make_project, make_node):
    """R-X2 第二真注入：清节点下所有 refs + 每条独立 activity_log。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    c1 = await svc.create_competitor(
        db_session, project_id=proj.id, display_name="C1", actor_user_id=user.id
    )
    c2 = await svc.create_competitor(
        db_session, project_id=proj.id, display_name="C2", actor_user_id=user.id
    )
    await svc.create_ref(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        competitor_id=c1.id,
        actor_user_id=user.id,
    )
    await svc.create_ref(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        competitor_id=c2.id,
        actor_user_id=user.id,
    )

    await svc.delete_by_node_id(db_session, node.id, proj.id, user.id)
    rows = await svc.list_refs_by_node(db_session, project_id=proj.id, node_id=node.id)
    assert rows == []


async def test_svc_delete_by_node_id_empty_node_no_op(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    # 不抛 — empty 列表 noop
    await svc.delete_by_node_id(db_session, node.id, proj.id, user.id)


async def test_svc_delete_by_node_id_propagates_write_event_exception(
    db_session, svc, make_project, make_node, monkeypatch
):
    """R1-C P1-02 立修（M04 同款范式）：write_event 抛异常时不 catch-all，向上传播。

    docstring 声明的 R1-C P1-01 异常契约（不 catch-all 吞错）必须有 test-level 闭环，
    防 M15 升级 write_event 真 INSERT 时悄然引入 silent catch。
    """
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    c = await svc.create_competitor(
        db_session, project_id=proj.id, display_name="X", actor_user_id=user.id
    )
    await svc.create_ref(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        competitor_id=c.id,
        actor_user_id=user.id,
    )

    async def _boom(**kwargs):
        raise RuntimeError("simulated write_event failure")

    monkeypatch.setattr("api.services.competitor_service.write_event", _boom)

    with pytest.raises(RuntimeError, match="simulated write_event failure"):
        await svc.delete_by_node_id(db_session, node.id, proj.id, user.id)


# ─────────────── M06-SVC-T4 M18 baseline-patch get_for_embedding ───────────────


async def test_svc_get_for_embedding_concat_name_description(db_session, svc, make_project):
    """A6 A 路径：拼接 name + description；url 不参与（CY 决策 4）。"""
    user, proj = await make_project()
    c = await svc.create_competitor(
        db_session,
        project_id=proj.id,
        display_name="Notion",
        website_url="https://notion.so",  # 不应出现在 embedding text
        description="all-in-one workspace",
        actor_user_id=user.id,
    )
    text = await svc.get_for_embedding(db_session, c.id, proj.id)
    assert text is not None
    assert "Notion" in text
    assert "all-in-one" in text
    assert "https://notion.so" not in text, "url 不参与 embedding"


async def test_svc_get_for_embedding_no_description(db_session, svc, make_project):
    user, proj = await make_project()
    c = await svc.create_competitor(
        db_session, project_id=proj.id, display_name="Solo", actor_user_id=user.id
    )
    text = await svc.get_for_embedding(db_session, c.id, proj.id)
    assert text == "Solo"


async def test_svc_get_for_embedding_not_found_returns_none(db_session, svc, make_project):
    _, proj = await make_project()
    text = await svc.get_for_embedding(db_session, uuid4(), proj.id)
    assert text is None


# ─────────────── M11 sprint R-X1 batch_create_in_transaction smoke ───────────────


async def test_svc_batch_create_in_transaction_creates_multiple(db_session, svc, make_project):
    """M11 sprint 接通：M06 batch_create_in_transaction 服务于 R-X1 orchestrator。"""
    user, proj = await make_project()
    created = await svc.batch_create_in_transaction(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        competitors_data=[
            {"display_name": "Notion", "description": "all-in-one"},
            {"display_name": "Figma", "website_url": "https://figma.com"},
        ],
    )
    assert len(created) == 2
    names = {c.display_name for c in created}
    assert names == {"Notion", "Figma"}
