"""M07 子片 3 — IssueService 测试。

覆盖 design §6 service 业务规则 + §10 activity_log + §13 ErrorCode +
状态机 4 状态 + R-X2 第三真注入 (orphan_by_node_id 4 参) + M18 baseline-patch。
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from api.errors.exceptions import (
    IssueAssigneeRequiredError,
    IssueClosedError,
    IssueNodeCrossProjectError,
    IssueNotFoundError,
    IssueTransitionInvalidError,
)
from api.services.issue_service import IssueService


@pytest.fixture
def svc():
    return IssueService()


# ─────────────── M07-SVC-T1 create golden ───────────────


async def test_svc_create_with_node(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    i = await svc.create(
        db_session,
        project_id=proj.id,
        category="bug",
        title="login broken",
        description="login button 404",
        node_id=node.id,
        actor_user_id=user.id,
    )
    assert i.id is not None
    assert i.status == "open"
    assert i.tags == []


async def test_svc_create_floating_no_node(db_session, svc, make_project):
    """游离 issue：node_id 可 NULL（design Q1 ack）。"""
    user, proj = await make_project()
    i = await svc.create(
        db_session,
        project_id=proj.id,
        category="tech_debt",
        title="random",
        description="d",
        actor_user_id=user.id,
    )
    assert i.node_id is None


async def test_svc_create_cross_project_node_raises(db_session, svc, make_project, make_node):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    with pytest.raises(IssueNodeCrossProjectError):
        await svc.create(
            db_session,
            project_id=projB.id,
            category="bug",
            title="hack",
            description="d",
            node_id=nA.id,
            actor_user_id=user.id,
        )


# ─────────────── M07-SVC-T2 list_by_project (M13 pilot pass-through) ───────────────


async def test_svc_list_by_project_with_filters(db_session, svc, make_project, make_node):
    """M13 pilot 跨模块调用契约：list_by_project pass-through DAO 多维过滤。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    await svc.create(
        db_session,
        project_id=proj.id,
        category="bug",
        title="b1",
        description="d",
        node_id=node.id,
        actor_user_id=user.id,
    )
    await svc.create(
        db_session,
        project_id=proj.id,
        category="tech_debt",
        title="t1",
        description="d",
        actor_user_id=user.id,
    )

    rows = await svc.list_by_project(db_session, project_id=proj.id, category="bug")
    assert len(rows) == 1
    rows_node = await svc.list_by_project(db_session, project_id=proj.id, node_id=node.id)
    assert len(rows_node) == 1


# ─────────────── M07-SVC-T3 update ───────────────


async def test_svc_update_changes_fields(db_session, svc, make_project):
    user, proj = await make_project()
    i = await svc.create(
        db_session,
        project_id=proj.id,
        category="bug",
        title="orig",
        description="d",
        actor_user_id=user.id,
    )
    updated = await svc.update(
        db_session,
        project_id=proj.id,
        issue_id=i.id,
        title="new",
        tags=["p0"],
        actor_user_id=user.id,
    )
    assert updated.title == "new"
    assert updated.tags == ["p0"]


