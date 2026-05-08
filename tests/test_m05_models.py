"""M05 子片 1 — VersionRecord model 单元测试。

覆盖 design §3 SQLAlchemy block + 唯一约束 (node_id, version_label) +
CHECK change_type/release_mode + 部分唯一索引 (node_id) WHERE is_current=true +
ER Node ⇄ VersionRecord 双向 + cascade on node/project delete。
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.models.version_record import VersionRecord

# ─────────────── M05-MODEL-T1 持久化基础 ───────────────


async def test_version_record_persists_with_defaults(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")

    rec = VersionRecord(
        node_id=node.id,
        project_id=proj.id,
        version_label="v1.0.0",
        summary="initial release",
        created_by=user.id,
    )
    db_session.add(rec)
    await db_session.flush()

    assert rec.id is not None
    assert rec.change_type == "added", "默认 change_type=added"
    assert rec.release_mode == "release", "默认 release_mode=release"
    assert rec.is_current is False, "默认 is_current=false"
    assert rec.snapshot_data is None
    assert rec.created_at is not None


# ─────────────── M05-MODEL-T2 唯一约束 (node_id, version_label) ───────────────


async def test_version_record_unique_node_label_violates(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")

    db_session.add(
        VersionRecord(
            node_id=node.id,
            project_id=proj.id,
            version_label="v1.0",
            summary="first",
            created_by=user.id,
        )
    )
    await db_session.flush()

    db_session.add(
        VersionRecord(
            node_id=node.id,
            project_id=proj.id,
            version_label="v1.0",
            summary="dup",
            created_by=user.id,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M05-MODEL-T3 CHECK constraints ───────────────


async def test_version_record_invalid_change_type_violates(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")

    db_session.add(
        VersionRecord(
            node_id=node.id,
            project_id=proj.id,
            version_label="v1",
            summary="bad",
            change_type="bogus",
            created_by=user.id,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_version_record_invalid_release_mode_violates(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")

    db_session.add(
        VersionRecord(
            node_id=node.id,
            project_id=proj.id,
            version_label="v1",
            summary="bad",
            release_mode="canary",
            created_by=user.id,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M05-MODEL-T4 部分唯一索引 is_current ───────────────


async def test_version_record_partial_unique_is_current(db_session, make_project, make_node):
    """同 node 至多 1 条 is_current=true（design §3 部分唯一索引）。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")

    db_session.add(
        VersionRecord(
            node_id=node.id,
            project_id=proj.id,
            version_label="v1",
            summary="first",
            is_current=True,
            created_by=user.id,
        )
    )
    await db_session.flush()

    # 同 node 第二条 is_current=true → 部分唯一索引违约
    db_session.add(
        VersionRecord(
            node_id=node.id,
            project_id=proj.id,
            version_label="v2",
            summary="second",
            is_current=True,
            created_by=user.id,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_version_record_partial_unique_allows_multiple_false(
    db_session, make_project, make_node
):
    """is_current=false 允许多条；不触发部分唯一索引。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")

    for label in ("v1", "v2", "v3"):
        db_session.add(
            VersionRecord(
                node_id=node.id,
                project_id=proj.id,
                version_label=label,
                summary=f"{label}-sum",
                is_current=False,
                created_by=user.id,
            )
        )
    await db_session.flush()


# ─────────────── M05-MODEL-T5 cascade on node delete ───────────────


async def test_version_record_cascades_when_node_deleted(db_session, make_project, make_node):
    """node FK ondelete=CASCADE：删除 node 应级联删 version_records。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")

    rec = VersionRecord(
        node_id=node.id,
        project_id=proj.id,
        version_label="v1",
        summary="x",
        created_by=user.id,
    )
    db_session.add(rec)
    await db_session.flush()
    rec_id = rec.id

    await db_session.delete(node)
    await db_session.flush()

    found = await db_session.scalar(select(VersionRecord).where(VersionRecord.id == rec_id))
    assert found is None, "node 删除应级联删 version_record"


async def test_version_record_cascades_when_project_deleted(db_session, make_project, make_node):
    """project FK ondelete=CASCADE：删除 project 应级联删 version_records。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")

    rec = VersionRecord(
        node_id=node.id,
        project_id=proj.id,
        version_label="v1",
        summary="x",
        created_by=user.id,
    )
    db_session.add(rec)
    await db_session.flush()
    rec_id = rec.id

    await db_session.delete(proj)
    await db_session.flush()

    found = await db_session.scalar(select(VersionRecord).where(VersionRecord.id == rec_id))
    assert found is None, "project 删除应级联删 version_record"


# ─────────────── M05-MODEL-T6 Node back_populates 双向链 ───────────────


async def test_node_version_records_relationship_loads(db_session, make_project, make_node):
    """design §3 ER：Node ⇄ VersionRecord 双向 relationship。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")

    db_session.add_all(
        [
            VersionRecord(
                node_id=node.id,
                project_id=proj.id,
                version_label="v1",
                summary="s1",
                created_by=user.id,
            ),
            VersionRecord(
                node_id=node.id,
                project_id=proj.id,
                version_label="v2",
                summary="s2",
                created_by=user.id,
            ),
        ]
    )
    await db_session.flush()
    await db_session.refresh(node, ["version_records"])

    assert len(node.version_records) == 2
    assert {r.version_label for r in node.version_records} == {"v1", "v2"}
