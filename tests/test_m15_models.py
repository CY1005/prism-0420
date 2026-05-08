"""M15 子片 1 — ActivityLog model 单元测试（design §3 / R10-2 owner）。

覆盖：
- T1 持久化基础 + 默认（id / created_at 自动 / event_metadata=None）
- T2 持久化全字段（含 JSONB metadata 嵌套结构）
- T3 project_id NULLABLE 全局事件（M14 baseline-patch 实证 / 2026-05-08）
- T4 action_type CHECK 约束（未知值拦截）
- T5 target_type CHECK 约束（未知值拦截）
- T6 ImmutableMixin 无 updated_at（表字段层验证）
- T7 project ON DELETE CASCADE 联动 activity_logs
- T8 M14 全局事件字面端到端（project_id=None + action_type='news_created' / 同 'news_linked'）
- T9 metadata JSONB 嵌套序列化往返
"""

from __future__ import annotations

import pytest
from sqlalchemy import delete, inspect, select
from sqlalchemy.exc import IntegrityError

from api.models.activity_log import ActivityLog
from api.models.project import Project

# ─────────────── M15-MODEL-T1 持久化基础 ───────────────


async def test_activity_log_persists_with_defaults(db_session, make_project):
    user, proj = await make_project()
    ev = ActivityLog(
        project_id=proj.id,
        user_id=user.id,
        action_type="project_created",
        target_type="project",
        target_id=str(proj.id),
        summary="创建了项目",
    )
    db_session.add(ev)
    await db_session.flush()
    await db_session.refresh(ev)
    assert ev.id is not None
    assert ev.created_at is not None
    assert ev.event_metadata is None


# ─────────────── M15-MODEL-T2 持久化全字段（JSONB metadata）───────────────


async def test_activity_log_persists_full_fields(db_session, make_project):
    user, proj = await make_project()
    ev = ActivityLog(
        project_id=proj.id,
        user_id=user.id,
        action_type="node_updated",
        target_type="node",
        target_id="00000000-0000-0000-0000-000000000001",
        summary="更新了节点『登录流程』",
        event_metadata={"updated_fields": ["title", "description"]},
    )
    db_session.add(ev)
    await db_session.flush()
    await db_session.refresh(ev)
    assert ev.event_metadata == {"updated_fields": ["title", "description"]}


# ─────────────── M15-MODEL-T3 project_id NULLABLE 全局事件 ───────────────


async def test_activity_log_project_id_nullable_for_global_event(db_session, make_user):
    """M14 baseline-patch 实证：write_event project_id=None 全局豁免业务模块（M14 首发）。"""
    user = await make_user()
    ev = ActivityLog(
        project_id=None,  # 全局
        user_id=user.id,
        action_type="news_created",
        target_type="industry_news",
        target_id="00000000-0000-0000-0000-000000000002",
        summary="录入行业动态：AI 监管",
        event_metadata={"source_type": "manual", "tags_count": 2},
    )
    db_session.add(ev)
    await db_session.flush()
    await db_session.refresh(ev)
    assert ev.project_id is None


# ─────────────── M15-MODEL-T4 action_type CHECK 约束 ───────────────


async def test_activity_log_unknown_action_type_violates_check(db_session, make_user):
    user = await make_user()
    ev = ActivityLog(
        project_id=None,
        user_id=user.id,
        action_type="hacked_action",  # 不在 _ACTION_TYPES 字面 IN 列表
        target_type="project",
        target_id="00000000-0000-0000-0000-000000000003",
        summary="x",
    )
    db_session.add(ev)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M15-MODEL-T5 target_type CHECK 约束 ───────────────


async def test_activity_log_unknown_target_type_violates_check(db_session, make_user):
    user = await make_user()
    ev = ActivityLog(
        project_id=None,
        user_id=user.id,
        action_type="news_created",
        target_type="hacked_target",  # 不在 _TARGET_TYPES
        target_id="00000000-0000-0000-0000-000000000004",
        summary="x",
    )
    db_session.add(ev)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M15-MODEL-T6 ImmutableMixin 无 updated_at ───────────────


def test_activity_log_table_has_no_updated_at_column():
    """ImmutableMixin 仅 created_at；append-only 语义在 schema 层就锁住。"""
    columns = {c.name for c in inspect(ActivityLog).columns}
    assert "created_at" in columns
    assert "updated_at" not in columns


# ─────────────── M15-MODEL-T7 project ON DELETE CASCADE ───────────────


async def test_activity_log_project_cascade_delete(db_session, make_project):
    user, proj = await make_project()
    ev = ActivityLog(
        project_id=proj.id,
        user_id=user.id,
        action_type="project_created",
        target_type="project",
        target_id=str(proj.id),
        summary="创建了项目",
    )
    db_session.add(ev)
    await db_session.flush()
    ev_id = ev.id

    await db_session.execute(delete(Project).where(Project.id == proj.id))
    await db_session.flush()
    rows = (
        (await db_session.execute(select(ActivityLog).where(ActivityLog.id == ev_id)))
        .scalars()
        .all()
    )
    assert rows == []


# ─────────────── M15-MODEL-T8 M14 全局事件字面端到端 ───────────────


async def test_activity_log_m14_news_action_types_pass_check(db_session, make_user):
    """M14 baseline-patch α 路线 5 个过去式 action_type 字面端到端通过 CHECK：
    news_created / news_updated / news_deleted / news_linked / news_unlinked."""
    user = await make_user()
    for at, tt in [
        ("news_created", "industry_news"),
        ("news_updated", "industry_news"),
        ("news_deleted", "industry_news"),
        ("news_linked", "news_node_link"),
        ("news_unlinked", "news_node_link"),
    ]:
        ev = ActivityLog(
            project_id=None,
            user_id=user.id,
            action_type=at,
            target_type=tt,
            target_id="00000000-0000-0000-0000-000000000005",
            summary=f"{at} test",
        )
        db_session.add(ev)
        await db_session.flush()
        await db_session.delete(ev)
        await db_session.flush()


# ─────────────── M15-MODEL-T9 metadata JSONB 嵌套往返 ───────────────


async def test_activity_log_metadata_jsonb_nested_round_trip(db_session, make_project):
    user, proj = await make_project()
    nested = {
        "updated_fields": ["title", "description"],
        "old_values": {"title": "旧标题"},
        "new_values": {"title": "新标题", "tags": ["a", "b"]},
    }
    ev = ActivityLog(
        project_id=proj.id,
        user_id=user.id,
        action_type="node_updated",
        target_type="node",
        target_id="00000000-0000-0000-0000-000000000006",
        summary="x",
        event_metadata=nested,
    )
    db_session.add(ev)
    await db_session.flush()
    await db_session.refresh(ev)

    fetched = (
        (await db_session.execute(select(ActivityLog).where(ActivityLog.id == ev.id)))
        .scalars()
        .one()
    )
    assert fetched.event_metadata == nested
