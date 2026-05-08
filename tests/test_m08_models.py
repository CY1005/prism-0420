"""M08 子片 1 — ModuleRelation model 单元测试。

覆盖 design §3 SQLAlchemy block + UNIQUE 三元组 + self-loop CHECK +
relation_type CHECK + cascade on node|project delete。
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.models.module_relation import ModuleRelation

# ─────────────── M08-MODEL-T1 持久化基础 ───────────────


async def test_relation_persists(db_session, make_project, make_node):
    user, proj = await make_project()
    n1 = await make_node(proj.id, name="A")
    n2 = await make_node(proj.id, name="B")
    r = ModuleRelation(
        project_id=proj.id,
        source_node_id=n1.id,
        target_node_id=n2.id,
        relation_type="depends_on",
        notes="A depends on B",
        created_by=user.id,
    )
    db_session.add(r)
    await db_session.flush()
    assert r.id is not None
    assert r.notes == "A depends on B"


# ─────────────── M08-MODEL-T2 UNIQUE 三元组 ───────────────


async def test_relation_unique_triple_violates(db_session, make_project, make_node):
    """UNIQUE(source, target, type) 三元组防完全重复。"""
    user, proj = await make_project()
    n1 = await make_node(proj.id, name="A")
    n2 = await make_node(proj.id, name="B")
    db_session.add(
        ModuleRelation(
            project_id=proj.id,
            source_node_id=n1.id,
            target_node_id=n2.id,
            relation_type="depends_on",
            created_by=user.id,
        )
    )
    await db_session.flush()
    db_session.add(
        ModuleRelation(
            project_id=proj.id,
            source_node_id=n1.id,
            target_node_id=n2.id,
            relation_type="depends_on",
            created_by=user.id,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_relation_same_pair_different_type_allowed(db_session, make_project, make_node):
    """同一对节点允许多种 relation_type（候选 A-2）。"""
    user, proj = await make_project()
    n1 = await make_node(proj.id, name="A")
    n2 = await make_node(proj.id, name="B")
    db_session.add_all(
        [
            ModuleRelation(
                project_id=proj.id,
                source_node_id=n1.id,
                target_node_id=n2.id,
                relation_type="depends_on",
                created_by=user.id,
            ),
            ModuleRelation(
                project_id=proj.id,
                source_node_id=n1.id,
                target_node_id=n2.id,
                relation_type="related_to",
                created_by=user.id,
            ),
        ]
    )
    await db_session.flush()  # 不应抛


async def test_relation_directionality_a_to_b_vs_b_to_a_allowed(
    db_session, make_project, make_node
):
    """有向关系（候选 A-1）：A→B 与 B→A 是不同记录。"""
    user, proj = await make_project()
    n1 = await make_node(proj.id, name="A")
    n2 = await make_node(proj.id, name="B")
    db_session.add_all(
        [
            ModuleRelation(
                project_id=proj.id,
                source_node_id=n1.id,
                target_node_id=n2.id,
                relation_type="depends_on",
                created_by=user.id,
            ),
            ModuleRelation(
                project_id=proj.id,
                source_node_id=n2.id,
                target_node_id=n1.id,
                relation_type="depends_on",
                created_by=user.id,
            ),
        ]
    )
    await db_session.flush()


# ─────────────── M08-MODEL-T3 CHECK constraints ───────────────


async def test_relation_invalid_type_violates(db_session, make_project, make_node):
    user, proj = await make_project()
    n1 = await make_node(proj.id, name="A")
    n2 = await make_node(proj.id, name="B")
    db_session.add(
        ModuleRelation(
            project_id=proj.id,
            source_node_id=n1.id,
            target_node_id=n2.id,
            relation_type="bogus",
            created_by=user.id,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_relation_self_loop_violates(db_session, make_project, make_node):
    user, proj = await make_project()
    n1 = await make_node(proj.id, name="A")
    db_session.add(
        ModuleRelation(
            project_id=proj.id,
            source_node_id=n1.id,
            target_node_id=n1.id,
            relation_type="depends_on",
            created_by=user.id,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M08-MODEL-T4 cascade ───────────────


async def test_relation_cascade_when_source_node_deleted(db_session, make_project, make_node):
    user, proj = await make_project()
    n1 = await make_node(proj.id, name="A")
    n2 = await make_node(proj.id, name="B")
    r = ModuleRelation(
        project_id=proj.id,
        source_node_id=n1.id,
        target_node_id=n2.id,
        relation_type="depends_on",
        created_by=user.id,
    )
    db_session.add(r)
    await db_session.flush()
    rid = r.id

    await db_session.delete(n1)
    await db_session.flush()
    db_session.expire_all()
    found = await db_session.scalar(select(ModuleRelation).where(ModuleRelation.id == rid))
    assert found is None, "source node 删除应级联删 relation"


async def test_relation_cascade_when_target_node_deleted(db_session, make_project, make_node):
    user, proj = await make_project()
    n1 = await make_node(proj.id, name="A")
    n2 = await make_node(proj.id, name="B")
    r = ModuleRelation(
        project_id=proj.id,
        source_node_id=n1.id,
        target_node_id=n2.id,
        relation_type="depends_on",
        created_by=user.id,
    )
    db_session.add(r)
    await db_session.flush()
    rid = r.id

    await db_session.delete(n2)
    await db_session.flush()
    db_session.expire_all()
    found = await db_session.scalar(select(ModuleRelation).where(ModuleRelation.id == rid))
    assert found is None, "target node 删除应级联删 relation"


async def test_relation_cascade_when_project_deleted(db_session, make_project, make_node):
    user, proj = await make_project()
    n1 = await make_node(proj.id, name="A")
    n2 = await make_node(proj.id, name="B")
    r = ModuleRelation(
        project_id=proj.id,
        source_node_id=n1.id,
        target_node_id=n2.id,
        relation_type="depends_on",
        created_by=user.id,
    )
    db_session.add(r)
    await db_session.flush()
    rid = r.id

    await db_session.delete(proj)
    await db_session.flush()
    db_session.expire_all()
    found = await db_session.scalar(select(ModuleRelation).where(ModuleRelation.id == rid))
    assert found is None, "project 删除应级联删 relation"
