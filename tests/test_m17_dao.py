"""M17 子片 2 — ImportTaskDAO + ImportTaskItemDAO 测试。

覆盖 design §9 主查询模式 + tenant 过滤 + user 过滤 + idempotency 7 天窗口 + dead_letter
30 天清理 + CRUD。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from api.dao.import_task_dao import ImportTaskDAO, ImportTaskItemDAO
from api.models.import_task import (
    ImportSourceType,
    ImportTask,
    ImportTaskItem,
    ImportTaskStatus,
)


@pytest.fixture
def dao():
    return ImportTaskDAO()


@pytest.fixture
def item_dao():
    return ImportTaskItemDAO()


def _task_kwargs(*, project_id, user_id, source_hash="H", **overrides):
    base = {
        "project_id": project_id,
        "user_id": user_id,
        "source_type": ImportSourceType.zip.value,
        "source_hash": source_hash,
        "source_uri": "s3://x.zip",
        "ai_provider": "claude",
        "ai_model": "claude-opus-4-7",
    }
    base.update(overrides)
    return base


# ─────────────── DAO-T1 list_by_project（user + project tenant） ───────────────


async def test_dao_list_by_project_returns_user_tasks_desc(db_session, dao, make_project):
    user, proj = await make_project()
    t1 = ImportTask(**_task_kwargs(project_id=proj.id, user_id=user.id, source_hash="A"))
    t2 = ImportTask(**_task_kwargs(project_id=proj.id, user_id=user.id, source_hash="B"))
    db_session.add_all([t1, t2])
    await db_session.flush()
    # 手动设 created_at 控制顺序
    t1.created_at = datetime.now(UTC) - timedelta(minutes=5)
    t2.created_at = datetime.now(UTC)
    await db_session.flush()

    rows = await dao.list_by_project(db_session, project_id=proj.id, user_id=user.id)
    assert [r.id for r in rows] == [t2.id, t1.id]


async def test_dao_list_by_project_excludes_other_user(db_session, dao, make_user, make_project):
    """同 project 不同 user 的任务不应回来（per-user view）。"""
    owner = await make_user()
    other = await make_user()
    _u, proj = await make_project(owner=owner)
    db_session.add(
        ImportTask(**_task_kwargs(project_id=proj.id, user_id=owner.id, source_hash="A"))
    )
    db_session.add(
        ImportTask(**_task_kwargs(project_id=proj.id, user_id=other.id, source_hash="B"))
    )
    await db_session.flush()

    rows = await dao.list_by_project(db_session, project_id=proj.id, user_id=owner.id)
    assert len(rows) == 1
    assert rows[0].user_id == owner.id


async def test_dao_list_by_project_excludes_other_project(db_session, dao, make_project):
    user, p1 = await make_project()
    _u, p2 = await make_project(owner=user)
    db_session.add(ImportTask(**_task_kwargs(project_id=p1.id, user_id=user.id, source_hash="A")))
    db_session.add(ImportTask(**_task_kwargs(project_id=p2.id, user_id=user.id, source_hash="B")))
    await db_session.flush()

    rows = await dao.list_by_project(db_session, project_id=p1.id, user_id=user.id)
    assert len(rows) == 1
    assert rows[0].project_id == p1.id


# ─────────────── DAO-T2 get_by_id（tenant 过滤） ───────────────


async def test_dao_get_by_id_returns_task(db_session, dao, make_project):
    user, proj = await make_project()
    task = ImportTask(**_task_kwargs(project_id=proj.id, user_id=user.id))
    db_session.add(task)
    await db_session.flush()

    got = await dao.get_by_id(db_session, task.id, proj.id)
    assert got is not None
    assert got.id == task.id


async def test_dao_get_by_id_cross_project_returns_none(db_session, dao, make_project):
    """跨 project 查询返 None（service 层转 404）。"""
    user, p1 = await make_project()
    _u, p2 = await make_project(owner=user)
    task = ImportTask(**_task_kwargs(project_id=p1.id, user_id=user.id))
    db_session.add(task)
    await db_session.flush()

    got = await dao.get_by_id(db_session, task.id, p2.id)
    assert got is None


# ─────────────── DAO-T3 find_idempotent ───────────────


async def test_dao_find_idempotent_returns_completed_task(db_session, dao, make_project):
    """7 天内 + status=completed 的同 user/project/hash 任务命中复用。"""
    user, proj = await make_project()
    task = ImportTask(
        **_task_kwargs(
            project_id=proj.id,
            user_id=user.id,
            source_hash="HASH-X",
            status=ImportTaskStatus.completed.value,
        )
    )
    db_session.add(task)
    await db_session.flush()

    hit = await dao.find_idempotent(
        db_session, user_id=user.id, project_id=proj.id, source_hash="HASH-X"
    )
    assert hit is not None
    assert hit.id == task.id


@pytest.mark.parametrize(
    "reusable_status",
    ["completed", "awaiting_review", "partial_failed"],
)
async def test_dao_find_idempotent_reuses_3_statuses(
    db_session, dao, make_project, reusable_status
):
    user, proj = await make_project()
    task = ImportTask(
        **_task_kwargs(
            project_id=proj.id,
            user_id=user.id,
            source_hash=f"H-{reusable_status}",
            status=reusable_status,
        )
    )
    db_session.add(task)
    await db_session.flush()

    hit = await dao.find_idempotent(
        db_session,
        user_id=user.id,
        project_id=proj.id,
        source_hash=f"H-{reusable_status}",
    )
    assert hit is not None


@pytest.mark.parametrize("non_reusable", ["failed", "cancelled", "pending", "ai_step1"])
async def test_dao_find_idempotent_skips_non_reusable_statuses(
    db_session, dao, make_project, non_reusable
):
    user, proj = await make_project()
    task = ImportTask(
        **_task_kwargs(
            project_id=proj.id,
            user_id=user.id,
            source_hash=f"H-{non_reusable}",
            status=non_reusable,
        )
    )
    db_session.add(task)
    await db_session.flush()

    hit = await dao.find_idempotent(
        db_session,
        user_id=user.id,
        project_id=proj.id,
        source_hash=f"H-{non_reusable}",
    )
    assert hit is None


async def test_dao_find_idempotent_skips_expired(db_session, dao, make_project):
    """8 天前的 completed 任务超出 7 天窗口不复用。"""
    user, proj = await make_project()
    task = ImportTask(
        **_task_kwargs(
            project_id=proj.id,
            user_id=user.id,
            source_hash="OLD",
            status=ImportTaskStatus.completed.value,
        )
    )
    db_session.add(task)
    await db_session.flush()
    task.created_at = datetime.now(UTC) - timedelta(days=8)
    await db_session.flush()

    hit = await dao.find_idempotent(
        db_session, user_id=user.id, project_id=proj.id, source_hash="OLD"
    )
    assert hit is None


async def test_dao_find_idempotent_isolates_by_project(db_session, dao, make_user, make_project):
    """B1 修复：同 user 同 hash 但不同 project 不命中（防跨租户污染）。"""
    user = await make_user()
    _u1, p1 = await make_project(owner=user)
    _u2, p2 = await make_project(owner=user)
    task = ImportTask(
        **_task_kwargs(
            project_id=p1.id,
            user_id=user.id,
            source_hash="SHARED-HASH",
            status=ImportTaskStatus.completed.value,
        )
    )
    db_session.add(task)
    await db_session.flush()

    # 同 user 同 hash 但查 p2 → 不命中
    hit = await dao.find_idempotent(
        db_session, user_id=user.id, project_id=p2.id, source_hash="SHARED-HASH"
    )
    assert hit is None

    # 查 p1 → 命中
    hit = await dao.find_idempotent(
        db_session, user_id=user.id, project_id=p1.id, source_hash="SHARED-HASH"
    )
    assert hit is not None


async def test_dao_find_idempotent_isolates_by_user(db_session, dao, make_user, make_project):
    user_a = await make_user()
    user_b = await make_user()
    _u, proj = await make_project(owner=user_a)
    task = ImportTask(
        **_task_kwargs(
            project_id=proj.id,
            user_id=user_a.id,
            source_hash="UH",
            status=ImportTaskStatus.completed.value,
        )
    )
    db_session.add(task)
    await db_session.flush()

    hit = await dao.find_idempotent(
        db_session, user_id=user_b.id, project_id=proj.id, source_hash="UH"
    )
    assert hit is None


# ─────────────── DAO-T4 find_dead_letter_orphans（zombie cron） ───────────────


async def test_dao_find_dead_letter_orphans_returns_old_failed(db_session, dao, make_project):
    """status=failed 且 created_at < NOW - 30d 应被列出。"""
    user, proj = await make_project()
    old_task = ImportTask(
        **_task_kwargs(
            project_id=proj.id,
            user_id=user.id,
            source_hash="DL-OLD",
            status=ImportTaskStatus.failed.value,
        )
    )
    fresh_task = ImportTask(
        **_task_kwargs(
            project_id=proj.id,
            user_id=user.id,
            source_hash="DL-FRESH",
            status=ImportTaskStatus.failed.value,
        )
    )
    db_session.add_all([old_task, fresh_task])
    await db_session.flush()
    old_task.created_at = datetime.now(UTC) - timedelta(days=31)
    fresh_task.created_at = datetime.now(UTC) - timedelta(days=5)
    await db_session.flush()

    rows = await dao.find_dead_letter_orphans(db_session)
    ids = {r.id for r in rows}
    assert old_task.id in ids
    assert fresh_task.id not in ids


async def test_dao_find_dead_letter_orphans_skips_non_failed_states(db_session, dao, make_project):
    """completed 30 天前的也不应被清（只清 failed 死信）。"""
    user, proj = await make_project()
    completed_old = ImportTask(
        **_task_kwargs(
            project_id=proj.id,
            user_id=user.id,
            source_hash="C-OLD",
            status=ImportTaskStatus.completed.value,
        )
    )
    db_session.add(completed_old)
    await db_session.flush()
    completed_old.created_at = datetime.now(UTC) - timedelta(days=60)
    await db_session.flush()

    rows = await dao.find_dead_letter_orphans(db_session)
    assert completed_old.id not in {r.id for r in rows}


# ─────────────── DAO-T5 update（tenant filter） ───────────────


async def test_dao_update_with_correct_project_id(db_session, dao, make_project):
    user, proj = await make_project()
    task = ImportTask(**_task_kwargs(project_id=proj.id, user_id=user.id))
    db_session.add(task)
    await db_session.flush()

    n = await dao.update(
        db_session, task.id, proj.id, fields={"status": "ai_step1", "progress": 25}
    )
    assert n == 1
    await db_session.refresh(task)
    assert task.status == "ai_step1"
    assert task.progress == 25


async def test_dao_update_cross_project_no_op(db_session, dao, make_project):
    """跨 project 越权写不应生效（rowcount=0）。"""
    user, p1 = await make_project()
    _u, p2 = await make_project(owner=user)
    task = ImportTask(**_task_kwargs(project_id=p1.id, user_id=user.id))
    db_session.add(task)
    await db_session.flush()

    n = await dao.update(db_session, task.id, p2.id, fields={"status": "failed"})
    assert n == 0


async def test_dao_update_empty_fields_raises(db_session, dao, make_project):
    user, proj = await make_project()
    with pytest.raises(ValueError):
        await dao.update(db_session, uuid4(), proj.id, fields={})


# ─────────────── DAO-T6 delete（tenant filter） ───────────────


async def test_dao_delete_returns_rowcount(db_session, dao, make_project):
    user, proj = await make_project()
    task = ImportTask(**_task_kwargs(project_id=proj.id, user_id=user.id))
    db_session.add(task)
    await db_session.flush()

    n = await dao.delete(db_session, task.id, proj.id)
    assert n == 1


async def test_dao_delete_cross_project_no_op(db_session, dao, make_project):
    user, p1 = await make_project()
    _u, p2 = await make_project(owner=user)
    task = ImportTask(**_task_kwargs(project_id=p1.id, user_id=user.id))
    db_session.add(task)
    await db_session.flush()

    n = await dao.delete(db_session, task.id, p2.id)
    assert n == 0


# ─────────────── ITEM-DAO-T1 list_by_task / status filter ───────────────


async def test_item_dao_list_by_task_returns_items_sorted(db_session, item_dao, dao, make_project):
    user, proj = await make_project()
    task = ImportTask(**_task_kwargs(project_id=proj.id, user_id=user.id))
    db_session.add(task)
    await db_session.flush()
    items = [
        ImportTaskItem(task_id=task.id, file_path="b/x.py", file_size=1),
        ImportTaskItem(task_id=task.id, file_path="a/y.py", file_size=1),
    ]
    db_session.add_all(items)
    await db_session.flush()

    rows = await item_dao.list_by_task(db_session, task.id)
    assert [r.file_path for r in rows] == ["a/y.py", "b/x.py"]


async def test_item_dao_list_by_task_status_filter(db_session, item_dao, make_project):
    user, proj = await make_project()
    task = ImportTask(**_task_kwargs(project_id=proj.id, user_id=user.id))
    db_session.add(task)
    await db_session.flush()
    db_session.add_all(
        [
            ImportTaskItem(task_id=task.id, file_path="a", file_size=1, status="failed"),
            ImportTaskItem(task_id=task.id, file_path="b", file_size=1, status="completed"),
        ]
    )
    await db_session.flush()

    rows = await item_dao.list_by_task(db_session, task.id, status="failed")
    assert len(rows) == 1
    assert rows[0].status == "failed"


# ─────────────── ITEM-DAO-T2 get_by_id（task scope） ───────────────


async def test_item_dao_get_by_id_cross_task_returns_none(db_session, item_dao, make_project):
    user, proj = await make_project()
    t1 = ImportTask(**_task_kwargs(project_id=proj.id, user_id=user.id, source_hash="A"))
    t2 = ImportTask(**_task_kwargs(project_id=proj.id, user_id=user.id, source_hash="B"))
    db_session.add_all([t1, t2])
    await db_session.flush()
    item = ImportTaskItem(task_id=t1.id, file_path="x", file_size=1)
    db_session.add(item)
    await db_session.flush()

    got = await item_dao.get_by_id(db_session, item.id, t2.id)
    assert got is None


# ─────────────── ITEM-DAO-T3 bulk_create + update ───────────────


async def test_item_dao_bulk_create_and_update(db_session, item_dao, make_project):
    user, proj = await make_project()
    task = ImportTask(**_task_kwargs(project_id=proj.id, user_id=user.id))
    db_session.add(task)
    await db_session.flush()

    items = [
        ImportTaskItem(task_id=task.id, file_path=f"f{i}.py", file_size=i + 1) for i in range(3)
    ]
    created = await item_dao.bulk_create(db_session, items)
    assert len(created) == 3

    n = await item_dao.update(
        db_session,
        items[0].id,
        task.id,
        fields={"status": "completed", "ai_output": {"x": 1}},
    )
    assert n == 1
    await db_session.refresh(items[0])
    assert items[0].status == "completed"
    assert items[0].ai_output == {"x": 1}


async def test_item_dao_update_cross_task_no_op(db_session, item_dao, make_project):
    user, proj = await make_project()
    t1 = ImportTask(**_task_kwargs(project_id=proj.id, user_id=user.id, source_hash="A"))
    t2 = ImportTask(**_task_kwargs(project_id=proj.id, user_id=user.id, source_hash="B"))
    db_session.add_all([t1, t2])
    await db_session.flush()
    item = ImportTaskItem(task_id=t1.id, file_path="x", file_size=1)
    db_session.add(item)
    await db_session.flush()

    n = await item_dao.update(db_session, item.id, t2.id, fields={"status": "failed"})
    assert n == 0
