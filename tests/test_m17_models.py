"""M17 子片 1 — ImportTask + ImportTaskItem model 单元测试。

覆盖 design §3 SQLAlchemy block + §12 Queue payload：
- 持久化 + 默认值（status=pending / progress=0 / retry_count=0）
- status CHECK 11 状态主表 + 5 状态明细表（拒非法值）
- source_type CHECK 3 形态（zip/git_url/git_bundle）
- UNIQUE(user_id, project_id, source_hash) idempotency 约束（B1 修复）
- ON DELETE CASCADE：project → import_task → item
- ON DELETE SET NULL：node → item.target_node_id（review 后映射的目标 node 删除时不丢 item）
- review_data / ai_output JSONB 大字段
- expires_at 双用：① idempotency 7 天 ② 死信 30 天
- M17 ActionType +8 / TargetType +1 同步对账（M15 NEW 4 处同步责任）
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.models.import_task import (
    ImportSourceType,
    ImportTask,
    ImportTaskItem,
    ImportTaskItemStatus,
    ImportTaskStatus,
)


def _make_task_kwargs(*, project_id, user_id, source_hash="abc123", **overrides):
    base = {
        "project_id": project_id,
        "user_id": user_id,
        "source_type": ImportSourceType.zip.value,
        "source_hash": source_hash,
        "source_uri": "s3://prism/imports/abc.zip",
        "ai_provider": "claude",
        "ai_model": "claude-opus-4-7",
    }
    base.update(overrides)
    return base


# ─────────────── M17-MODEL-T1 持久化基础 + 默认值 ───────────────


async def test_import_task_persists_with_defaults(db_session, make_project):
    user, proj = await make_project()
    task = ImportTask(**_make_task_kwargs(project_id=proj.id, user_id=user.id))
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)

    assert task.id is not None
    assert task.status == ImportTaskStatus.pending.value
    assert task.progress == 0
    assert task.error_message is None
    assert task.error_metadata is None
    assert task.review_data is None
    assert task.completed_at is None
    assert task.expires_at is None
    assert task.created_at is not None


# ─────────────── M17-MODEL-T2 11 状态合法 + 非法拒 ───────────────


@pytest.mark.parametrize(
    "status_value",
    [
        "pending",
        "extracting",
        "ai_step1",
        "ai_step2",
        "ai_step3",
        "awaiting_review",
        "importing",
        "completed",
        "partial_failed",
        "failed",
        "cancelled",
    ],
)
async def test_import_task_all_11_statuses_allowed(db_session, make_project, status_value):
    user, proj = await make_project()
    task = ImportTask(**_make_task_kwargs(project_id=proj.id, user_id=user.id, status=status_value))
    db_session.add(task)
    await db_session.flush()  # 不应抛


async def test_import_task_invalid_status_violates(db_session, make_project):
    user, proj = await make_project()
    task = ImportTask(
        **_make_task_kwargs(project_id=proj.id, user_id=user.id, status="bogus_state")
    )
    db_session.add(task)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M17-MODEL-T3 source_type CHECK 3 形态 ───────────────


@pytest.mark.parametrize("source_type_value", ["zip", "git_url", "git_bundle"])
async def test_import_task_all_3_source_types_allowed(db_session, make_project, source_type_value):
    user, proj = await make_project()
    task = ImportTask(
        **_make_task_kwargs(project_id=proj.id, user_id=user.id, source_type=source_type_value)
    )
    db_session.add(task)
    await db_session.flush()


async def test_import_task_invalid_source_type_violates(db_session, make_project):
    user, proj = await make_project()
    task = ImportTask(**_make_task_kwargs(project_id=proj.id, user_id=user.id, source_type="rar"))
    db_session.add(task)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M17-MODEL-T4 idempotency UNIQUE(user, project, source_hash) ───────────────


async def test_import_task_idempotency_unique_violates_on_duplicate(db_session, make_project):
    """B1 修复：同一 user + 同一 project + 同一 source_hash 触发 UNIQUE 冲突。"""
    user, proj = await make_project()
    db_session.add(
        ImportTask(**_make_task_kwargs(project_id=proj.id, user_id=user.id, source_hash="H1"))
    )
    await db_session.flush()
    db_session.add(
        ImportTask(**_make_task_kwargs(project_id=proj.id, user_id=user.id, source_hash="H1"))
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_import_task_idempotency_different_project_allowed(
    db_session, make_user, make_project
):
    """B1 修复：同一 user + 同一 source_hash 但不同 project 不冲突。"""
    user = await make_user()
    _u1, p1 = await make_project(owner=user)
    _u2, p2 = await make_project(owner=user)
    db_session.add(
        ImportTask(**_make_task_kwargs(project_id=p1.id, user_id=user.id, source_hash="H"))
    )
    db_session.add(
        ImportTask(**_make_task_kwargs(project_id=p2.id, user_id=user.id, source_hash="H"))
    )
    await db_session.flush()  # 不应抛


# ─────────────── M17-MODEL-T5 cascade on project delete ───────────────


async def test_import_task_cascade_when_project_deleted(db_session, make_project):
    user, proj = await make_project()
    task = ImportTask(**_make_task_kwargs(project_id=proj.id, user_id=user.id))
    db_session.add(task)
    await db_session.flush()
    tid = task.id

    await db_session.delete(proj)
    await db_session.flush()
    db_session.expire_all()

    found = await db_session.scalar(select(ImportTask).where(ImportTask.id == tid))
    assert found is None, "project 删除应级联删 import_task"


# ─────────────── M17-MODEL-T6 unknown user FK ───────────────


async def test_import_task_unknown_user_violates_fk(db_session, make_project):
    _user, proj = await make_project()
    task = ImportTask(**_make_task_kwargs(project_id=proj.id, user_id=uuid4()))
    db_session.add(task)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M17-MODEL-T7 review_data / ai_output JSONB 大字段 ───────────────


async def test_import_task_review_data_jsonb(db_session, make_project):
    user, proj = await make_project()
    review = {
        "proposed_nodes": [
            {"id": str(uuid4()), "name": "Auth"},
            {"id": str(uuid4()), "name": "Billing"},
        ],
        "confidence_scores": {"Auth": 0.92, "Billing": 0.78},
    }
    task = ImportTask(
        **_make_task_kwargs(
            project_id=proj.id,
            user_id=user.id,
            review_data=review,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
    )
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)
    assert task.review_data == review
    assert task.review_data["confidence_scores"]["Auth"] == 0.92


# ─────────────── M17-ITEM-T1 item 持久化 + 默认值 ───────────────


async def test_import_item_persists_with_defaults(db_session, make_project):
    user, proj = await make_project()
    task = ImportTask(**_make_task_kwargs(project_id=proj.id, user_id=user.id))
    db_session.add(task)
    await db_session.flush()
    item = ImportTaskItem(
        task_id=task.id,
        file_path="src/auth/login.py",
        file_size=1024,
    )
    db_session.add(item)
    await db_session.flush()
    await db_session.refresh(item)
    assert item.id is not None
    assert item.status == ImportTaskItemStatus.pending.value
    assert item.retry_count == 0
    assert item.target_node_id is None
    assert item.error_message is None
    assert item.created_at is not None


# ─────────────── M17-ITEM-T2 item 5 状态合法 + 非法拒 ───────────────


@pytest.mark.parametrize(
    "status_value", ["pending", "processing", "completed", "failed", "skipped"]
)
async def test_import_item_all_5_statuses_allowed(db_session, make_project, status_value):
    user, proj = await make_project()
    task = ImportTask(**_make_task_kwargs(project_id=proj.id, user_id=user.id))
    db_session.add(task)
    await db_session.flush()
    item = ImportTaskItem(
        task_id=task.id,
        file_path="x.py",
        file_size=1,
        status=status_value,
    )
    db_session.add(item)
    await db_session.flush()


async def test_import_item_invalid_status_violates(db_session, make_project):
    user, proj = await make_project()
    task = ImportTask(**_make_task_kwargs(project_id=proj.id, user_id=user.id))
    db_session.add(task)
    await db_session.flush()
    item = ImportTaskItem(task_id=task.id, file_path="x", file_size=1, status="bogus")
    db_session.add(item)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M17-ITEM-T3 cascade on task delete ───────────────


async def test_import_item_cascade_when_task_deleted(db_session, make_project):
    user, proj = await make_project()
    task = ImportTask(**_make_task_kwargs(project_id=proj.id, user_id=user.id))
    db_session.add(task)
    await db_session.flush()
    item = ImportTaskItem(task_id=task.id, file_path="x", file_size=1)
    db_session.add(item)
    await db_session.flush()
    iid = item.id

    await db_session.delete(task)
    await db_session.flush()
    db_session.expire_all()

    found = await db_session.scalar(select(ImportTaskItem).where(ImportTaskItem.id == iid))
    assert found is None, "task 删除应级联删 item"


# ─────────────── M17-ITEM-T4 SET NULL on node delete (target_node_id) ───────────────


async def test_import_item_target_node_set_null_when_node_deleted(
    db_session, make_project, make_node
):
    """review 后用户决定的目标 node 删除时，item.target_node_id 设为 NULL（不丢 item）。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="Target")
    task = ImportTask(**_make_task_kwargs(project_id=proj.id, user_id=user.id))
    db_session.add(task)
    await db_session.flush()
    item = ImportTaskItem(task_id=task.id, file_path="x", file_size=1, target_node_id=node.id)
    db_session.add(item)
    await db_session.flush()
    iid = item.id

    await db_session.delete(node)
    await db_session.flush()
    db_session.expire_all()

    found = await db_session.scalar(select(ImportTaskItem).where(ImportTaskItem.id == iid))
    assert found is not None, "node 删除时不应级联删 item（SET NULL 语义）"
    assert found.target_node_id is None