async def test_svc_update_reattach_node(db_session, svc, make_project, make_node):
    """游离 issue 可重新关联 node（design CY ack reattach 允许）。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    i = await svc.create(
        db_session,
        project_id=proj.id,
        category="bug",
        title="x",
        description="d",
        actor_user_id=user.id,
    )
    assert i.node_id is None
    updated = await svc.update(
        db_session,
        project_id=proj.id,
        issue_id=i.id,
        node_id=node.id,
        actor_user_id=user.id,
    )
    assert updated.node_id == node.id


async def test_svc_update_not_found_raises(db_session, svc, make_project):
    user, proj = await make_project()
    with pytest.raises(IssueNotFoundError):
        await svc.update(
            db_session,
            project_id=proj.id,
            issue_id=uuid4(),
            title="x",
            actor_user_id=user.id,
        )


# ─────────────── M07-SVC-T4 状态机 transition ───────────────


async def test_svc_transition_open_to_in_progress(db_session, svc, make_project):
    user, proj = await make_project()
    assignee = user  # 简化用 self
    i = await svc.create(
        db_session,
        project_id=proj.id,
        category="bug",
        title="x",
        description="d",
        actor_user_id=user.id,
    )
    updated = await svc.transition(
        db_session,
        project_id=proj.id,
        issue_id=i.id,
        target_status="in_progress",
        assigned_to=assignee.id,
        actor_user_id=user.id,
    )
    assert updated.status == "in_progress"
    assert updated.assigned_to == assignee.id


async def test_svc_transition_open_to_in_progress_requires_assignee(db_session, svc, make_project):
    user, proj = await make_project()
    i = await svc.create(
        db_session,
        project_id=proj.id,
        category="bug",
        title="x",
        description="d",
        actor_user_id=user.id,
    )
    with pytest.raises(IssueAssigneeRequiredError):
        await svc.transition(
            db_session,
            project_id=proj.id,
            issue_id=i.id,
            target_status="in_progress",
            actor_user_id=user.id,
        )


async def test_svc_transition_open_to_resolved_writes_resolved_at(db_session, svc, make_project):
    user, proj = await make_project()
    i = await svc.create(
        db_session,
        project_id=proj.id,
        category="bug",
        title="x",
        description="d",
        actor_user_id=user.id,
    )
    updated = await svc.transition(
        db_session,
        project_id=proj.id,
        issue_id=i.id,
        target_status="resolved",
        actor_user_id=user.id,
    )
    assert updated.status == "resolved"
    assert updated.resolved_at is not None


async def test_svc_transition_in_progress_to_open_clears_assignee(db_session, svc, make_project):
    """取消认领（design §4 P5 audit F-3）：assigned_to 重置 NULL。"""
    user, proj = await make_project()
    i = await svc.create(
        db_session,
        project_id=proj.id,
        category="bug",
        title="x",
        description="d",
        actor_user_id=user.id,
    )
    await svc.transition(
        db_session,
        project_id=proj.id,
        issue_id=i.id,
        target_status="in_progress",
        assigned_to=user.id,
        actor_user_id=user.id,
    )
    updated = await svc.transition(
        db_session,
        project_id=proj.id,
        issue_id=i.id,
        target_status="open",
        actor_user_id=user.id,
    )
    assert updated.status == "open"
    assert updated.assigned_to is None


async def test_svc_transition_resolved_to_closed(db_session, svc, make_project):
    user, proj = await make_project()
    i = await svc.create(
        db_session,
        project_id=proj.id,
        category="bug",
        title="x",
        description="d",
        actor_user_id=user.id,
    )
    await svc.transition(
        db_session,
        project_id=proj.id,
        issue_id=i.id,
        target_status="resolved",
        actor_user_id=user.id,
    )
    updated = await svc.transition(
        db_session,
        project_id=proj.id,
        issue_id=i.id,
        target_status="closed",
        actor_user_id=user.id,
    )
    assert updated.status == "closed"


async def test_svc_transition_open_to_closed_invalid(db_session, svc, make_project):
    """open → closed 直接转换被禁（必经 in_progress 或 resolved）。"""
    user, proj = await make_project()
    i = await svc.create(
        db_session,
        project_id=proj.id,
        category="bug",
        title="x",
        description="d",
        actor_user_id=user.id,
    )
    with pytest.raises(IssueTransitionInvalidError):
        await svc.transition(
            db_session,
            project_id=proj.id,
            issue_id=i.id,
            target_status="closed",
            actor_user_id=user.id,
        )


async def test_svc_transition_closed_cannot_reopen(db_session, svc, make_project):
    """closed → 任何被禁（必须新建 issue）。"""
    user, proj = await make_project()
    i = await svc.create(
        db_session,
        project_id=proj.id,
        category="bug",
        title="x",
        description="d",
        actor_user_id=user.id,
    )
    await svc.transition(
        db_session,
        project_id=proj.id,
        issue_id=i.id,
        target_status="resolved",
        actor_user_id=user.id,
    )
    await svc.transition(
        db_session, project_id=proj.id, issue_id=i.id, target_status="closed", actor_user_id=user.id
    )
    with pytest.raises(IssueClosedError):
        await svc.transition(
            db_session,
            project_id=proj.id,
            issue_id=i.id,
            target_status="open",
            actor_user_id=user.id,
        )


# ─────────────── M07-SVC-T5 delete ───────────────


async def test_svc_delete(db_session, svc, make_project):
    user, proj = await make_project()
    i = await svc.create(
        db_session,
        project_id=proj.id,
        category="bug",
        title="x",
        description="d",
        actor_user_id=user.id,
    )
    await svc.delete(db_session, project_id=proj.id, issue_id=i.id, actor_user_id=user.id)
    with pytest.raises(IssueNotFoundError):
        await svc.get_by_id(db_session, project_id=proj.id, issue_id=i.id)


# ─────────────── M07-SVC-T6 R-X2 orphan_by_node_id ───────────────


async def test_svc_orphan_by_node_id_sets_null_writes_activity_log(
    db_session, svc, make_project, make_node, monkeypatch
):
    """**R-X2 第三真注入关键测试**：orphan UPDATE SET NULL + 每条 orphan event。

    R1-C P1-02 立修（M07 sprint，2026-05-08）：M04/M06 同款范式 — monkeypatch
    write_event 捕获 events 列表，验证 N 条独立 orphan 事件 + metadata 字段
    （之前仅验 node_id IS NULL，未覆盖 R10-1 R-X2 写 N 条独立 activity_log 不变量）。
    """
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    i1 = await svc.create(
        db_session,
        project_id=proj.id,
        category="bug",
        title="i1",
        description="d",
        node_id=node.id,
        actor_user_id=user.id,
    )
    i2 = await svc.create(
        db_session,
        project_id=proj.id,
        category="bug",
        title="i2",
        description="d",
        node_id=node.id,
        actor_user_id=user.id,
    )
    i1_id, i2_id = i1.id, i2.id

    # 捕获 orphan 路径写出的 activity_log events（M04/M06 同款 monkeypatch 范式）
    captured: list[dict] = []

    async def fake_write_event(**kwargs):
        captured.append(kwargs)

    monkeypatch.setattr("api.services.issue_service.write_event", fake_write_event)

    await svc.orphan_by_node_id(db_session, node.id, proj.id, user.id)

    # 直 SQL 验证 node_id IS NULL（避免 ORM cache 问题）
    res = await db_session.execute(
        text("SELECT id, node_id FROM issues WHERE id IN (:i1, :i2)"),
        {"i1": i1_id, "i2": i2_id},
    )
    rows = {r[0]: r[1] for r in res.fetchall()}
    assert rows[i1_id] is None
    assert rows[i2_id] is None

    # R-X2 R10-1 不变量：每条 issue 独立 orphan event（含 cascade_source metadata）
    orphan_events = [
        e for e in captured if e.get("action_type") == "orphan" and e.get("target_type") == "issue"
    ]
    assert len(orphan_events) == 2, (
        f"应为每条 issue 写 1 条 orphan event，实得 {len(orphan_events)}"
    )
    target_ids = {e["target_id"] for e in orphan_events}
    assert target_ids == {str(i1_id), str(i2_id)}
    for e in orphan_events:
        # M07 metadata key 与 M04/M06 不同（M07: old_node_id+reason; M04/M06: node_id+cascade_source）
        # — punt 进 m07 audit "跨模块 metadata key 命名一致性"，本测试按当前实装验
        assert e["metadata"]["old_node_id"] == str(node.id)
        assert e["metadata"]["reason"] == "cascade_from_node_delete"


async def test_svc_orphan_by_node_id_empty_no_op(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    # 不抛 — empty 列表 noop
    await svc.orphan_by_node_id(db_session, node.id, proj.id, user.id)


async def test_svc_orphan_by_node_id_propagates_write_event_exception(
    db_session, svc, make_project, make_node, monkeypatch
):
    """R1-C P1-02 范式（M04/M06 同款）：write_event 异常向上传播，不 catch-all。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    await svc.create(
        db_session,
        project_id=proj.id,
        category="bug",
        title="x",
        description="d",
        node_id=node.id,
        actor_user_id=user.id,
    )

    async def _boom(**kwargs):
        raise RuntimeError("simulated write_event failure")

    monkeypatch.setattr("api.services.issue_service.write_event", _boom)
    with pytest.raises(RuntimeError, match="simulated write_event failure"):
        await svc.orphan_by_node_id(db_session, node.id, proj.id, user.id)


