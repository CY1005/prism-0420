"""M15 子片 2 — ActivityStreamDAO 单元测试（design §3 + §9 / R-X3 精神 + ADR-003 规则 3）。

覆盖：
- list_stream tenant 强过滤 / JOIN user_name / 多过滤维度 / 首页 total D-2 / ORDER /
  page validation / 空结果
- list_for_team target_type+target_id 路径 / 跨团队过滤 / page validation / 首页 total
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from api.dao.activity_stream_dao import ActivityStreamDAO


@pytest.fixture()
def dao() -> ActivityStreamDAO:
    return ActivityStreamDAO()


# ─────────────── M15-DAO-T1 list_stream 基础 + JOIN user_name ───────────────


async def test_list_stream_returns_join_user_name(db_session, make_project, make_activity_log, dao):
    user, proj = await make_project()
    await make_activity_log(
        project_id=proj.id,
        user_id=user.id,
        action_type="project_created",
        target_type="project",
        target_id=str(proj.id),
        summary="创建项目",
    )
    rows, total = await dao.list_stream(db_session, proj.id)
    assert total == 1
    assert len(rows) == 1
    ev, user_name = rows[0]
    assert user_name == user.name
    assert ev.project_id == proj.id


# ─────────────── M15-DAO-T2 强 project_id tenant 过滤 ───────────────


async def test_list_stream_excludes_other_project(db_session, make_project, make_activity_log, dao):
    user_a, proj_a = await make_project(name_suffix="-a")
    user_b, proj_b = await make_project(name_suffix="-b")
    await make_activity_log(
        project_id=proj_a.id,
        user_id=user_a.id,
        action_type="project_created",
        target_type="project",
        target_id=str(proj_a.id),
    )
    await make_activity_log(
        project_id=proj_b.id,
        user_id=user_b.id,
        action_type="project_created",
        target_type="project",
        target_id=str(proj_b.id),
    )
    rows_a, total_a = await dao.list_stream(db_session, proj_a.id)
    assert total_a == 1
    assert all(ev.project_id == proj_a.id for ev, _ in rows_a)


# ─────────────── M15-DAO-T3 user_id 过滤 ───────────────


async def test_list_stream_filter_by_user_id(
    db_session, make_project, make_user, make_activity_log, dao
):
    user_a, proj = await make_project()
    user_b = await make_user()
    await make_activity_log(
        project_id=proj.id,
        user_id=user_a.id,
        action_type="project_created",
        target_type="project",
        target_id=str(proj.id),
    )
    await make_activity_log(
        project_id=proj.id,
        user_id=user_b.id,
        action_type="node_created",
        target_type="node",
        target_id=str(uuid4()),
    )
    rows, total = await dao.list_stream(db_session, proj.id, user_id=user_a.id)
    assert total == 1
    assert all(ev.user_id == user_a.id for ev, _ in rows)


# ─────────────── M15-DAO-T4 action_type 过滤 ───────────────


async def test_list_stream_filter_by_action_type(db_session, make_project, make_activity_log, dao):
    user, proj = await make_project()
    await make_activity_log(
        project_id=proj.id,
        user_id=user.id,
        action_type="project_created",
        target_type="project",
        target_id=str(proj.id),
    )
    await make_activity_log(
        project_id=proj.id,
        user_id=user.id,
        action_type="node_created",
        target_type="node",
        target_id=str(uuid4()),
    )
    rows, total = await dao.list_stream(db_session, proj.id, action_type="node_created")
    assert total == 1
    assert all(ev.action_type == "node_created" for ev, _ in rows)


# ─────────────── M15-DAO-T5 target_type 过滤 ───────────────


async def test_list_stream_filter_by_target_type(db_session, make_project, make_activity_log, dao):
    user, proj = await make_project()
    await make_activity_log(
        project_id=proj.id,
        user_id=user.id,
        action_type="project_created",
        target_type="project",
        target_id=str(proj.id),
    )
    await make_activity_log(
        project_id=proj.id,
        user_id=user.id,
        action_type="node_created",
        target_type="node",
        target_id=str(uuid4()),
    )
    rows, total = await dao.list_stream(db_session, proj.id, target_type="node")
    assert total == 1
    assert all(ev.target_type == "node" for ev, _ in rows)


# ─────────────── M15-DAO-T6 时间范围过滤 ───────────────


async def test_list_stream_filter_by_time_range(db_session, make_project, make_activity_log, dao):
    user, proj = await make_project()
    ev1 = await make_activity_log(
        project_id=proj.id,
        user_id=user.id,
        action_type="project_created",
        target_type="project",
        target_id=str(proj.id),
    )
    # 改 created_at 模拟历史事件（直接 setattr + flush）
    old = datetime.now(UTC) - timedelta(days=10)
    ev1.created_at = old
    await db_session.flush()

    await make_activity_log(
        project_id=proj.id,
        user_id=user.id,
        action_type="node_created",
        target_type="node",
        target_id=str(uuid4()),
    )

    cutoff = datetime.now(UTC) - timedelta(days=1)
    rows, total = await dao.list_stream(db_session, proj.id, from_dt=cutoff)
    assert total == 1


# ─────────────── M15-DAO-T7 首页 total D-2 / 后续 page total=None ───────────────


async def test_list_stream_total_first_page_only(db_session, make_project, make_activity_log, dao):
    user, proj = await make_project()
    for _ in range(3):
        await make_activity_log(
            project_id=proj.id,
            user_id=user.id,
            action_type="node_created",
            target_type="node",
            target_id=str(uuid4()),
        )

    _, total_first = await dao.list_stream(db_session, proj.id, page=1, page_size=2)
    _, total_second = await dao.list_stream(db_session, proj.id, page=2, page_size=2)
    assert total_first == 3
    assert total_second is None


# ─────────────── M15-DAO-T8 ORDER BY created_at DESC ───────────────


async def test_list_stream_order_by_created_at_desc(
    db_session, make_project, make_activity_log, dao
):
    user, proj = await make_project()
    ev1 = await make_activity_log(
        project_id=proj.id,
        user_id=user.id,
        action_type="project_created",
        target_type="project",
        target_id=str(proj.id),
        summary="first",
    )
    # 强制 ev1 created_at 在过去，避免与 ev2 同一 timestamp 触发 id 二次排序歧义
    ev1.created_at = datetime.now(UTC) - timedelta(seconds=10)
    await db_session.flush()
    ev2 = await make_activity_log(
        project_id=proj.id,
        user_id=user.id,
        action_type="node_created",
        target_type="node",
        target_id=str(uuid4()),
        summary="second",
    )
    rows, _ = await dao.list_stream(db_session, proj.id)
    assert [ev.summary for ev, _ in rows] == ["second", "first"]
    assert rows[0][0].id == ev2.id
    assert rows[1][0].id == ev1.id


# ─────────────── M15-DAO-T9 page/page_size <= 0 ValueError ───────────────


async def test_list_stream_invalid_page_raises(db_session, make_project, dao):
    _, proj = await make_project()
    with pytest.raises(ValueError):
        await dao.list_stream(db_session, proj.id, page=0)
    with pytest.raises(ValueError):
        await dao.list_stream(db_session, proj.id, page_size=0)


# ─────────────── M15-DAO-T10 空结果（过滤全不匹配 / page 越界）───────────────


async def test_list_stream_empty_when_filter_no_match(
    db_session, make_project, make_activity_log, dao
):
    user, proj = await make_project()
    await make_activity_log(
        project_id=proj.id,
        user_id=user.id,
        action_type="project_created",
        target_type="project",
        target_id=str(proj.id),
    )
    rows, total = await dao.list_stream(db_session, proj.id, action_type="news_created")
    assert rows == []
    assert total == 0


async def test_list_stream_empty_when_page_out_of_range(
    db_session, make_project, make_activity_log, dao
):
    user, proj = await make_project()
    await make_activity_log(
        project_id=proj.id,
        user_id=user.id,
        action_type="project_created",
        target_type="project",
        target_id=str(proj.id),
    )
    rows, total = await dao.list_stream(db_session, proj.id, page=99, page_size=10)
    # page=99 不是首页 → total=None；rows 空
    assert rows == []
    assert total is None


# ─────────────── M15-DAO-T11 list_for_team target_type+id 路径 ───────────────


async def test_list_for_team_returns_team_events(db_session, make_user, make_activity_log, dao):
    user = await make_user()
    fake_team_id = uuid4()
    other_team_id = uuid4()
    await make_activity_log(
        project_id=None,  # team_* 事件无 project_id（M20 baseline-patch）
        user_id=user.id,
        action_type="team_created",
        target_type="team",
        target_id=str(fake_team_id),
    )
    await make_activity_log(
        project_id=None,
        user_id=user.id,
        action_type="team_renamed",
        target_type="team",
        target_id=str(other_team_id),
    )
    rows, total = await dao.list_for_team(db_session, fake_team_id)
    assert total == 1
    assert all(ev.target_id == str(fake_team_id) for ev, _ in rows)


# ─────────────── M15-DAO-T12 list_for_team 不匹配 0 行 ───────────────


async def test_list_for_team_empty_when_no_match(db_session, dao):
    rows, total = await dao.list_for_team(db_session, uuid4())
    assert rows == []
    assert total == 0


# ─────────────── M15-DAO-T13 list_for_team page validation ───────────────


async def test_list_for_team_invalid_page_raises(db_session, dao):
    with pytest.raises(ValueError):
        await dao.list_for_team(db_session, uuid4(), page=0)
    with pytest.raises(ValueError):
        await dao.list_for_team(db_session, uuid4(), page_size=0)


# ─────────────── M15-DAO-T14 list_for_team 首页 total / 后续 None ───────────────


async def test_list_for_team_total_first_page_only(db_session, make_user, make_activity_log, dao):
    user = await make_user()
    team_id = uuid4()
    for _ in range(3):
        await make_activity_log(
            project_id=None,
            user_id=user.id,
            action_type="team_renamed",
            target_type="team",
            target_id=str(team_id),
        )

    _, total_first = await dao.list_for_team(db_session, team_id, page=1, page_size=2)
    _, total_second = await dao.list_for_team(db_session, team_id, page=2, page_size=2)
    assert total_first == 3
    assert total_second is None


# ─────────────── M15-DAO-T15 跨 project list_stream 不召回 team 事件 ───────────────


async def test_list_stream_does_not_return_team_events_with_no_project(
    db_session, make_project, make_user, make_activity_log, dao
):
    """team_* 事件 project_id=None；list_stream 强 project_id=? 过滤天然不召回。"""
    user, proj = await make_project()
    team_id = uuid4()
    await make_activity_log(
        project_id=None,
        user_id=user.id,
        action_type="team_created",
        target_type="team",
        target_id=str(team_id),
    )
    rows, total = await dao.list_stream(db_session, proj.id)
    assert rows == []
    assert total == 0
