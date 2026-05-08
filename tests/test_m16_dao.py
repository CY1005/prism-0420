"""M16 子片 2 — AISnapshotTaskDAO 单元测试。

覆盖 design §9：
- get_by_id 双签名（带/不带 user_id）
- find_idempotent 5min 窗口 + status 子集
- create
- cas_start_running CAS（pending→running / 已被抢先返 False）
- cas_complete CAS（running→succeeded/failed / 已被抢先返 False）
- cas_zombie_transition zombie cron（running >11min / pending >2min 一并转 failed）
- delete_expired 清理 cron
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from api.dao.ai_snapshot_task_dao import AISnapshotTaskDAO
from api.models.ai_snapshot_task import AISnapshotTask


@pytest.fixture
def dao():
    return AISnapshotTaskDAO()


# ─────────────── M16-DAO-T1 get_by_id 双签名 ───────────────


async def test_get_by_id_no_user_id_returns_task(
    db_session, dao, make_project, make_node, make_ai_snapshot_task
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    task = await make_ai_snapshot_task(project_id=proj.id, node_id=node.id, user_id=user.id)

    found = await dao.get_by_id(db_session, task.id)
    assert found is not None
    assert found.id == task.id


async def test_get_by_id_with_user_id_filters(
    db_session, dao, make_project, make_node, make_user, make_ai_snapshot_task
):
    """带 user_id 时强制 task.user_id == user_id（cross-user 越权返 None）。"""
    creator, proj = await make_project()
    other = await make_user()
    node = await make_node(proj.id, name="N")
    task = await make_ai_snapshot_task(project_id=proj.id, node_id=node.id, user_id=creator.id)

    # 同 user 拿到
    found = await dao.get_by_id(db_session, task.id, user_id=creator.id)
    assert found is not None
    # 不同 user 拿不到
    not_found = await dao.get_by_id(db_session, task.id, user_id=other.id)
    assert not_found is None


async def test_get_by_id_unknown_id_returns_none(db_session, dao):
    found = await dao.get_by_id(db_session, uuid4())
    assert found is None


# ─────────────── M16-DAO-T2 find_idempotent ───────────────


async def test_find_idempotent_returns_recent_pending(
    db_session, dao, make_project, make_node, make_ai_snapshot_task
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    task = await make_ai_snapshot_task(
        project_id=proj.id, node_id=node.id, user_id=user.id, version_count=3
    )

    found = await dao.find_idempotent(
        db_session, user_id=user.id, project_id=proj.id, node_id=node.id, version_count=3
    )
    assert found is not None
    assert found.id == task.id


async def test_find_idempotent_excludes_failed(
    db_session, dao, make_project, make_node, make_ai_snapshot_task
):
    """failed/cancelled 不复用——用户能立刻重发。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    await make_ai_snapshot_task(
        project_id=proj.id,
        node_id=node.id,
        user_id=user.id,
        version_count=3,
        status="failed",
    )

    found = await dao.find_idempotent(
        db_session, user_id=user.id, project_id=proj.id, node_id=node.id, version_count=3
    )
    assert found is None


async def test_find_idempotent_excludes_old_5min(
    db_session, dao, make_project, make_node, make_ai_snapshot_task
):
    """超过 5 分钟窗口不复用（应当让用户重新触发）。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    task = await make_ai_snapshot_task(
        project_id=proj.id, node_id=node.id, user_id=user.id, version_count=3
    )
    # 改 created_at 到 6 分钟前
    task.created_at = datetime.now(UTC) - timedelta(minutes=6)
    await db_session.flush()

    found = await dao.find_idempotent(
        db_session, user_id=user.id, project_id=proj.id, node_id=node.id, version_count=3
    )
    assert found is None


async def test_find_idempotent_different_version_count(
    db_session, dao, make_project, make_node, make_ai_snapshot_task
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    await make_ai_snapshot_task(
        project_id=proj.id, node_id=node.id, user_id=user.id, version_count=3
    )

    # version_count 不同 → 不复用
    found = await dao.find_idempotent(
        db_session, user_id=user.id, project_id=proj.id, node_id=node.id, version_count=5
    )
    assert found is None


async def test_find_idempotent_different_user(
    db_session, dao, make_project, make_node, make_user, make_ai_snapshot_task
):
    creator, proj = await make_project()
    other = await make_user()
    node = await make_node(proj.id, name="N")
    await make_ai_snapshot_task(
        project_id=proj.id, node_id=node.id, user_id=creator.id, version_count=3
    )

    found = await dao.find_idempotent(
        db_session, user_id=other.id, project_id=proj.id, node_id=node.id, version_count=3
    )
    assert found is None


# ─────────────── M16-DAO-T3 create ───────────────


async def test_create_persists_with_pending_default(db_session, dao, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    task = await dao.create(
        db_session,
        user_id=user.id,
        project_id=proj.id,
        node_id=node.id,
        version_count=3,
        ai_provider="mock",
        ai_model="default",
    )
    assert task.id is not None
    assert task.status == "pending"
    assert task.version_count == 3


# ─────────────── M16-DAO-T4 cas_start_running ───────────────


async def test_cas_start_running_pending_succeeds(
    db_session, dao, make_project, make_node, make_ai_snapshot_task
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    task = await make_ai_snapshot_task(
        project_id=proj.id, node_id=node.id, user_id=user.id, status="pending"
    )

    ok = await dao.cas_start_running(db_session, task_id=task.id)
    assert ok is True
    await db_session.refresh(task)
    refreshed = task
    assert refreshed.status == "running"


async def test_cas_start_running_already_failed_returns_false(
    db_session, dao, make_project, make_node, make_ai_snapshot_task
):
    """cron 抢先转 failed 后，runner CAS 应返 False（design §6 字面纪律 / 防双写）。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    task = await make_ai_snapshot_task(
        project_id=proj.id, node_id=node.id, user_id=user.id, status="failed"
    )

    ok = await dao.cas_start_running(db_session, task_id=task.id)
    assert ok is False


