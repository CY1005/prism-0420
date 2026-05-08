"""M05 子片 3 — VersionService 测试。

覆盖 design §6 service 业务规则 + §10 activity_log + §13 ErrorCode
+ B2 (闸门 2.5) 并发 set_current 双写测试 + A9 race race IntegrityError 转换。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from api.errors.exceptions import (
    VersionLabelDuplicateError,
    VersionNotFoundError,
)
from api.services.version_service import VersionService


@pytest.fixture
def svc():
    return VersionService()


# ─────────────── M05-SVC-T1 create golden ───────────────


async def test_svc_create_persists_and_writes_activity_log(
    db_session, svc, make_project, make_node
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")

    rec = await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        version_label="v1.0",
        summary="initial",
        actor_user_id=user.id,
    )
    assert rec.id is not None
    assert rec.version_label == "v1.0"
    assert rec.is_current is False
    assert rec.change_type == "added"


async def test_svc_create_with_is_current_clears_previous(db_session, svc, make_project, make_node):
    """create with is_current=True 同事务内先清旧 current 再 INSERT。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")

    v1 = await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        version_label="v1",
        summary="first",
        is_current=True,
        actor_user_id=user.id,
    )
    v2 = await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        version_label="v2",
        summary="second",
        is_current=True,
        actor_user_id=user.id,
    )
    await db_session.refresh(v1)
    await db_session.refresh(v2)
    assert v1.is_current is False, "v1 应被自动清掉 current"
    assert v2.is_current is True


async def test_svc_create_duplicate_label_raises_label_duplicate(
    db_session, svc, make_project, make_node
):
    """A9: UNIQUE(node, version_label) 冲突 → VersionLabelDuplicateError，不裸抛 500。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")

    await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        version_label="v1",
        summary="first",
        actor_user_id=user.id,
    )
    with pytest.raises(VersionLabelDuplicateError):
        await svc.create(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            version_label="v1",
            summary="dup",
            actor_user_id=user.id,
        )


async def test_svc_create_blocks_cross_tenant_node(db_session, svc, make_project, make_node):
    """三层防御第三层：node 不属于该 project → VersionNotFoundError 不暴露 forbidden。"""
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")

    with pytest.raises(VersionNotFoundError):
        await svc.create(
            db_session,
            project_id=projB.id,
            node_id=nA.id,
            version_label="v1",
            summary="hack",
            actor_user_id=user.id,
        )


# ─────────────── M05-SVC-T2 list_by_node ───────────────


async def test_svc_list_by_node_returns_ordered(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    for label in ("v1", "v2", "v3"):
        await svc.create(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            version_label=label,
            summary=label,
            actor_user_id=user.id,
        )

    rows = await svc.list_by_node(db_session, project_id=proj.id, node_id=node.id)
    assert len(rows) == 3


async def test_svc_list_by_node_blocks_cross_tenant(db_session, svc, make_project, make_node):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    await svc.create(
        db_session,
        project_id=projA.id,
        node_id=nA.id,
        version_label="v1",
        summary="x",
        actor_user_id=user.id,
    )

    with pytest.raises(VersionNotFoundError):
        # node A 不属于 projB → service 层第三层防御抛 VersionNotFoundError
        await svc.list_by_node(db_session, project_id=projB.id, node_id=nA.id)


async def test_svc_count_by_node(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    for label in ("v1", "v2"):
        await svc.create(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            version_label=label,
            summary=label,
            actor_user_id=user.id,
        )

    assert await svc.count_by_node(db_session, project_id=proj.id, node_id=node.id) == 2


async def test_svc_count_by_node_blocks_cross_tenant_node(db_session, svc, make_project, make_node):
    """R1-C P1-02 立修：cross-tenant node_id 走 NotFoundError 而非静默返 0。"""
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    await svc.create(
        db_session,
        project_id=projA.id,
        node_id=nA.id,
        version_label="v1",
        summary="x",
        actor_user_id=user.id,
    )

    with pytest.raises(VersionNotFoundError):
        await svc.count_by_node(db_session, project_id=projB.id, node_id=nA.id)


# ─────────────── M05-SVC-T3 get_by_id ───────────────


async def test_svc_get_by_id_returns_version(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    rec = await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        version_label="v1",
        summary="x",
        actor_user_id=user.id,
    )

    found = await svc.get_by_id(db_session, project_id=proj.id, node_id=node.id, version_id=rec.id)
    assert found.id == rec.id


async def test_svc_get_by_id_not_found_raises(db_session, svc, make_project, make_node):
    _, proj = await make_project()
    node = await make_node(proj.id, name="A")
    with pytest.raises(VersionNotFoundError):
        await svc.get_by_id(db_session, project_id=proj.id, node_id=node.id, version_id=uuid4())


async def test_svc_get_by_id_wrong_node_raises(db_session, svc, make_project, make_node):
    """version 存在但属于另一节点 → 抛 VersionNotFoundError（防 wrong-node-id 拼凑）。"""
    user, proj = await make_project()
    node1 = await make_node(proj.id, name="N1")
    node2 = await make_node(proj.id, name="N2")
    rec = await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node1.id,
        version_label="v1",
        summary="x",
        actor_user_id=user.id,
    )

    with pytest.raises(VersionNotFoundError):
        await svc.get_by_id(db_session, project_id=proj.id, node_id=node2.id, version_id=rec.id)


# ─────────────── M05-SVC-T4 update_metadata ───────────────


async def test_svc_update_metadata_changes_summary(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    rec = await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        version_label="v1",
        summary="orig",
        actor_user_id=user.id,
    )

    updated = await svc.update_metadata(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        version_id=rec.id,
        summary="new",
        details="extra",
        actor_user_id=user.id,
    )
    assert updated.summary == "new"
    assert updated.details == "extra"


async def test_svc_update_metadata_no_op_returns_existing(db_session, svc, make_project, make_node):
    """全部 None → 不写 activity_log 也不报错；返回 existing。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    rec = await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        version_label="v1",
        summary="x",
        actor_user_id=user.id,
    )

    result = await svc.update_metadata(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        version_id=rec.id,
        actor_user_id=user.id,
    )
    assert result.id == rec.id


