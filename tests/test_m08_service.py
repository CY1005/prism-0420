"""M08 子片 3 — ModuleRelationService 测试。

覆盖 design §6 业务规则 + §10 activity_log + §13 ErrorCode +
R-X2 第四真注入（双向 + delete 语义）。
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from api.errors.exceptions import (
    RelationDuplicateError,
    RelationNodeNotInProjectError,
    RelationNotFoundError,
    RelationSelfLoopError,
)
from api.services.module_relation_service import ModuleRelationService


@pytest.fixture
def svc():
    return ModuleRelationService()


# ─────────────── M08-SVC-T1 create golden + 边界 ───────────────


async def test_svc_create_golden(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    n1, n2 = await make_node(proj.id, name="A"), await make_node(proj.id, name="B")
    r = await svc.create_relation(
        db_session,
        project_id=proj.id,
        source_node_id=n1.id,
        target_node_id=n2.id,
        relation_type="depends_on",
        notes="A depends on B",
        actor_user_id=user.id,
    )
    assert r.id is not None
    assert r.notes == "A depends on B"


async def test_svc_create_self_loop_raises(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    n1 = await make_node(proj.id, name="A")
    with pytest.raises(RelationSelfLoopError):
        await svc.create_relation(
            db_session,
            project_id=proj.id,
            source_node_id=n1.id,
            target_node_id=n1.id,
            relation_type="depends_on",
            actor_user_id=user.id,
        )


async def test_svc_create_cross_project_node_raises(db_session, svc, make_project, make_node):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    nB = await make_node(projB.id, name="B")
    with pytest.raises(RelationNodeNotInProjectError):
        # 试图在 projA 内创建跨项目关联
        await svc.create_relation(
            db_session,
            project_id=projA.id,
            source_node_id=nA.id,
            target_node_id=nB.id,
            relation_type="depends_on",
            actor_user_id=user.id,
        )


async def test_svc_create_duplicate_triple_raises(db_session, svc, make_project, make_node):
    """A9 race 转换：UNIQUE(source, target, type) → RelationDuplicateError。"""
    user, proj = await make_project()
    n1, n2 = await make_node(proj.id, name="A"), await make_node(proj.id, name="B")
    await svc.create_relation(
        db_session,
        project_id=proj.id,
        source_node_id=n1.id,
        target_node_id=n2.id,
        relation_type="depends_on",
        actor_user_id=user.id,
    )
    with pytest.raises(RelationDuplicateError):
        await svc.create_relation(
            db_session,
            project_id=proj.id,
            source_node_id=n1.id,
            target_node_id=n2.id,
            relation_type="depends_on",
            actor_user_id=user.id,
        )


# ─────────────── M08-SVC-T2 read ───────────────


async def test_svc_list_by_project(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    n1, n2 = await make_node(proj.id, name="A"), await make_node(proj.id, name="B")
    await svc.create_relation(
        db_session,
        project_id=proj.id,
        source_node_id=n1.id,
        target_node_id=n2.id,
        relation_type="depends_on",
        actor_user_id=user.id,
    )
    rows = await svc.list_by_project(db_session, project_id=proj.id)
    assert len(rows) == 1


async def test_svc_list_by_node_bidirectional(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    n1, n2, n3 = (
        await make_node(proj.id, name="A"),
        await make_node(proj.id, name="B"),
        await make_node(proj.id, name="C"),
    )
    await svc.create_relation(
        db_session,
        project_id=proj.id,
        source_node_id=n1.id,
        target_node_id=n2.id,
        relation_type="depends_on",
        actor_user_id=user.id,
    )
    await svc.create_relation(
        db_session,
        project_id=proj.id,
        source_node_id=n3.id,
        target_node_id=n1.id,
        relation_type="related_to",
        actor_user_id=user.id,
    )
    rows = await svc.list_by_node(db_session, project_id=proj.id, node_id=n1.id)
    assert len(rows) == 2


async def test_svc_get_by_id_not_found_raises(db_session, svc, make_project):
    _, proj = await make_project()
    with pytest.raises(RelationNotFoundError):
        await svc.get_by_id(db_session, project_id=proj.id, relation_id=uuid4())


async def test_svc_search_by_keyword(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    n1, n2 = await make_node(proj.id, name="A"), await make_node(proj.id, name="B")
    await svc.create_relation(
        db_session,
        project_id=proj.id,
        source_node_id=n1.id,
        target_node_id=n2.id,
        relation_type="depends_on",
        notes="performance critical",
        actor_user_id=user.id,
    )
    rows = await svc.search_by_keyword(db_session, project_id=proj.id, query="performance")
    assert len(rows) == 1


# ─────────────── M08-SVC-T3 update_notes / delete_relation ───────────────


async def test_svc_update_notes(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    n1, n2 = await make_node(proj.id, name="A"), await make_node(proj.id, name="B")
    r = await svc.create_relation(
        db_session,
        project_id=proj.id,
        source_node_id=n1.id,
        target_node_id=n2.id,
        relation_type="depends_on",
        notes="orig",
        actor_user_id=user.id,
    )
    updated = await svc.update_notes(
        db_session,
        project_id=proj.id,
        relation_id=r.id,
        notes="new",
        actor_user_id=user.id,
    )
    assert updated.notes == "new"


async def test_svc_delete_relation(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    n1, n2 = await make_node(proj.id, name="A"), await make_node(proj.id, name="B")
    r = await svc.create_relation(
        db_session,
        project_id=proj.id,
        source_node_id=n1.id,
        target_node_id=n2.id,
        relation_type="depends_on",
        actor_user_id=user.id,
    )
    await svc.delete_relation(
        db_session, project_id=proj.id, relation_id=r.id, actor_user_id=user.id
    )
    with pytest.raises(RelationNotFoundError):
        await svc.get_by_id(db_session, project_id=proj.id, relation_id=r.id)


# ─────────────── M08-SVC-T4 R-X2 delete_by_node_id 第四真注入 ───────────────


async def test_svc_delete_by_node_id_bidirectional(db_session, svc, make_project, make_node):
    """**R-X2 第四真注入**：双向 DELETE + N 条 delete activity_log。"""
    user, proj = await make_project()
    n1, n2, n3 = (
        await make_node(proj.id, name="A"),
        await make_node(proj.id, name="B"),
        await make_node(proj.id, name="C"),
    )
    r1 = await svc.create_relation(
        db_session,
        project_id=proj.id,
        source_node_id=n1.id,
        target_node_id=n2.id,
        relation_type="depends_on",
        actor_user_id=user.id,
    )
    r2 = await svc.create_relation(
        db_session,
        project_id=proj.id,
        source_node_id=n3.id,
        target_node_id=n1.id,
        relation_type="related_to",
        actor_user_id=user.id,
    )
    r3 = await svc.create_relation(
        db_session,
        project_id=proj.id,
        source_node_id=n2.id,
        target_node_id=n3.id,
        relation_type="conflicts_with",
        actor_user_id=user.id,
    )
    r1_id, r2_id, r3_id = r1.id, r2.id, r3.id

    await svc.delete_by_node_id(db_session, n1.id, proj.id, user.id)

    res = await db_session.execute(
        text("SELECT id FROM module_relations WHERE id IN (:r1, :r2, :r3)"),
        {"r1": r1_id, "r2": r2_id, "r3": r3_id},
    )
    remaining = {row[0] for row in res.fetchall()}
    assert remaining == {r3_id}, "n1 出向+入向 2 条删除，n2→n3 仍存"


async def test_svc_delete_by_node_id_empty_no_op(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    await svc.delete_by_node_id(db_session, node.id, proj.id, user.id)


async def test_svc_delete_by_node_id_propagates_write_event_exception(
    db_session, svc, make_project, make_node, monkeypatch
):
    """R1-C P1-02 范式（M04/M06/M07 同款）：write_event 异常向上传播。"""
    user, proj = await make_project()
    n1, n2 = await make_node(proj.id, name="A"), await make_node(proj.id, name="B")
    await svc.create_relation(
        db_session,
        project_id=proj.id,
        source_node_id=n1.id,
        target_node_id=n2.id,
        relation_type="depends_on",
        actor_user_id=user.id,
    )

    async def _boom(**kwargs):
        raise RuntimeError("simulated write_event failure")

    monkeypatch.setattr("api.services.module_relation_service.write_event", _boom)
    with pytest.raises(RuntimeError, match="simulated write_event failure"):
        await svc.delete_by_node_id(db_session, n1.id, proj.id, user.id)
