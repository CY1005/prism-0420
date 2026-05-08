"""M07 子片 2 — IssueDAO 测试。

覆盖 design §9 主查询模式 + tenant 过滤 + 多维过滤（category/status/node_id/tag）+
SELECT FOR UPDATE + R-X2 orphan_by_node_id（UPDATE SET NULL）。
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from api.dao.issue_dao import IssueDAO
from api.models.issue import Issue


@pytest.fixture
def dao():
    return IssueDAO()


async def _make_issue(
    db_session,
    *,
    user,
    project,
    node=None,
    category="bug",
    status="open",
    title="t",
    description="d",
    tags=None,
) -> Issue:
    i = Issue(
        project_id=project.id,
        node_id=node.id if node else None,
        category=category,
        status=status,
        title=title,
        description=description,
        tags=tags if tags is not None else [],
        created_by=user.id,
    )
    db_session.add(i)
    await db_session.flush()
    return i


# ─────────────── M07-DAO-T1 list_by_project + 多维过滤 ───────────────


async def test_dao_list_by_project_basic(db_session, dao, make_project):
    user, proj = await make_project()
    await _make_issue(db_session, user=user, project=proj, title="i1")
    await _make_issue(db_session, user=user, project=proj, title="i2")
    rows = await dao.list_by_project(db_session, proj.id)
    assert len(rows) == 2


async def test_dao_list_by_project_filter_category(db_session, dao, make_project):
    user, proj = await make_project()
    await _make_issue(db_session, user=user, project=proj, category="bug")
    await _make_issue(db_session, user=user, project=proj, category="tech_debt")
    rows = await dao.list_by_project(db_session, proj.id, category="bug")
    assert len(rows) == 1
    assert rows[0].category == "bug"


async def test_dao_list_by_project_filter_status(db_session, dao, make_project):
    user, proj = await make_project()
    await _make_issue(db_session, user=user, project=proj, status="open")
    await _make_issue(db_session, user=user, project=proj, status="resolved")
    rows = await dao.list_by_project(db_session, proj.id, status="open")
    assert len(rows) == 1


async def test_dao_list_by_project_filter_node_id(db_session, dao, make_project, make_node):
    user, proj = await make_project()
    n1 = await make_node(proj.id, name="N1")
    n2 = await make_node(proj.id, name="N2")
    await _make_issue(db_session, user=user, project=proj, node=n1)
    await _make_issue(db_session, user=user, project=proj, node=n2)
    await _make_issue(db_session, user=user, project=proj, node=None)  # 游离

    rows = await dao.list_by_project(db_session, proj.id, node_id=n1.id)
    assert len(rows) == 1


async def test_dao_list_by_project_filter_tag(db_session, dao, make_project):
    """JSONB tag 查询：tags @> [tag]。"""
    user, proj = await make_project()
    await _make_issue(db_session, user=user, project=proj, tags=["p0", "regression"])
    await _make_issue(db_session, user=user, project=proj, tags=["p1"])
    await _make_issue(db_session, user=user, project=proj, tags=[])

    rows = await dao.list_by_project(db_session, proj.id, tag="p0")
    assert len(rows) == 1
    assert "p0" in rows[0].tags


async def test_dao_list_by_project_isolates_tenants(db_session, dao, make_project):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    await _make_issue(db_session, user=user, project=projA, title="A")
    await _make_issue(db_session, user=user, project=projB, title="B")

    rowsA = await dao.list_by_project(db_session, projA.id)
    assert len(rowsA) == 1


async def test_dao_list_by_project_respects_limit(db_session, dao, make_project):
    user, proj = await make_project()
    for i in range(5):
        await _make_issue(db_session, user=user, project=proj, title=f"i{i}")
    rows = await dao.list_by_project(db_session, proj.id, limit=3)
    assert len(rows) == 3


# ─────────────── M07-DAO-T2 get_by_id + cross-tenant ───────────────


async def test_dao_get_by_id_in_tenant(db_session, dao, make_project):
    user, proj = await make_project()
    i = await _make_issue(db_session, user=user, project=proj)
    found = await dao.get_by_id(db_session, i.id, proj.id)
    assert found is not None and found.id == i.id


async def test_dao_get_by_id_blocks_cross_tenant(db_session, dao, make_project):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    i = await _make_issue(db_session, user=user, project=projA)
    found = await dao.get_by_id(db_session, i.id, projB.id)
    assert found is None


async def test_dao_get_by_id_missing_returns_none(db_session, dao, make_project):
    _, proj = await make_project()
    assert await dao.get_by_id(db_session, uuid4(), proj.id) is None


# ─────────────── M07-DAO-T3 get_for_update（SELECT FOR UPDATE）───────────────


async def test_dao_get_for_update_returns_locked_row(db_session, dao, make_project):
    """SELECT FOR UPDATE 应正常返回行（同事务内不会自锁）。"""
    user, proj = await make_project()
    i = await _make_issue(db_session, user=user, project=proj)
    locked = await dao.get_for_update(db_session, i.id, proj.id)
    assert locked is not None and locked.id == i.id


# ─────────────── M07-DAO-T4 count_by_project ───────────────


async def test_dao_count_by_project(db_session, dao, make_project):
    user, proj = await make_project()
    await _make_issue(db_session, user=user, project=proj, status="open")
    await _make_issue(db_session, user=user, project=proj, status="open")
    await _make_issue(db_session, user=user, project=proj, status="resolved")
    assert await dao.count_by_project(db_session, proj.id) == 3
    assert await dao.count_by_project(db_session, proj.id, status="open") == 2


# ─────────────── M07-DAO-T5 update / delete ───────────────


async def test_dao_update_changes_fields(db_session, dao, make_project):
    user, proj = await make_project()
    i = await _make_issue(db_session, user=user, project=proj, title="orig")
    rows = await dao.update(
        db_session, i.id, proj.id, fields={"title": "new", "status": "in_progress"}
    )
    assert rows == 1
    await db_session.refresh(i)
    assert i.title == "new"
    assert i.status == "in_progress"


async def test_dao_update_blocks_cross_tenant(db_session, dao, make_project):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    i = await _make_issue(db_session, user=user, project=projA)
    rows = await dao.update(db_session, i.id, projB.id, fields={"title": "hack"})
    assert rows == 0


async def test_dao_update_empty_fields_raises(db_session, dao):
    with pytest.raises(ValueError):
        await dao.update(db_session, uuid4(), uuid4(), fields={})


async def test_dao_delete_by_id(db_session, dao, make_project):
    user, proj = await make_project()
    i = await _make_issue(db_session, user=user, project=proj)
    rows = await dao.delete_by_id(db_session, i.id, proj.id)
    assert rows == 1
    assert await dao.get_by_id(db_session, i.id, proj.id) is None


async def test_dao_delete_by_id_blocks_cross_tenant(db_session, dao, make_project):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    i = await _make_issue(db_session, user=user, project=projA)
    rows = await dao.delete_by_id(db_session, i.id, projB.id)
    assert rows == 0
    assert await dao.get_by_id(db_session, i.id, projA.id) is not None


# ─────────────── M07-DAO-T6 R-X2 orphan_by_node_id ───────────────


async def test_dao_list_by_node_for_orphan(db_session, dao, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    await _make_issue(db_session, user=user, project=proj, node=node)
    await _make_issue(db_session, user=user, project=proj, node=node)
    await _make_issue(db_session, user=user, project=proj, node=None)  # 游离不应返回

    rows = await dao.list_by_node_for_orphan(db_session, node.id, proj.id)
    assert len(rows) == 2


async def test_dao_orphan_by_node_id_sets_null(db_session, dao, make_project, make_node):
    """**R-X2 orphan 关键测试**：UPDATE node_id = NULL（不是 DELETE）。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    i1 = await _make_issue(db_session, user=user, project=proj, node=node)
    i2 = await _make_issue(db_session, user=user, project=proj, node=node)
    other = await _make_issue(db_session, user=user, project=proj, node=None)
    # 提前抓 ID（expire 后 ORM access 会触发 IO）
    i1_id, i2_id, other_id = i1.id, i2.id, other.id

    rows = await dao.orphan_by_node_id(db_session, node.id, proj.id)
    assert rows == 2

    db_session.expire_all()
    res = await db_session.execute(select(Issue).where(Issue.id.in_([i1_id, i2_id, other_id])))
    found = {r.id: r for r in res.scalars().all()}
    assert found[i1_id].node_id is None, "i1 应被 orphan"
    assert found[i2_id].node_id is None, "i2 应被 orphan"
    assert found[other_id].node_id is None, "other 原本就游离"
    assert len(found) == 3, "全部 issue 仍存在（不被删除）"


async def test_dao_orphan_by_node_id_blocks_cross_tenant(db_session, dao, make_project, make_node):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    iA = await _make_issue(db_session, user=user, project=projA, node=nA)
    iA_id, nA_id = iA.id, nA.id

    rows = await dao.orphan_by_node_id(db_session, nA_id, projB.id)
    assert rows == 0
    # 直 SQL 查 node_id 列（避免 ORM cache + expire 后 attr access 异步 IO 问题）
    from sqlalchemy import text

    result = await db_session.execute(
        text("SELECT node_id FROM issues WHERE id = :id"), {"id": iA_id}
    )
    node_id_after = result.scalar_one()
    assert node_id_after == nA_id, "B 项目不应能 orphan A 项目的 issue"
