"""M11 子片 2 — ColdStartDAO 测试。

覆盖 design §9 主查询模式 + tenant 过滤 + user 过滤 + create/update CRUD。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from api.dao.cold_start_dao import ColdStartDAO
from api.models.cold_start_task import ColdStartStatus, ColdStartTask


@pytest.fixture
def dao():
    return ColdStartDAO()


async def _make_task(
    db_session,
    *,
    project_id,
    user_id,
    status: str = ColdStartStatus.PENDING.value,
    source_filename: str = "x.csv",
    source_hash: str | None = None,
) -> ColdStartTask:
    task = ColdStartTask(
        project_id=project_id,
        user_id=user_id,
        source_hash=source_hash or uuid4().hex,
        source_filename=source_filename,
        status=status,
    )
    db_session.add(task)
    await db_session.flush()
    return task


# ─────────────── M11-DAO-T1 list_by_project ───────────────


async def test_dao_list_by_project_returns_user_tasks_desc(db_session, dao, make_project):
    """created_at desc 排序：手动设置不同 created_at（PG `now()` 在同事务内返回相同值）。"""
    from datetime import UTC, datetime, timedelta

    user, proj = await make_project()
    t1 = await _make_task(db_session, project_id=proj.id, user_id=user.id)
    t2 = await _make_task(db_session, project_id=proj.id, user_id=user.id)
    base = datetime.now(UTC)
    t1.created_at = base - timedelta(seconds=10)
    t2.created_at = base
    await db_session.flush()
    rows = await dao.list_by_project(db_session, proj.id, user.id)
    assert len(rows) == 2
    assert rows[0].id == t2.id, "created_at desc：最新在前"
    assert rows[1].id == t1.id


async def test_dao_list_by_project_filters_by_user(db_session, dao, make_project):
    """同项目跨用户：A 用户不应看到 B 用户的导入任务。"""
    userA, proj = await make_project()
    _, _projB = await make_project()  # noise
    # 用 make_user 通过 make_project 间接创建第二个 user
    _, projShared = await make_project(owner=userA)
    # 制造一个不同 owner 的 task：在同一 proj 下挂 userA 的任务 + 另建 userB
    userB_user, _ = await make_project(name_suffix="-B")
    await _make_task(db_session, project_id=projShared.id, user_id=userA.id)
    await _make_task(db_session, project_id=projShared.id, user_id=userB_user.id)

    rowsA = await dao.list_by_project(db_session, projShared.id, userA.id)
    rowsB = await dao.list_by_project(db_session, projShared.id, userB_user.id)
    assert len(rowsA) == 1
    assert len(rowsB) == 1
    assert rowsA[0].user_id == userA.id
    assert rowsB[0].user_id == userB_user.id


async def test_dao_list_by_project_isolates_tenants(db_session, dao, make_project):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(owner=user, name_suffix="-B")
    await _make_task(db_session, project_id=projA.id, user_id=user.id)
    await _make_task(db_session, project_id=projB.id, user_id=user.id)
    rowsA = await dao.list_by_project(db_session, projA.id, user.id)
    assert len(rowsA) == 1
    assert rowsA[0].project_id == projA.id


async def test_dao_list_by_project_respects_limit(db_session, dao, make_project):
    user, proj = await make_project()
    for _ in range(5):
        await _make_task(db_session, project_id=proj.id, user_id=user.id)
    rows = await dao.list_by_project(db_session, proj.id, user.id, limit=3)
    assert len(rows) == 3


# ─────────────── M11-DAO-T2 get_by_id ───────────────


async def test_dao_get_by_id_in_tenant(db_session, dao, make_project):
    user, proj = await make_project()
    t = await _make_task(db_session, project_id=proj.id, user_id=user.id)
    found = await dao.get_by_id(db_session, t.id, proj.id)
    assert found is not None
    assert found.id == t.id


async def test_dao_get_by_id_cross_tenant_returns_none(db_session, dao, make_project):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(owner=user, name_suffix="-B")
    t = await _make_task(db_session, project_id=projA.id, user_id=user.id)
    found = await dao.get_by_id(db_session, t.id, projB.id)
    assert found is None, "跨 project 越权 GET 必须返 None"


async def test_dao_get_by_id_unknown_returns_none(db_session, dao, make_project):
    _, proj = await make_project()
    found = await dao.get_by_id(db_session, uuid4(), proj.id)
    assert found is None


# ─────────────── M11-DAO-T3 create ───────────────


async def test_dao_create_persists(db_session, dao, make_project):
    user, proj = await make_project()
    task = ColdStartTask(
        project_id=proj.id,
        user_id=user.id,
        source_hash="h1",
        source_filename="a.csv",
    )
    out = await dao.create(db_session, task)
    assert out.id is not None
    assert out.status == ColdStartStatus.PENDING.value


# ─────────────── M11-DAO-T4 update ───────────────


async def test_dao_update_status_and_counts(db_session, dao, make_project):
    user, proj = await make_project()
    t = await _make_task(db_session, project_id=proj.id, user_id=user.id)
    rowcount = await dao.update(
        db_session,
        t.id,
        proj.id,
        fields={
            "status": ColdStartStatus.COMPLETED.value,
            "total_rows": 100,
            "success_rows": 100,
        },
    )
    assert rowcount == 1
    await db_session.refresh(t)
    assert t.status == ColdStartStatus.COMPLETED.value
    assert t.total_rows == 100
    assert t.success_rows == 100


async def test_dao_update_cross_tenant_no_effect(db_session, dao, make_project):
    """跨 project 越权 UPDATE 必须 rowcount=0（强制 tenant 过滤）。"""
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(owner=user, name_suffix="-B")
    t = await _make_task(db_session, project_id=projA.id, user_id=user.id)
    rowcount = await dao.update(
        db_session,
        t.id,
        projB.id,  # 错的 project
        fields={"status": ColdStartStatus.FAILED.value},
    )
    assert rowcount == 0
    await db_session.refresh(t)
    assert t.status == ColdStartStatus.PENDING.value, "原状态未变"


async def test_dao_update_unknown_id_returns_zero(db_session, dao, make_project):
    _, proj = await make_project()
    rowcount = await dao.update(
        db_session,
        uuid4(),
        proj.id,
        fields={"status": ColdStartStatus.FAILED.value},
    )
    assert rowcount == 0


async def test_dao_update_empty_fields_raises(db_session, dao, make_project):
    user, proj = await make_project()
    t = await _make_task(db_session, project_id=proj.id, user_id=user.id)
    with pytest.raises(ValueError, match="fields cannot be empty"):
        await dao.update(db_session, t.id, proj.id, fields={})