# ─────────────── M17-ITEM-T5 ai_output JSONB ───────────────


async def test_import_item_ai_output_jsonb(db_session, make_project):
    user, proj = await make_project()
    task = ImportTask(**_make_task_kwargs(project_id=proj.id, user_id=user.id))
    db_session.add(task)
    await db_session.flush()
    output = {
        "extracted_dimensions": [{"key": "biz_objective", "content": "Auth"}],
        "suggested_node_path": "/Auth/Login",
    }
    item = ImportTaskItem(
        task_id=task.id, file_path="src/auth/login.py", file_size=2048, ai_output=output
    )
    db_session.add(item)
    await db_session.flush()
    await db_session.refresh(item)
    assert item.ai_output == output


# ─────────────── M17-MODEL-T8 R14 横切 enum owner 同步：CHECK 含新 ActionType+TargetType ───────────────


def test_action_type_enum_includes_m17_values():
    """M15 NEW 元教训：横切表 owner 模块的 enum 字面同步责任（4 处必同步）。
    本测试守护 model._ACTION_TYPES 含 M17 新增 8 值（model + schema + CHECK + 测试）。"""
    from api.models.activity_log import _ACTION_TYPES

    m17_actions = {
        "import_created",
        "import_status_changed",
        "import_ai_step_completed",
        "import_review_confirmed",
        "import_batch_inserted",
        "import_canceled",
        "import_failed",
        "import_partial_failed",
    }
    assert m17_actions <= set(_ACTION_TYPES), (
        f"_ACTION_TYPES 缺 M17 值：{m17_actions - set(_ACTION_TYPES)}"
    )


def test_target_type_enum_includes_m17_value():
    from api.models.activity_log import _TARGET_TYPES

    assert "import_task" in _TARGET_TYPES


def test_schema_action_type_strenum_synced_with_model_for_m17():
    """4 处同步对账：schema StrEnum 与 model._ACTION_TYPES 字面一致（含 M17 新值）。"""
    from api.models.activity_log import _ACTION_TYPES
    from api.schemas.activity_stream_schema import ActionType

    assert set(_ACTION_TYPES) == {a.value for a in ActionType}


def test_schema_target_type_strenum_synced_with_model_for_m17():
    from api.models.activity_log import _TARGET_TYPES
    from api.schemas.activity_stream_schema import TargetType

    assert set(_TARGET_TYPES) == {t.value for t in TargetType}