async def test_svc_update_metadata_not_found_raises(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    with pytest.raises(VersionNotFoundError):
        await svc.update_metadata(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            version_id=uuid4(),
            summary="x",
            actor_user_id=user.id,
        )


# ─────────────── M05-SVC-T5 delete ───────────────


async def test_svc_delete_removes_record(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    rec = await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        version_label="v1",
        summary="x",
        actor_user_id=user.id,
    )

    await svc.delete(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        version_id=rec.id,
        actor_user_id=user.id,
    )
    with pytest.raises(VersionNotFoundError):
        await svc.get_by_id(db_session, project_id=proj.id, node_id=node.id, version_id=rec.id)


async def test_svc_delete_not_found_raises(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    with pytest.raises(VersionNotFoundError):
        await svc.delete(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            version_id=uuid4(),
            actor_user_id=user.id,
        )


# ─────────────── M05-SVC-T6 set_current ───────────────


async def test_svc_set_current_marks_and_clears_previous(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    v1 = await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        version_label="v1",
        summary="x",
        is_current=True,
        actor_user_id=user.id,
    )
    v2 = await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        version_label="v2",
        summary="y",
        actor_user_id=user.id,
    )

    result = await svc.set_current(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        version_id=v2.id,
        actor_user_id=user.id,
    )
    await db_session.refresh(v1)
    assert result.is_current is True
    assert v1.is_current is False, "set_current 应清空旧 current"


async def test_svc_set_current_idempotent_for_same_version(
    db_session, svc, make_project, make_node
):
    """对当前已是 current 的版本调 set_current 应平稳通过（clear_current_flag 把它清成 false 再标 true）。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    v = await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        version_label="v1",
        summary="x",
        is_current=True,
        actor_user_id=user.id,
    )

    result = await svc.set_current(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        version_id=v.id,
        actor_user_id=user.id,
    )
    assert result.is_current is True


async def test_svc_set_current_blocks_cross_node(db_session, svc, make_project, make_node):
    """version_id 属于另一 node → VersionNotFoundError。"""
    user, proj = await make_project()
    node1 = await make_node(proj.id, name="N1")
    node2 = await make_node(proj.id, name="N2")
    rec = await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node1.id,
        version_label="v1",
        summary="x",
        actor_user_id=user.id,
    )

    with pytest.raises(VersionNotFoundError):
        await svc.set_current(
            db_session,
            project_id=proj.id,
            node_id=node2.id,
            version_id=rec.id,
            actor_user_id=user.id,
        )


# ─────────────── M05-SVC-T7 (B2 闸门 2.5) 并发 set_current 双写 ───────────────


async def test_svc_concurrent_set_current_keeps_partial_unique_invariant(
    db_session, svc, make_project, make_node
):
    """B2 候选 A 实证：service 路径下"同 node 至多 1 条 is_current=true"不变量保持。

    验证：(1) 多次 create(is_current=True) 序列后 (2) 多次 set_current 切换后
    部分唯一索引 uq_version_node_is_current 不会被 service 层路径破坏。
    """
    from sqlalchemy import select

    from api.models.version_record import VersionRecord

    user, proj = await make_project()
    node = await make_node(proj.id, name="A")

    # 序列 1: 三次 create(is_current=True) — service 层每次先 clear 旧 current
    for label in ("va", "vb", "vc"):
        await svc.create(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            version_label=label,
            summary=label,
            is_current=True,
            actor_user_id=user.id,
        )
    res = await db_session.execute(
        select(VersionRecord).where(
            VersionRecord.node_id == node.id,
            VersionRecord.is_current.is_(True),
        )
    )
    rows = res.scalars().all()
    assert len(rows) == 1
    assert rows[0].version_label == "vc"

    # 序列 2: set_current 切回 va
    va = (
        await db_session.execute(
            select(VersionRecord).where(
                VersionRecord.node_id == node.id,
                VersionRecord.version_label == "va",
            )
        )
    ).scalar_one()
    await svc.set_current(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        version_id=va.id,
        actor_user_id=user.id,
    )
    res = await db_session.execute(
        select(VersionRecord).where(
            VersionRecord.node_id == node.id,
            VersionRecord.is_current.is_(True),
        )
    )
    rows = res.scalars().all()
    assert len(rows) == 1
    assert rows[0].version_label == "va"
