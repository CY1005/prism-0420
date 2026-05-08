"""M07 子片 1 — Issue model 单元测试。

覆盖 design §3 SQLAlchemy block + CHECK status/category + node_id ON DELETE SET NULL
**orphan 语义**（与 M04/M06 cascade delete 不同）+ tags JSONB 默认 []。
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.models.issue import Issue

# ─────────────── M07-MODEL-T1 持久化基础 + 默认值 ───────────────


async def test_issue_persists_with_defaults(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    i = Issue(
        project_id=proj.id,
        node_id=node.id,
        category="bug",
        title="login 404",
        description="login button broken",
        created_by=user.id,
    )
    db_session.add(i)
    await db_session.flush()
    assert i.id is not None
    assert i.status == "open", "默认 status=open"
    assert i.tags == []
    assert i.resolved_at is None


async def test_issue_persists_floating_no_node(db_session, make_project):
    """游离 issue：node_id 可 NULL（design §1 边界灰区）。"""
    user, proj = await make_project()
    i = Issue(
        project_id=proj.id,
        node_id=None,
        category="tech_debt",
        title="random debt",
        description="项目级技术债",
        created_by=user.id,
    )
    db_session.add(i)
    await db_session.flush()
    assert i.node_id is None


# ─────────────── M07-MODEL-T2 CHECK constraints ───────────────


async def test_issue_invalid_status_violates(db_session, make_project):
    user, proj = await make_project()
    i = Issue(
        project_id=proj.id,
        category="bug",
        title="x",
        description="x",
        status="bogus",
        created_by=user.id,
    )
    db_session.add(i)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_issue_invalid_category_violates(db_session, make_project):
    user, proj = await make_project()
    i = Issue(
        project_id=proj.id,
        category="invalid_cat",
        title="x",
        description="x",
        created_by=user.id,
    )
    db_session.add(i)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M07-MODEL-T3 orphan 语义（node 删除 → node_id SET NULL）───────────────


async def test_issue_orphan_when_node_deleted(db_session, make_project, make_node):
    """**M07 关键测试**：node 删除时 issue 不级联删除（与 M04/M06 不同），
    而是 node_id 设 NULL（FK ON DELETE SET NULL）。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    i = Issue(
        project_id=proj.id,
        node_id=node.id,
        category="bug",
        title="x",
        description="x",
        created_by=user.id,
    )
    db_session.add(i)
    await db_session.flush()
    iid = i.id

    # 走 SQL 直删触发 DB FK SET NULL（Node.issues passive_deletes=True，
    # SQLAlchemy 不主动 UPDATE issues — DB 层 FK ON DELETE SET NULL 兜底）
    await db_session.delete(node)
    await db_session.flush()

    # 必须 expire 让 ORM 重新读 DB（否则 ORM cache 还显示旧 node_id）
    db_session.expire_all()
    found = await db_session.scalar(select(Issue).where(Issue.id == iid))
    assert found is not None, "issue 不应被级联删除（orphan 语义）"
    assert found.node_id is None, "node_id 应被 FK SET NULL"


async def test_issue_cascades_when_project_deleted(db_session, make_project):
    """project 删除时 issue 级联删除（FK ON DELETE CASCADE）。"""
    user, proj = await make_project()
    i = Issue(
        project_id=proj.id,
        category="bug",
        title="x",
        description="x",
        created_by=user.id,
    )
    db_session.add(i)
    await db_session.flush()
    iid = i.id

    await db_session.delete(proj)
    await db_session.flush()
    found = await db_session.scalar(select(Issue).where(Issue.id == iid))
    assert found is None, "project 删除应级联删 issue"


# ─────────────── M07-MODEL-T4 tags JSONB ───────────────


async def test_issue_tags_jsonb(db_session, make_project):
    user, proj = await make_project()
    i = Issue(
        project_id=proj.id,
        category="bug",
        title="x",
        description="x",
        tags=["regression", "p0"],
        created_by=user.id,
    )
    db_session.add(i)
    await db_session.flush()
    await db_session.refresh(i)
    assert i.tags == ["regression", "p0"]


# ─────────────── M07-MODEL-T5 Node ⇄ Issue 双向（passive_deletes）───────────────


async def test_node_issues_relationship_loads(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    db_session.add_all(
        [
            Issue(
                project_id=proj.id,
                node_id=node.id,
                category="bug",
                title="b1",
                description="d1",
                created_by=user.id,
            ),
            Issue(
                project_id=proj.id,
                node_id=node.id,
                category="tech_debt",
                title="b2",
                description="d2",
                created_by=user.id,
            ),
        ]
    )
    await db_session.flush()
    await db_session.refresh(node, ["issues"])
    assert len(node.issues) == 2
