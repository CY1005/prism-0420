"""M06 子片 2 — CompetitorDAO 测试。

覆盖 design §9 主查询模式 + tenant 过滤 + Competitor + CompetitorRef CRUD +
list_refs_by_node_for_delete (R-X2 用)。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from api.dao.competitor_dao import CompetitorDAO
from api.models.competitor import Competitor, CompetitorRef


@pytest.fixture
def dao():
    return CompetitorDAO()


async def _make_competitor(db_session, *, project, user, name="Notion") -> Competitor:
    c = Competitor(project_id=project.id, display_name=name, created_by=user.id)
    db_session.add(c)
    await db_session.flush()
    return c


async def _make_ref(db_session, *, project, node, competitor, user) -> CompetitorRef:
    ref = CompetitorRef(
        node_id=node.id,
        competitor_id=competitor.id,
        project_id=project.id,
        created_by=user.id,
    )
    db_session.add(ref)
    await db_session.flush()
    return ref


# ─────────────── M06-DAO-T1 list_by_project ───────────────


async def test_dao_list_by_project_orders_by_display_name(db_session, dao, make_project):
    user, proj = await make_project()
    await _make_competitor(db_session, project=proj, user=user, name="Zed")
    await _make_competitor(db_session, project=proj, user=user, name="Alpha")

    rows = await dao.list_by_project(db_session, proj.id)
    names = [r.display_name for r in rows]
    assert names == sorted(names), "ASC 排序"


async def test_dao_list_by_project_isolates_tenants(db_session, dao, make_project):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    await _make_competitor(db_session, project=projA, user=user, name="A1")
    await _make_competitor(db_session, project=projB, user=user, name="B1")

    rowsA = await dao.list_by_project(db_session, projA.id)
    assert len(rowsA) == 1 and rowsA[0].display_name == "A1"


# ─────────────── M06-DAO-T2 get_competitor_by_id ───────────────


async def test_dao_get_competitor_by_id_returns_in_tenant(db_session, dao, make_project):
    user, proj = await make_project()
    c = await _make_competitor(db_session, project=proj, user=user)
    found = await dao.get_competitor_by_id(db_session, c.id, proj.id)
    assert found is not None and found.id == c.id


async def test_dao_get_competitor_by_id_blocks_cross_tenant(db_session, dao, make_project):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    c = await _make_competitor(db_session, project=projA, user=user)
    found = await dao.get_competitor_by_id(db_session, c.id, projB.id)
    assert found is None


# ─────────────── M06-DAO-T3 update_competitor ───────────────


async def test_dao_update_competitor_changes_fields(db_session, dao, make_project):
    user, proj = await make_project()
    c = await _make_competitor(db_session, project=proj, user=user, name="orig")
    rows = await dao.update_competitor(
        db_session, c.id, proj.id, fields={"display_name": "new", "description": "d"}
    )
    assert rows == 1
    await db_session.refresh(c)
    assert c.display_name == "new"
    assert c.description == "d"


async def test_dao_update_competitor_blocks_cross_tenant(db_session, dao, make_project):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    c = await _make_competitor(db_session, project=projA, user=user)
    rows = await dao.update_competitor(db_session, c.id, projB.id, fields={"display_name": "hack"})
    assert rows == 0


async def test_dao_update_competitor_empty_fields_raises(db_session, dao):
    with pytest.raises(ValueError):
        await dao.update_competitor(db_session, uuid4(), uuid4(), fields={})


# ─────────────── M06-DAO-T4 delete_competitor + count_refs ───────────────


async def test_dao_delete_competitor_removes(db_session, dao, make_project):
    user, proj = await make_project()
    c = await _make_competitor(db_session, project=proj, user=user)
    rows = await dao.delete_competitor(db_session, c.id, proj.id)
    assert rows == 1
    assert await dao.get_competitor_by_id(db_session, c.id, proj.id) is None


async def test_dao_count_refs_by_competitor(db_session, dao, make_project, make_node):
    user, proj = await make_project()
    n1 = await make_node(proj.id, name="N1")
    n2 = await make_node(proj.id, name="N2")
    c = await _make_competitor(db_session, project=proj, user=user)
    await _make_ref(db_session, project=proj, node=n1, competitor=c, user=user)
    await _make_ref(db_session, project=proj, node=n2, competitor=c, user=user)

    assert await dao.count_refs_by_competitor(db_session, c.id, proj.id) == 2


async def test_dao_count_refs_blocks_cross_tenant(db_session, dao, make_project, make_node):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    cA = await _make_competitor(db_session, project=projA, user=user)
    await _make_ref(db_session, project=projA, node=nA, competitor=cA, user=user)
    assert await dao.count_refs_by_competitor(db_session, cA.id, projB.id) == 0


# ─────────────── M06-DAO-T5 list_refs_by_node ───────────────


async def test_dao_list_refs_by_node_returns_in_tenant(db_session, dao, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    c = await _make_competitor(db_session, project=proj, user=user)
    await _make_ref(db_session, project=proj, node=node, competitor=c, user=user)

    rows = await dao.list_refs_by_node(db_session, node.id, proj.id)
    assert len(rows) == 1


async def test_dao_list_refs_by_node_blocks_cross_tenant(db_session, dao, make_project, make_node):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    cA = await _make_competitor(db_session, project=projA, user=user)
    await _make_ref(db_session, project=projA, node=nA, competitor=cA, user=user)

    rowsCross = await dao.list_refs_by_node(db_session, nA.id, projB.id)
    assert rowsCross == []


# ─────────────── M06-DAO-T6 list_refs_by_node_for_delete (R-X2) ───────────────


async def test_dao_list_refs_for_delete(db_session, dao, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    c1 = await _make_competitor(db_session, project=proj, user=user, name="C1")
    c2 = await _make_competitor(db_session, project=proj, user=user, name="C2")
    await _make_ref(db_session, project=proj, node=node, competitor=c1, user=user)
    await _make_ref(db_session, project=proj, node=node, competitor=c2, user=user)

    rows = await dao.list_refs_by_node_for_delete(db_session, node.id, proj.id)
    assert len(rows) == 2
    assert {r.competitor_id for r in rows} == {c1.id, c2.id}


# ─────────────── M06-DAO-T7 get_ref_by_id ───────────────


async def test_dao_get_ref_by_id_returns_in_tenant(db_session, dao, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    c = await _make_competitor(db_session, project=proj, user=user)
    ref = await _make_ref(db_session, project=proj, node=node, competitor=c, user=user)

    found = await dao.get_ref_by_id(db_session, ref.id, proj.id)
    assert found is not None and found.id == ref.id


async def test_dao_get_ref_by_id_blocks_cross_tenant(db_session, dao, make_project, make_node):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    cA = await _make_competitor(db_session, project=projA, user=user)
    refA = await _make_ref(db_session, project=projA, node=nA, competitor=cA, user=user)

    assert await dao.get_ref_by_id(db_session, refA.id, projB.id) is None


# ─────────────── M06-DAO-T8 update_ref ───────────────


async def test_dao_update_ref(db_session, dao, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    c = await _make_competitor(db_session, project=proj, user=user)
    ref = await _make_ref(db_session, project=proj, node=node, competitor=c, user=user)

    rows = await dao.update_ref(
        db_session,
        ref.id,
        proj.id,
        fields={"feature_coverage": "全覆盖", "tech_approach": "新方案"},
    )
    assert rows == 1
    await db_session.refresh(ref)
    assert ref.feature_coverage == "全覆盖"


async def test_dao_update_ref_blocks_cross_tenant(db_session, dao, make_project, make_node):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    cA = await _make_competitor(db_session, project=projA, user=user)
    refA = await _make_ref(db_session, project=projA, node=nA, competitor=cA, user=user)

    rows = await dao.update_ref(db_session, refA.id, projB.id, fields={"feature_coverage": "hack"})
    assert rows == 0


# ─────────────── M06-DAO-T9 delete_ref ───────────────


async def test_dao_delete_ref(db_session, dao, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    c = await _make_competitor(db_session, project=proj, user=user)
    ref = await _make_ref(db_session, project=proj, node=node, competitor=c, user=user)

    rows = await dao.delete_ref(db_session, ref.id, proj.id)
    assert rows == 1
    assert await dao.get_ref_by_id(db_session, ref.id, proj.id) is None