# ─────────────── M16-DAO-T5 cas_complete ───────────────


async def test_cas_complete_running_to_succeeded(
    db_session, dao, make_project, make_node, make_ai_snapshot_task
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    task = await make_ai_snapshot_task(
        project_id=proj.id, node_id=node.id, user_id=user.id, status="running"
    )

    review = {"summary": "ok", "dimensions": []}
    ok = await dao.cas_complete(db_session, task_id=task.id, review_data=review, status="succeeded")
    assert ok is True
    await db_session.refresh(task)
    refreshed = task
    assert refreshed.status == "succeeded"
    assert refreshed.review_data == review
    assert refreshed.completed_at is not None
    assert refreshed.expires_at is not None


async def test_cas_complete_running_to_failed_with_error(
    db_session, dao, make_project, make_node, make_ai_snapshot_task
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    task = await make_ai_snapshot_task(
        project_id=proj.id, node_id=node.id, user_id=user.id, status="running"
    )

    ok = await dao.cas_complete(
        db_session,
        task_id=task.id,
        review_data=None,
        status="failed",
        error_code="snapshot_provider_error",
        error_message="provider 503",
    )
    assert ok is True
    await db_session.refresh(task)
    refreshed = task
    assert refreshed.status == "failed"
    assert refreshed.error_code == "snapshot_provider_error"
    assert refreshed.error_message == "provider 503"


async def test_cas_complete_already_finalized_returns_false(
    db_session, dao, make_project, make_node, make_ai_snapshot_task
):
    """cron 抢先转 failed 后，runner cas_complete 应返 False（防双写终态事件）。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    task = await make_ai_snapshot_task(
        project_id=proj.id, node_id=node.id, user_id=user.id, status="failed"
    )

    ok = await dao.cas_complete(db_session, task_id=task.id, review_data={}, status="succeeded")
    assert ok is False


# ─────────────── M16-DAO-T6 cas_zombie_transition ───────────────


async def test_cas_zombie_transitions_running_over_threshold(
    db_session, dao, make_project, make_node, make_ai_snapshot_task
):
    """status='running' AND created_at < NOW-11min → failed/SNAPSHOT_ZOMBIE。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    task = await make_ai_snapshot_task(
        project_id=proj.id, node_id=node.id, user_id=user.id, status="running"
    )
    task.created_at = datetime.now(UTC) - timedelta(minutes=15)
    await db_session.flush()
    await db_session.commit()  # zombie cron 跑前提交（cron 看到的视图）

    ids = await dao.cas_zombie_transition(db_session)
    assert task.id in ids

    await db_session.refresh(task)
    refreshed = task
    assert refreshed.status == "failed"
    assert refreshed.error_code == "snapshot_zombie"


async def test_cas_zombie_transitions_pending_over_threshold(
    db_session, dao, make_project, make_node, make_ai_snapshot_task
):
    """status='pending' AND created_at < NOW-2min → failed/SNAPSHOT_ZOMBIE
    （audit m1+m6 修复 / add_task 失败 + OOM 时孤儿 pending 也被抓）。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    task = await make_ai_snapshot_task(
        project_id=proj.id, node_id=node.id, user_id=user.id, status="pending"
    )
    task.created_at = datetime.now(UTC) - timedelta(minutes=5)
    await db_session.flush()
    await db_session.commit()

    ids = await dao.cas_zombie_transition(db_session)
    assert task.id in ids


async def test_cas_zombie_does_not_touch_recent_running(
    db_session, dao, make_project, make_node, make_ai_snapshot_task
):
    """status='running' AND created_at < NOW-2min（仍在 11min 阈值内）→ 不转。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    task = await make_ai_snapshot_task(
        project_id=proj.id, node_id=node.id, user_id=user.id, status="running"
    )
    # 仍在 running 阈值内（< 11min）
    task.created_at = datetime.now(UTC) - timedelta(minutes=5)
    await db_session.flush()
    await db_session.commit()

    ids = await dao.cas_zombie_transition(db_session)
    assert task.id not in ids


# ─────────────── M16-DAO-T7 delete_expired ───────────────


async def test_delete_expired_removes_old_rows(
    db_session, dao, make_project, make_node, make_ai_snapshot_task
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    expired_task = await make_ai_snapshot_task(
        project_id=proj.id,
        node_id=node.id,
        user_id=user.id,
        status="succeeded",
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    fresh_task = await make_ai_snapshot_task(
        project_id=proj.id,
        node_id=node.id,
        user_id=user.id,
        status="succeeded",
        expires_at=datetime.now(UTC) + timedelta(days=10),
    )
    await db_session.commit()

    deleted = await dao.delete_expired(db_session)
    assert deleted >= 1

    found_expired = await db_session.scalar(
        select(AISnapshotTask).where(AISnapshotTask.id == expired_task.id)
    )
    found_fresh = await db_session.scalar(
        select(AISnapshotTask).where(AISnapshotTask.id == fresh_task.id)
    )
    assert found_expired is None
    assert found_fresh is not None
