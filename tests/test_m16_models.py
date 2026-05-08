"""M16 子片 1 — AISnapshotTask model 单元测试。

覆盖 design §3 SQLAlchemy block + §12B 字段①：
- 持久化 + 默认值（status=pending）
- status CHECK 5 状态枚举（拒非法值）
- ON DELETE CASCADE on projects.id / nodes.id
- review_data JSONB 大字段（AI 输出 dict）
- expires_at 任务清理用
- 多任务同 (user, project, node, version_count) 5min 内允许（无 UniqueConstraint，
  audit B1 修复 / 幂等走 advisory_xact_lock 而非 DB 约束）
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.models.ai_snapshot_task import AISnapshotTask, AISnapshotTaskStatus

# ─────────────── M16-MODEL-T1 持久化基础 + 默认值 ───────────────


async def test_ai_snapshot_persists_with_defaults(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="N1")
    task = AISnapshotTask(
        project_id=proj.id,
        node_id=node.id,
        user_id=user.id,
        version_count=3,
        ai_provider="mock",
        ai_model="default",
    )
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)

    assert task.id is not None
    assert task.status == AISnapshotTaskStatus.pending.value
    assert task.version_count == 3
    assert task.review_data is None
    assert task.error_message is None
    assert task.error_code is None
    assert task.completed_at is None
    assert task.expires_at is None
    assert task.created_at is not None


# ─────────────── M16-MODEL-T2 status CHECK 5 状态合法 ───────────────


@pytest.mark.parametrize(
    "status_value",
    ["pending", "running", "succeeded", "failed", "cancelled"],
)
async def test_ai_snapshot_all_5_statuses_allowed(
    db_session, make_project, make_node, status_value
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    task = AISnapshotTask(
        project_id=proj.id,
        node_id=node.id,
        user_id=user.id,
        status=status_value,
        version_count=3,
        ai_provider="mock",
        ai_model="default",
    )
    db_session.add(task)
    await db_session.flush()  # 不应抛


async def test_ai_snapshot_invalid_status_violates(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    task = AISnapshotTask(
        project_id=proj.id,
        node_id=node.id,
        user_id=user.id,
        status="bogus_state",
        version_count=3,
        ai_provider="mock",
        ai_model="default",
    )
    db_session.add(task)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M16-MODEL-T3 cascade on project delete ───────────────


async def test_ai_snapshot_cascade_when_project_deleted(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    task = AISnapshotTask(
        project_id=proj.id,
        node_id=node.id,
        user_id=user.id,
        version_count=3,
        ai_provider="mock",
        ai_model="default",
    )
    db_session.add(task)
    await db_session.flush()
    tid = task.id

    await db_session.delete(proj)
    await db_session.flush()
    db_session.expire_all()

    found = await db_session.scalar(select(AISnapshotTask).where(AISnapshotTask.id == tid))
    assert found is None, "project 删除应级联删 ai_snapshot_task"


# ─────────────── M16-MODEL-T4 cascade on node delete ───────────────


async def test_ai_snapshot_cascade_when_node_deleted(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    task = AISnapshotTask(
        project_id=proj.id,
        node_id=node.id,
        user_id=user.id,
        version_count=3,
        ai_provider="mock",
        ai_model="default",
    )
    db_session.add(task)
    await db_session.flush()
    tid = task.id

    await db_session.delete(node)
    await db_session.flush()
    db_session.expire_all()

    found = await db_session.scalar(select(AISnapshotTask).where(AISnapshotTask.id == tid))
    assert found is None, "node 删除应级联删 ai_snapshot_task"


# ─────────────── M16-MODEL-T5 review_data JSONB ───────────────


async def test_ai_snapshot_review_data_jsonb(db_session, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    review = {
        "summary": "AI 一句话快照",
        "dimensions": [
            {"key": "biz_objective", "name": "业务目标", "content": "提升 GMV"},
            {"key": "user_pain", "name": "用户痛点", "content": "审批慢"},
        ],
    }
    task = AISnapshotTask(
        project_id=proj.id,
        node_id=node.id,
        user_id=user.id,
        status="succeeded",
        version_count=5,
        ai_provider="claude",
        ai_model="claude-opus-4-7",
        review_data=review,
        completed_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)
    assert task.review_data == review
    assert task.review_data["summary"] == "AI 一句话快照"


# ─────────────── M16-MODEL-T6 多任务同 (user, project, node) 5min 允许（无 UniqueConstraint） ───────────────


async def test_ai_snapshot_multiple_concurrent_allowed(db_session, make_project, make_node):
    """audit B1 修复 / 幂等走 advisory_xact_lock 而非 DB UniqueConstraint。
    DB 层不阻止重复（业务幂等含 5min 时间窗口 + status 子集 PG immutable 不支持）。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    db_session.add_all(
        [
            AISnapshotTask(
                project_id=proj.id,
                node_id=node.id,
                user_id=user.id,
                version_count=3,
                ai_provider="mock",
                ai_model="default",
            ),
            AISnapshotTask(
                project_id=proj.id,
                node_id=node.id,
                user_id=user.id,
                version_count=3,
                ai_provider="mock",
                ai_model="default",
            ),
        ]
    )
    await db_session.flush()  # 不应抛


# ─────────────── M16-MODEL-T7 unknown user_id 违反 FK ───────────────


async def test_ai_snapshot_unknown_user_violates_fk(db_session, make_project, make_node):
    _user, proj = await make_project()
    node = await make_node(proj.id, name="N")
    task = AISnapshotTask(
        project_id=proj.id,
        node_id=node.id,
        user_id=uuid4(),  # 不存在的 user
        version_count=3,
        ai_provider="mock",
        ai_model="default",
    )
    db_session.add(task)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M16-MODEL-T8 R14 横切 enum owner 同步：CHECK 含新 ActionType+TargetType ───────────────


def test_action_type_enum_includes_m16_values():
    """M15 NEW 元教训：横切表 owner 模块的 enum 字面同步责任（4 处必同步）。
    本测试守护 model._ACTION_TYPES 含 M16 新增 3 值（model + schema + CHECK + 测试）。"""
    from api.models.activity_log import _ACTION_TYPES

    m16_actions = {"ai_snapshot_started", "ai_snapshot_completed", "ai_snapshot_failed"}
    assert m16_actions <= set(_ACTION_TYPES), (
        f"_ACTION_TYPES 缺 M16 值：{m16_actions - set(_ACTION_TYPES)}"
    )


def test_target_type_enum_includes_m16_value():
    """M15 NEW 元教训：横切 TargetType 同步：M16 新增 ai_snapshot_task。"""
    from api.models.activity_log import _TARGET_TYPES

    assert "ai_snapshot_task" in _TARGET_TYPES


def test_schema_action_type_strenum_synced_with_model():
    """4 处同步对账：schema StrEnum 与 model._ACTION_TYPES 字面一致。"""
    from api.models.activity_log import _ACTION_TYPES
    from api.schemas.activity_stream_schema import ActionType

    assert set(_ACTION_TYPES) == {a.value for a in ActionType}


def test_schema_target_type_strenum_synced_with_model():
    from api.models.activity_log import _TARGET_TYPES
    from api.schemas.activity_stream_schema import TargetType

    assert set(_TARGET_TYPES) == {t.value for t in TargetType}
