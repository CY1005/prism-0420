"""M06 子片 1 — Competitor + CompetitorRef model 单元测试。

覆盖 design §3 SQLAlchemy block + UNIQUE(node_id, competitor_id) +
display_name 不唯一（同名版本不同）+ ER 双向 + cascade on node/competitor/project delete。
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.models.competitor import Competitor, CompetitorRef

# ─────────────── M06-MODEL-T1 持久化基础 ───────────────


async def test_competitor_persists(db_session, make_project):
    user, proj = await make_project()
    c = Competitor(
        project_id=proj.id,
        display_name="Notion",
        website_url="https://notion.so",
        description="all-in-one workspace",
        created_by=user.id,
    )
    db_session.add(c)
    await db_session.flush()
    assert c.id is not None
    assert c.created_at is not None


async def test_competitor_ref_persists_with_jsonb(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    c = Competitor(project_id=proj.id, display_name="Notion", created_by=user.id)
    db_session.add(c)
    await db_session.flush()

    ref = CompetitorRef(
        node_id=node.id,
        competitor_id=c.id,
        project_id=proj.id,
        competitor_version="3.5",
        feature_coverage="覆盖核心",
        tech_approach="block-based",
        pros_and_cons={"pros": ["快"], "cons": ["贵"]},
        created_by=user.id,
    )
    db_session.add(ref)
    await db_session.flush()
    assert ref.pros_and_cons == {"pros": ["快"], "cons": ["贵"]}


# ─────────────── M06-MODEL-T2 同名竞品允许（无 UNIQUE on display_name）───────────────


async def test_competitor_same_display_name_allowed(db_session, make_project):
    """design §3 字面：display_name 无唯一约束，允许同名不同版本竞品。"""
    user, proj = await make_project()
    db_session.add_all(
        [
            Competitor(project_id=proj.id, display_name="Notion", created_by=user.id),
            Competitor(project_id=proj.id, display_name="Notion", created_by=user.id),
        ]
    )
    await db_session.flush()  # 不应抛 IntegrityError


# ─────────────── M06-MODEL-T3 UNIQUE(node, competitor) ─────────────


async def test_competitor_ref_unique_node_competitor_violates(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    c = Competitor(project_id=proj.id, display_name="Notion", created_by=user.id)
    db_session.add(c)
    await db_session.flush()

    db_session.add(
        CompetitorRef(
            node_id=node.id,
            competitor_id=c.id,
            project_id=proj.id,
            created_by=user.id,
        )
    )
    await db_session.flush()

    db_session.add(
        CompetitorRef(
            node_id=node.id,
            competitor_id=c.id,
            project_id=proj.id,
            created_by=user.id,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M06-MODEL-T4 cascade on node delete ───────────────


async def test_competitor_ref_cascades_when_node_deleted(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    c = Competitor(project_id=proj.id, display_name="X", created_by=user.id)
    db_session.add(c)
    await db_session.flush()
    ref = CompetitorRef(
        node_id=node.id,
        competitor_id=c.id,
        project_id=proj.id,
        created_by=user.id,
    )
    db_session.add(ref)
    await db_session.flush()
    ref_id = ref.id

    await db_session.delete(node)
    await db_session.flush()
    found = await db_session.scalar(select(CompetitorRef).where(CompetitorRef.id == ref_id))
    assert found is None


async def test_competitor_ref_cascades_when_competitor_deleted(db_session, make_project, make_node):
    """删除 competitor 应级联删 refs（competitor_id ondelete=CASCADE）。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    c = Competitor(project_id=proj.id, display_name="X", created_by=user.id)
    db_session.add(c)
    await db_session.flush()
    ref = CompetitorRef(
        node_id=node.id,
        competitor_id=c.id,
        project_id=proj.id,
        created_by=user.id,
    )
    db_session.add(ref)
    await db_session.flush()
    ref_id = ref.id

    await db_session.delete(c)
    await db_session.flush()
    found = await db_session.scalar(select(CompetitorRef).where(CompetitorRef.id == ref_id))
    assert found is None


async def test_competitor_cascades_when_project_deleted(db_session, make_project):
    user, proj = await make_project()
    c = Competitor(project_id=proj.id, display_name="X", created_by=user.id)
    db_session.add(c)
    await db_session.flush()
    cid = c.id
    await db_session.delete(proj)
    await db_session.flush()
    found = await db_session.scalar(select(Competitor).where(Competitor.id == cid))
    assert found is None


# ─────────────── M06-MODEL-T5 ER 双向链 ───────────────


async def test_competitor_refs_relationship_loads(db_session, make_project, make_node):
    """design §3 ER：Competitor ⇄ CompetitorRef 双向 / Node ⇄ CompetitorRef 双向。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    c = Competitor(project_id=proj.id, display_name="X", created_by=user.id)
    db_session.add(c)
    await db_session.flush()
    db_session.add_all(
        [
            CompetitorRef(
                node_id=node.id,
                competitor_id=c.id,
                project_id=proj.id,
                created_by=user.id,
            )
        ]
    )
    await db_session.flush()

    await db_session.refresh(c, ["refs"])
    assert len(c.refs) == 1

    await db_session.refresh(node, ["competitor_refs"])
    assert len(node.competitor_refs) == 1
