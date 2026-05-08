"""M11 子片 1 — ColdStartTask model 单元测试。

覆盖 design §3 SQLAlchemy block：
- 持久化 + 默认值（status=pending / total_rows=0 / success_rows=0 / failed_rows=0）
- status CHECK 约束（5 状态枚举 / 拒非法值）
- ON DELETE CASCADE on projects.id
- error_report JSONB 行级错误结构
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.models.cold_start_task import ColdStartStatus, ColdStartTask

# ─────────────── M11-MODEL-T1 持久化基础 + 默认值 ───────────────


async def test_cold_start_task_persists_with_defaults(db_session, make_project):
    user, proj = await make_project()
    task = ColdStartTask(
        project_id=proj.id,
        user_id=user.id,
        source_hash="abc123",
        source_filename="modules.csv",
    )
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)

    assert task.id is not None
    assert task.status == ColdStartStatus.PENDING.value
    assert task.total_rows == 0
    assert task.success_rows == 0
    assert task.failed_rows == 0
    assert task.error_report is None
    assert task.completed_at is None
    assert task.created_at is not None
    assert task.updated_at is not None


# ─────────────── M11-MODEL-T2 status CHECK 5 状态合法 ───────────────


@pytest.mark.parametrize(
    "status_value",
    ["pending", "validating", "importing", "completed", "failed"],
)
async def test_cold_start_task_all_5_statuses_allowed(db_session, make_project, status_value):
    user, proj = await make_project()
    task = ColdStartTask(
        project_id=proj.id,
        user_id=user.id,
        source_hash=f"h-{status_value}",
        source_filename="x.csv",
        status=status_value,
    )
    db_session.add(task)
    await db_session.flush()  # 不应抛


async def test_cold_start_task_invalid_status_violates(db_session, make_project):
    """G6 移除 partial_failed → 写入 'partial_failed' 应被 CHECK 拒绝。"""
    user, proj = await make_project()
    task = ColdStartTask(
        project_id=proj.id,
        user_id=user.id,
        source_hash="h",
        source_filename="x.csv",
        status="partial_failed",
    )
    db_session.add(task)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M11-MODEL-T3 cascade on project delete ───────────────


async def test_cold_start_task_cascade_when_project_deleted(db_session, make_project):
    user, proj = await make_project()
    task = ColdStartTask(
        project_id=proj.id,
        user_id=user.id,
        source_hash="h",
        source_filename="x.csv",
    )
    db_session.add(task)
    await db_session.flush()
    tid = task.id

    await db_session.delete(proj)
    await db_session.flush()
    db_session.expire_all()

    found = await db_session.scalar(select(ColdStartTask).where(ColdStartTask.id == tid))
    assert found is None, "project 删除应级联删 cold_start_task"


# ─────────────── M11-MODEL-T4 error_report JSONB 行级错误 ───────────────


async def test_cold_start_task_error_report_jsonb(db_session, make_project):
    user, proj = await make_project()
    error_rows = [
        {"row": 3, "field": "node_path", "message": "missing parent"},
        {"row": 7, "field": "dimension_value", "message": "exceeds max length"},
    ]
    task = ColdStartTask(
        project_id=proj.id,
        user_id=user.id,
        source_hash="h",
        source_filename="x.csv",
        status=ColdStartStatus.FAILED.value,
        total_rows=10,
        success_rows=0,
        failed_rows=2,
        error_report=error_rows,
    )
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)

    assert task.error_report == error_rows
    assert task.failed_rows == 2


# ─────────────── M11-MODEL-T5 multi rows per (user, project) 允许 ───────────────


async def test_cold_start_task_multiple_per_user_project_allowed(db_session, make_project):
    """G2/G6：无 idempotency；同 user + project + source_hash 可建多条。"""
    user, proj = await make_project()
    same_hash = "deadbeef"
    db_session.add_all(
        [
            ColdStartTask(
                project_id=proj.id,
                user_id=user.id,
                source_hash=same_hash,
                source_filename="a.csv",
            ),
            ColdStartTask(
                project_id=proj.id,
                user_id=user.id,
                source_hash=same_hash,
                source_filename="a.csv",
            ),
        ]
    )
    await db_session.flush()  # 不应抛 — 无 UNIQUE 约束


# ─────────────── M11-MODEL-T6 project_id NOT NULL ───────────────


async def test_cold_start_task_project_id_required(db_session, make_user):
    user = await make_user()
    task = ColdStartTask(
        project_id=None,  # type: ignore[arg-type]
        user_id=user.id,
        source_hash="h",
        source_filename="x.csv",
    )
    db_session.add(task)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M11-MODEL-T7 user_id NOT NULL ───────────────


async def test_cold_start_task_user_id_required(db_session, make_project):
    _user, proj = await make_project()
    task = ColdStartTask(
        project_id=proj.id,
        user_id=None,  # type: ignore[arg-type]
        source_hash="h",
        source_filename="x.csv",
    )
    db_session.add(task)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M11-MODEL-T8 status default = pending ───────────────


async def test_cold_start_task_status_default_pending(db_session, make_project):
    user, proj = await make_project()
    # 不显式传 status
    task = ColdStartTask(
        project_id=proj.id,
        user_id=user.id,
        source_hash="h",
        source_filename="x.csv",
    )
    db_session.add(task)
    await db_session.flush()
    assert task.status == ColdStartStatus.PENDING.value


# ─────────────── M11-MODEL-T9 unknown user_id 违反 FK ───────────────


async def test_cold_start_task_unknown_user_violates_fk(db_session, make_project):
    _user, proj = await make_project()
    task = ColdStartTask(
        project_id=proj.id,
        user_id=uuid4(),  # 不存在的 user
        source_hash="h",
        source_filename="x.csv",
    )
    db_session.add(task)
    with pytest.raises(IntegrityError):
        await db_session.flush()