# ─────────────── M07-SVC-T7 M18 baseline-patch get_for_embedding ───────────────


async def test_svc_get_for_embedding_concat_title_description(db_session, svc, make_project):
    user, proj = await make_project()
    i = await svc.create(
        db_session,
        project_id=proj.id,
        category="bug",
        title="login fails",
        description="when click on login button",
        actor_user_id=user.id,
    )
    text_out = await svc.get_for_embedding(db_session, i.id, proj.id)
    assert text_out is not None
    assert "login fails" in text_out
    assert "click on login" in text_out


async def test_svc_get_for_embedding_not_found_returns_none(db_session, svc, make_project):
    _, proj = await make_project()
    text_out = await svc.get_for_embedding(db_session, uuid4(), proj.id)
    assert text_out is None


async def test_svc_get_for_embedding_empty_description_still_includes_separator(
    db_session, svc, make_project
):
    """R1-C P1-01 立修配套：description 空字符串不应被 falsy 跳过。"""
    user, proj = await make_project()
    i = await svc.create(
        db_session,
        project_id=proj.id,
        category="bug",
        title="title only",
        description="",  # 空字符串（design §3 nullable=False，但允许 ""）
        actor_user_id=user.id,
    )
    text_out = await svc.get_for_embedding(db_session, i.id, proj.id)
    # 应拼出 "title only\n"（含分隔符），而非旧 falsy 跳过得 "title only"
    assert text_out == "title only\n"
