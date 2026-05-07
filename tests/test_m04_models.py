"""M04 子片 1 — DimensionRecord model 单元测试。

覆盖 design §3 SQLAlchemy block + 唯一约束 + tenant 一致性 NOT NULL。
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from api.models.dimension_record import DimensionRecord

# ─────────────── helpers ───────────────


async def _seed_dim_type(db_session, key: str = "tech_stack", name: str = "技术栈") -> int:
    """建一条 dimension_types 行并返回 id（M02 seed 默认 'default' 之外）。"""
    from api.models.project import DimensionType

    dt = DimensionType(key=key, name=name)
    db_session.add(dt)
    await db_session.flush()
    return dt.id


# ─────────────── M04-MODEL-T1 持久化基础 ───────────────


async def test_dim_record_persists_with_defaults(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await _seed_dim_type(db_session, key="t1")

    rec = DimensionRecord(
        node_id=node.id,
        project_id=proj.id,
        dimension_type_id=type_id,
        content={"description": "hello"},
        created_by=user.id,
        updated_by=user.id,
    )
    db_session.add(rec)
    await db_session.flush()

    assert rec.id is not None
    assert rec.version == 1, "默认 version=1（乐观锁初始）"
    assert rec.content == {"description": "hello"}
    assert rec.created_at is not None
    assert rec.updated_at is not None


# ─────────────── M04-MODEL-T2 唯一约束 (node_id, dimension_type_id) ───────────────


async def test_dim_record_unique_node_type_violates(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await _seed_dim_type(db_session, key="t_uq")

    db_session.add(
        DimensionRecord(
            node_id=node.id,
            project_id=proj.id,
            dimension_type_id=type_id,
            content={},
            created_by=user.id,
            updated_by=user.id,
        )
    )
    await db_session.flush()

    db_session.add(
        DimensionRecord(
            node_id=node.id,
            project_id=proj.id,
            dimension_type_id=type_id,
            content={"a": 1},
            created_by=user.id,
            updated_by=user.id,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M04-MODEL-T3 cascade on node delete ───────────────


async def test_dim_record_cascades_when_node_deleted(db_session, make_project, make_node):
    """node FK ondelete=CASCADE：删除 node 应级联删 dimension_records。"""
    from sqlalchemy import select

    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await _seed_dim_type(db_session, key="t_cas")

    rec = DimensionRecord(
        node_id=node.id,
        project_id=proj.id,
        dimension_type_id=type_id,
        content={},
        created_by=user.id,
        updated_by=user.id,
    )
    db_session.add(rec)
    await db_session.flush()
    rec_id = rec.id

    await db_session.delete(node)
    await db_session.flush()

    found = await db_session.scalar(select(DimensionRecord).where(DimensionRecord.id == rec_id))
    assert found is None, "node 删除应级联删 dimension_record"


# ─────────────── M04-MODEL-T4 cascade on project delete ───────────────


async def test_dim_record_cascades_when_project_deleted(db_session, make_project, make_node):
    """project FK ondelete=CASCADE：删除 project 应级联删 dimension_records。"""
    from sqlalchemy import select

    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await _seed_dim_type(db_session, key="t_cas_p")

    rec = DimensionRecord(
        node_id=node.id,
        project_id=proj.id,
        dimension_type_id=type_id,
        content={},
        created_by=user.id,
        updated_by=user.id,
    )
    db_session.add(rec)
    await db_session.flush()
    rec_id = rec.id

    await db_session.delete(proj)
    await db_session.flush()

    found = await db_session.scalar(select(DimensionRecord).where(DimensionRecord.id == rec_id))
    assert found is None, "project 删除应级联删 dimension_record"


# ─────────────── M04-MODEL-T5 Node back_populates 双向链 ───────────────


async def test_node_dimension_records_relationship_loads(db_session, make_project, make_node):
    """design §3 ER：Node ⇄ DimensionRecord 双向 relationship。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id_1 = await _seed_dim_type(db_session, key="b1")
    type_id_2 = await _seed_dim_type(db_session, key="b2")

    db_session.add_all(
        [
            DimensionRecord(
                node_id=node.id,
                project_id=proj.id,
                dimension_type_id=type_id_1,
                content={},
                created_by=user.id,
                updated_by=user.id,
            ),
            DimensionRecord(
                node_id=node.id,
                project_id=proj.id,
                dimension_type_id=type_id_2,
                content={},
                created_by=user.id,
                updated_by=user.id,
            ),
        ]
    )
    await db_session.flush()
    await db_session.refresh(node, ["dimension_records"])

    assert len(node.dimension_records) == 2
    assert {r.dimension_type_id for r in node.dimension_records} == {type_id_1, type_id_2}
