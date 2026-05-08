"""M18 子片 2 — EmbeddingDAO / EmbeddingFailureDAO / EmbeddingTaskDAO /
SearchEvaluationLogDAO / EmbeddingBackfillDAO 测试。

覆盖 design §9 主查询模式 + tenant 过滤 + CAS 状态机 + backfill LEFT JOIN +
failure 计数 + zombie 超时识别 + vector_search 占位验证。

conftest fixture 复用：make_project / make_user / make_node / make_competitor / make_issue /
make_dim_type / make_dim_record（M04→M07 已有）。
新增 conftest fixture：make_embedding / make_embedding_task（已加入 tests/conftest.py）。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from api.dao.embedding_backfill_dao import EmbeddingBackfillDAO
from api.dao.embedding_dao import EmbeddingDAO
from api.dao.embedding_failure_dao import EmbeddingFailureDAO
from api.dao.embedding_task_dao import EmbeddingTaskDAO
from api.dao.search_evaluation_log_dao import SearchEvaluationLogDAO
from api.models.embedding import (
    Embedding,
    EmbeddingTaskStatus,
)

# ─────────────── fixtures ───────────────

_PROVIDER = "mock"
_MODEL_NAME = "mock-default"
_MODEL_VERSION = "v1"
_DIM = 512
_VEC = [0.1] * 512
_MODALITY = "text"


@pytest.fixture
def embedding_dao():
    return EmbeddingDAO()


@pytest.fixture
def failure_dao():
    return EmbeddingFailureDAO()


@pytest.fixture
def task_dao():
    return EmbeddingTaskDAO()


@pytest.fixture
def eval_log_dao():
    return SearchEvaluationLogDAO()


@pytest.fixture
def backfill_dao():
    return EmbeddingBackfillDAO()


def _emb_kwargs(*, project_id, target_type="node", target_id=None, **overrides):
    """最小 Embedding 构造参数（dim=512 / mock provider）。"""
    return {
        "project_id": project_id,
        "modality": _MODALITY,
        "target_type": target_type,
        "target_id": target_id or uuid4(),
        "provider": _PROVIDER,
        "model_name": _MODEL_NAME,
        "model_version": _MODEL_VERSION,
        "dim": _DIM,
        "embedding_512": _VEC,
        "embedding_1536": None,
        "embedding_3072": None,
        "content_hash": uuid4().hex,
        **overrides,
    }


def _task_kwargs(*, project_id, target_type="node", target_id=None, **overrides):
    return {
        "project_id": project_id,
        "target_type": target_type,
        "target_id": target_id or uuid4(),
        "provider": _PROVIDER,
        "model_name": _MODEL_NAME,
        "model_version": _MODEL_VERSION,
        "enqueued_by": "incremental",
        **overrides,
    }


# ═══════════════════════════════════════════════════════════════════
# EmbeddingDAO
# ═══════════════════════════════════════════════════════════════════


# ─────────── E-T1 find_by_target（7 字段 PK / tenant 过滤）───────────


async def test_embedding_find_by_target_hit(db_session, embedding_dao, make_project):
    """7 字段 PK 精确查找命中。"""
    _u, proj = await make_project()
    target_id = uuid4()
    e = Embedding(**_emb_kwargs(project_id=proj.id, target_id=target_id))
    db_session.add(e)
    await db_session.flush()

    got = await embedding_dao.find_by_target(
        db_session, proj.id, "node", target_id, _PROVIDER, _MODEL_NAME, _MODEL_VERSION
    )
    assert got is not None
    assert got.target_id == target_id


async def test_embedding_find_by_target_miss_wrong_target(db_session, embedding_dao, make_project):
    """target_id 不匹配返 None。"""
    _u, proj = await make_project()
    e = Embedding(**_emb_kwargs(project_id=proj.id))
    db_session.add(e)
    await db_session.flush()

    got = await embedding_dao.find_by_target(
        db_session, proj.id, "node", uuid4(), _PROVIDER, _MODEL_NAME, _MODEL_VERSION
    )
    assert got is None


async def test_embedding_find_by_target_cross_project_returns_none(
    db_session, embedding_dao, make_project
):
    """跨 project 强 tenant 过滤：返 None（service 层转 404）。"""
    _u, p1 = await make_project()
    _u2, p2 = await make_project()
    target_id = uuid4()
    e = Embedding(**_emb_kwargs(project_id=p1.id, target_id=target_id))
    db_session.add(e)
    await db_session.flush()

    got = await embedding_dao.find_by_target(
        db_session, p2.id, "node", target_id, _PROVIDER, _MODEL_NAME, _MODEL_VERSION
    )
    assert got is None


# ─────────── E-T2 find_by_project_and_provider ───────────────────


async def test_embedding_find_by_project_and_provider_returns_list(
    db_session, embedding_dao, make_project
):
    _u, proj = await make_project()
    db_session.add_all(
        [
            Embedding(**_emb_kwargs(project_id=proj.id, target_id=uuid4())),
            Embedding(**_emb_kwargs(project_id=proj.id, target_id=uuid4())),
        ]
    )
    await db_session.flush()

    rows = await embedding_dao.find_by_project_and_provider(
        db_session, proj.id, _PROVIDER, _MODEL_NAME, _MODEL_VERSION
    )
    assert len(rows) >= 2


async def test_embedding_find_by_project_and_provider_excludes_other_project(
    db_session, embedding_dao, make_project
):
    """强 tenant 过滤：不同 project 的 embedding 不回来。"""
    _u, p1 = await make_project()
    _u2, p2 = await make_project()
    db_session.add(Embedding(**_emb_kwargs(project_id=p1.id)))
    db_session.add(Embedding(**_emb_kwargs(project_id=p2.id)))
    await db_session.flush()

    rows = await embedding_dao.find_by_project_and_provider(
        db_session, p1.id, _PROVIDER, _MODEL_NAME, _MODEL_VERSION
    )
    assert all(r.project_id == p1.id for r in rows)


# ─────────── E-T3 vector_search 占位 ─────────────────────────────


async def test_embedding_vector_search_raises_not_implemented(
    db_session, embedding_dao, make_project
):
    """vector_search 占位：pgvector 未装，子片 3 回写（抛 NotImplementedError）。"""
    _u, proj = await make_project()
    with pytest.raises(NotImplementedError, match="pgvector"):
        await embedding_dao.vector_search(
            db_session,
            proj.id,
            query_vec=_VEC,
            dim=_DIM,
            provider=_PROVIDER,
            model_name=_MODEL_NAME,
            model_version=_MODEL_VERSION,
        )


# ─────────── E-T4 delete_by_target ───────────────────────────────


async def test_embedding_delete_by_target_returns_rowcount(db_session, embedding_dao, make_project):
    _u, proj = await make_project()
    target_id = uuid4()
    e = Embedding(**_emb_kwargs(project_id=proj.id, target_id=target_id))
    db_session.add(e)
    await db_session.flush()

    n = await embedding_dao.delete_by_target(db_session, proj.id, "node", target_id)
    assert n == 1


async def test_embedding_delete_by_target_cross_project_noop(
    db_session, embedding_dao, make_project
):
    """跨 project 强 tenant 过滤：不删对方 project 的行。"""
    _u, p1 = await make_project()
    _u2, p2 = await make_project()
    target_id = uuid4()
    e = Embedding(**_emb_kwargs(project_id=p1.id, target_id=target_id))
    db_session.add(e)
    await db_session.flush()

    n = await embedding_dao.delete_by_target(db_session, p2.id, "node", target_id)
    assert n == 0


# ─────────── E-T5 count_by_project_and_provider ──────────────────


async def test_embedding_count_by_project_and_provider(db_session, embedding_dao, make_project):
    _u, proj = await make_project()
    db_session.add_all(
        [
            Embedding(**_emb_kwargs(project_id=proj.id, target_id=uuid4())),
            Embedding(**_emb_kwargs(project_id=proj.id, target_id=uuid4())),
        ]
    )
    await db_session.flush()

    n = await embedding_dao.count_by_project_and_provider(
        db_session, proj.id, _PROVIDER, _MODEL_NAME, _MODEL_VERSION
    )
    assert n >= 2


# ─────────── E-T6 upsert_embedding ──────────────────────────────


async def test_embedding_upsert_inserts_new_row(db_session, embedding_dao, make_project):
    _u, proj = await make_project()
    target_id = uuid4()

    row = await embedding_dao.upsert_embedding(
        db_session,
        project_id=proj.id,
        modality=_MODALITY,
        target_type="node",
        target_id=target_id,
        provider=_PROVIDER,
        model_name=_MODEL_NAME,
        model_version=_MODEL_VERSION,
        dim=_DIM,
        vector=_VEC,
        content_hash="hash-v1",
    )
    assert row is not None
    assert row.target_id == target_id
    assert row.content_hash == "hash-v1"


async def test_embedding_upsert_updates_existing_row(db_session, embedding_dao, make_project):
    """ON CONFLICT DO UPDATE：同 7 字段 PK 更新 content_hash。"""
    _u, proj = await make_project()
    target_id = uuid4()

    await embedding_dao.upsert_embedding(
        db_session,
        project_id=proj.id,
        modality=_MODALITY,
        target_type="node",
        target_id=target_id,
        provider=_PROVIDER,
        model_name=_MODEL_NAME,
        model_version=_MODEL_VERSION,
        dim=_DIM,
        vector=_VEC,
        content_hash="hash-v1",
    )

    updated = await embedding_dao.upsert_embedding(
        db_session,
        project_id=proj.id,
        modality=_MODALITY,
        target_type="node",
        target_id=target_id,
        provider=_PROVIDER,
        model_name=_MODEL_NAME,
        model_version=_MODEL_VERSION,
        dim=_DIM,
        vector=[0.2] * 512,
        content_hash="hash-v2",
    )
    assert updated.content_hash == "hash-v2"


async def test_embedding_upsert_invalid_dim_raises(db_session, embedding_dao, make_project):
    _u, proj = await make_project()
    with pytest.raises(ValueError, match="unsupported dim"):
        await embedding_dao.upsert_embedding(
            db_session,
            project_id=proj.id,
            modality=_MODALITY,
            target_type="node",
            target_id=uuid4(),
            provider=_PROVIDER,
            model_name=_MODEL_NAME,
            model_version=_MODEL_VERSION,
            dim=768,
            vector=[0.1] * 768,
            content_hash="h",
        )


# ═══════════════════════════════════════════════════════════════════
# EmbeddingFailureDAO
# ═══════════════════════════════════════════════════════════════════


# ─────────── F-T1 record_failure ─────────────────────────────────


async def test_failure_record_creates_row(db_session, failure_dao, make_project):
    _u, proj = await make_project()
    f = await failure_dao.record_failure(
        db_session,
        project_id=proj.id,
        target_type="node",
        target_id=uuid4(),
        provider=_PROVIDER,
        model_name=_MODEL_NAME,
        model_version=_MODEL_VERSION,
        error_code="EMBEDDING_TIMEOUT",
        error_message="timed out",
    )
    assert f.id is not None
    assert f.project_id == proj.id
    assert f.error_code == "EMBEDDING_TIMEOUT"


async def test_failure_record_multiple_creates_multiple_rows(db_session, failure_dao, make_project):
    """每次失败插独立行（无 failure_count 字段；计数在 count_failures_* 查询层聚合）。"""
    _u, proj = await make_project()
    target_id = uuid4()
    for i in range(3):
        await failure_dao.record_failure(
            db_session,
            project_id=proj.id,
            target_type="node",
            target_id=target_id,
            provider=_PROVIDER,
            model_name=_MODEL_NAME,
            model_version=_MODEL_VERSION,
            error_code="ERR",
            error_message=f"fail-{i}",
        )

    rows = await failure_dao.find_by_target(db_session, proj.id, "node", target_id)
    assert len(rows) == 3


# ─────────── F-T2 find_by_target ─────────────────────────────────


async def test_failure_find_by_target_cross_project_returns_empty(
    db_session, failure_dao, make_project
):
    """强 tenant 过滤：跨 project 查返空列表。"""
    _u, p1 = await make_project()
    _u2, p2 = await make_project()
    target_id = uuid4()
    await failure_dao.record_failure(
        db_session,
        project_id=p1.id,
        target_type="node",
        target_id=target_id,
        provider=_PROVIDER,
        model_name=_MODEL_NAME,
        model_version=_MODEL_VERSION,
        error_code="ERR",
        error_message="fail",
    )

    rows = await failure_dao.find_by_target(db_session, p2.id, "node", target_id)
    assert rows == []


# ─────────── F-T3 count_failures_in_window（全局）────────────────


async def test_failure_count_in_window_global(db_session, failure_dao, make_project):
    """全局统计：hours=1 内的失败数包含多 project。"""
    _u, p1 = await make_project()
    _u2, p2 = await make_project()
    for proj in [p1, p2]:
        await failure_dao.record_failure(
            db_session,
            project_id=proj.id,
            target_type="node",
            target_id=uuid4(),
            provider=_PROVIDER,
            model_name=_MODEL_NAME,
            model_version=_MODEL_VERSION,
            error_code="ERR",
            error_message="x",
        )

    n = await failure_dao.count_failures_in_window(db_session, hours=1)
    assert n >= 2


# ─────────── F-T4 count_failures_by_project_in_window（PER_PROJECT）────────


async def test_failure_count_by_project_in_window_isolates(db_session, failure_dao, make_project):
    """PER_PROJECT 维度：project_id 过滤不计入其他 project 的失败。"""
    _u, p1 = await make_project()
    _u2, p2 = await make_project()
    await failure_dao.record_failure(
        db_session,
        project_id=p1.id,
        target_type="node",
        target_id=uuid4(),
        provider=_PROVIDER,
        model_name=_MODEL_NAME,
        model_version=_MODEL_VERSION,
        error_code="ERR",
        error_message="x",
    )
    # p2 无失败
    n = await failure_dao.count_failures_by_project_in_window(db_session, p2.id, hours=1)
    assert n == 0


async def test_failure_count_by_project_excludes_old(db_session, failure_dao, make_project):
    """时间窗口过滤：failed_at < threshold 的行不计入。"""
    _u, proj = await make_project()
    f = await failure_dao.record_failure(
        db_session,
        project_id=proj.id,
        target_type="node",
        target_id=uuid4(),
        provider=_PROVIDER,
        model_name=_MODEL_NAME,
        model_version=_MODEL_VERSION,
        error_code="ERR",
        error_message="old",
    )
    # 把 failed_at 设成 3 小时前
    f.failed_at = datetime.now(UTC) - timedelta(hours=3)
    await db_session.flush()

    n = await failure_dao.count_failures_by_project_in_window(db_session, proj.id, hours=1)
    assert n == 0


# ─────────── F-T5 delete_old ─────────────────────────────────────


async def test_failure_delete_old_removes_expired(db_session, failure_dao, make_project):
    _u, proj = await make_project()
    f = await failure_dao.record_failure(
        db_session,
        project_id=proj.id,
        target_type="node",
        target_id=uuid4(),
        provider=_PROVIDER,
        model_name=_MODEL_NAME,
        model_version=_MODEL_VERSION,
        error_code="ERR",
        error_message="old",
    )
    f.failed_at = datetime.now(UTC) - timedelta(days=91)
    await db_session.flush()

    n = await failure_dao.delete_old(db_session, days=90)
    assert n >= 1


async def test_failure_delete_old_keeps_recent(db_session, failure_dao, make_project):
    _u, proj = await make_project()
    await failure_dao.record_failure(
        db_session,
        project_id=proj.id,
        target_type="node",
        target_id=uuid4(),
        provider=_PROVIDER,
        model_name=_MODEL_NAME,
        model_version=_MODEL_VERSION,
        error_code="ERR",
        error_message="recent",
    )

    n = await failure_dao.delete_old(db_session, days=90)
    assert n == 0  # 刚插入的不应被删


# ═══════════════════════════════════════════════════════════════════
# EmbeddingTaskDAO
# ═══════════════════════════════════════════════════════════════════


# ─────────── T-T1 create ──────────────────────────────────────────


async def test_task_create_returns_pending(db_session, task_dao, make_project):
    _u, proj = await make_project()
    task = await task_dao.create(
        db_session,
        project_id=proj.id,
        target_type="node",
        target_id=uuid4(),
        provider=_PROVIDER,
        model_name=_MODEL_NAME,
        model_version=_MODEL_VERSION,
    )
    assert task.id is not None
    assert task.status == EmbeddingTaskStatus.pending.value
    assert task.project_id == proj.id


# ─────────── T-T2 cas_start_running（pending → running）──────────────


async def test_task_cas_start_running_pending_to_running(db_session, task_dao, make_project):
    """pending → running CAS 命中。"""
    _u, proj = await make_project()
    task = await task_dao.create(db_session, **_task_kwargs(project_id=proj.id))
    await db_session.commit()

    updated = await task_dao.cas_start_running(db_session, task.id)
    assert updated is not None
    assert updated.status == EmbeddingTaskStatus.running.value


async def test_task_cas_start_running_already_running_returns_none(
    db_session, task_dao, make_project
):
    """已经 running 的 task，再次 cas_start_running 返 None（CAS miss）。"""
    _u, proj = await make_project()
    task = await task_dao.create(db_session, **_task_kwargs(project_id=proj.id))
    await db_session.commit()

    await task_dao.cas_start_running(db_session, task.id)
    # 再来一次 → CAS miss
    result = await task_dao.cas_start_running(db_session, task.id)
    assert result is None


# ─────────── T-T3 cas_complete（running → succeeded/failed/dead_letter）────────


async def test_task_cas_complete_running_to_succeeded(db_session, task_dao, make_project):
    _u, proj = await make_project()
    task = await task_dao.create(db_session, **_task_kwargs(project_id=proj.id))
    await db_session.commit()

    await task_dao.cas_start_running(db_session, task.id)
    done = await task_dao.cas_complete(db_session, task.id, EmbeddingTaskStatus.succeeded)
    assert done is not None
    assert done.status == EmbeddingTaskStatus.succeeded.value
    assert done.completed_at is not None


async def test_task_cas_complete_succeeded_cannot_run_again(db_session, task_dao, make_project):
    """succeeded → running 反向不允许（CAS WHERE status='pending'）。"""
    _u, proj = await make_project()
    task = await task_dao.create(db_session, **_task_kwargs(project_id=proj.id))
    await db_session.commit()

    await task_dao.cas_start_running(db_session, task.id)
    await task_dao.cas_complete(db_session, task.id, EmbeddingTaskStatus.succeeded)
    # 已 succeeded → cas_start_running 应返 None
    result = await task_dao.cas_start_running(db_session, task.id)
    assert result is None


async def test_task_cas_complete_invalid_status_raises(db_session, task_dao, make_project):
    """pending 目标不允许（只允许终态 succeeded/failed/dead_letter）。"""
    _u, proj = await make_project()
    task = await task_dao.create(db_session, **_task_kwargs(project_id=proj.id))
    await db_session.commit()

    await task_dao.cas_start_running(db_session, task.id)
    with pytest.raises(ValueError, match="终态"):
        await task_dao.cas_complete(db_session, task.id, EmbeddingTaskStatus.pending)


async def test_task_cas_complete_with_error_fields(db_session, task_dao, make_project):
    """failed 终态带 error_code + error_message。"""
    _u, proj = await make_project()
    task = await task_dao.create(db_session, **_task_kwargs(project_id=proj.id))
    await db_session.commit()

    await task_dao.cas_start_running(db_session, task.id)
    done = await task_dao.cas_complete(
        db_session,
        task.id,
        EmbeddingTaskStatus.failed,
        error_code="PROVIDER_ERROR",
        error_message="network timeout",
    )
    assert done is not None
    assert done.error_code == "PROVIDER_ERROR"
    assert done.error_message == "network timeout"


# ─────────── T-T4 cas_zombie_transition ──────────────────────────────────────


async def test_task_cas_zombie_transition_running_timeout_to_dead_letter(
    db_session, task_dao, make_project
):
    """running 超时 → dead_letter（模拟 updated_at 超 timeout）。"""
    _u, proj = await make_project()
    task = await task_dao.create(db_session, **_task_kwargs(project_id=proj.id))
    await db_session.commit()

    await task_dao.cas_start_running(db_session, task.id)
    # 把 updated_at 设成很早（模拟超时）
    await db_session.execute(
        __import__("sqlalchemy").text(
            "UPDATE embedding_tasks SET updated_at = NOW() - INTERVAL '10 minutes' WHERE id = :id"
        ),
        {"id": task.id},
    )
    await db_session.commit()

    result = await task_dao.cas_zombie_transition(db_session, task.id, timeout_seconds=60)
    assert result is not None
    assert result.status == EmbeddingTaskStatus.dead_letter.value


async def test_task_cas_zombie_not_timeout_returns_none(db_session, task_dao, make_project):
    """running 但未超时 → cas_zombie_transition 返 None。"""
    _u, proj = await make_project()
    task = await task_dao.create(db_session, **_task_kwargs(project_id=proj.id))
    await db_session.commit()

    await task_dao.cas_start_running(db_session, task.id)
    # updated_at 是刚才，timeout=3600s → 未超时
    result = await task_dao.cas_zombie_transition(db_session, task.id, timeout_seconds=3600)
    assert result is None


# ─────────── T-T5 find_zombie_tasks ──────────────────────────────────────────


async def test_task_find_zombie_tasks_returns_timed_out_running(db_session, task_dao, make_project):
    """find_zombie_tasks 列出 running 且 updated_at < threshold 的任务。"""
    _u, proj = await make_project()
    task = await task_dao.create(db_session, **_task_kwargs(project_id=proj.id))
    await db_session.commit()

    await task_dao.cas_start_running(db_session, task.id)
    # 把 updated_at 设成超时前
    await db_session.execute(
        __import__("sqlalchemy").text(
            "UPDATE embedding_tasks SET updated_at = NOW() - INTERVAL '10 minutes' WHERE id = :id"
        ),
        {"id": task.id},
    )
    await db_session.commit()

    zombies = await task_dao.find_zombie_tasks(db_session, timeout_seconds=60)
    ids = {z.id for z in zombies}
    assert task.id in ids


async def test_task_find_zombie_tasks_excludes_fresh_running(db_session, task_dao, make_project):
    """updated_at 刚更新的 running task 不列为 zombie。"""
    _u, proj = await make_project()
    task = await task_dao.create(db_session, **_task_kwargs(project_id=proj.id))
    await db_session.commit()

    await task_dao.cas_start_running(db_session, task.id)
    # timeout=3600s → 刚更新的不超时
    zombies = await task_dao.find_zombie_tasks(db_session, timeout_seconds=3600)
    ids = {z.id for z in zombies}
    assert task.id not in ids


# ─────────── T-T6 find_pending_for_recovery ─────────────────────────────────


async def test_task_find_pending_for_recovery(db_session, task_dao, make_project):
    """startup recovery：列出 status=pending 的残留任务。"""
    _u, proj = await make_project()
    task = await task_dao.create(db_session, **_task_kwargs(project_id=proj.id))
    await db_session.flush()

    rows = await task_dao.find_pending_for_recovery(db_session)
    ids = {r.id for r in rows}
    assert task.id in ids


# ─────────── T-T7 delete_old_terminal ────────────────────────────────────────


async def test_task_delete_old_terminal_removes_expired(db_session, task_dao, make_project):
    _u, proj = await make_project()
    task = await task_dao.create(db_session, **_task_kwargs(project_id=proj.id))
    await db_session.commit()

    await task_dao.cas_start_running(db_session, task.id)
    await task_dao.cas_complete(db_session, task.id, EmbeddingTaskStatus.succeeded)

    # 把 expires_at 设成过去
    await db_session.execute(
        __import__("sqlalchemy").text(
            "UPDATE embedding_tasks SET expires_at = NOW() - INTERVAL '1 day' WHERE id = :id"
        ),
        {"id": task.id},
    )
    await db_session.commit()

    n = await task_dao.delete_old_terminal(db_session, days=30)
    assert n >= 1


# ═══════════════════════════════════════════════════════════════════
# SearchEvaluationLogDAO
# ═══════════════════════════════════════════════════════════════════


# ─────────── EL-T1 record + find_by_project ──────────────────────


async def test_eval_log_record_and_find_by_project(
    db_session, eval_log_dao, make_project, make_user
):
    _u, proj = await make_project()
    user = await make_user()

    log = await eval_log_dao.record(
        db_session,
        project_id=proj.id,
        user_id=user.id,
        query="test search",
        keyword_top5=[{"target_type": "node", "target_id": str(uuid4()), "score": 0.9}],
        semantic_top5=[],
        hybrid_top5=[],
        rrf_k=60,
        similarity_threshold=0.7,
    )
    assert log.id is not None
    assert log.query == "test search"
    assert log.rrf_k == 60

    rows = await eval_log_dao.find_by_project(db_session, proj.id)
    ids = {r.id for r in rows}
    assert log.id in ids


async def test_eval_log_find_by_project_limit(db_session, eval_log_dao, make_project, make_user):
    _u, proj = await make_project()
    user = await make_user()
    for _ in range(5):
        await eval_log_dao.record(
            db_session,
            project_id=proj.id,
            user_id=user.id,
            query="q",
            keyword_top5=[],
            semantic_top5=[],
            hybrid_top5=[],
            rrf_k=60,
            similarity_threshold=0.7,
        )

    rows = await eval_log_dao.find_by_project(db_session, proj.id, limit=3)
    assert len(rows) <= 3


async def test_eval_log_find_by_project_filters_by_project(
    db_session, eval_log_dao, make_project, make_user
):
    """find_by_project 只返回指定 project 的日志（按 project_id 过滤）。"""
    _u, p1 = await make_project()
    _u2, p2 = await make_project()
    user = await make_user()

    await eval_log_dao.record(
        db_session,
        project_id=p1.id,
        user_id=user.id,
        query="q1",
        keyword_top5=[],
        semantic_top5=[],
        hybrid_top5=[],
        rrf_k=60,
        similarity_threshold=0.7,
    )

    rows = await eval_log_dao.find_by_project(db_session, p2.id)
    # p2 无日志 → 空列表
    assert len(rows) == 0


# ─────────── EL-T2 delete_old ────────────────────────────────────


async def test_eval_log_delete_old_removes_old_records(
    db_session, eval_log_dao, make_project, make_user
):
    _u, proj = await make_project()
    user = await make_user()
    log = await eval_log_dao.record(
        db_session,
        project_id=proj.id,
        user_id=user.id,
        query="old",
        keyword_top5=[],
        semantic_top5=[],
        hybrid_top5=[],
        rrf_k=60,
        similarity_threshold=0.7,
    )
    # 把 sampled_at 设成 2 年前
    log.sampled_at = datetime.now(UTC) - timedelta(days=730)
    await db_session.flush()

    n = await eval_log_dao.delete_old(db_session, days=365)
    assert n >= 1


# ═══════════════════════════════════════════════════════════════════
# EmbeddingBackfillDAO（规则 4 豁免 / LEFT JOIN）
# ═══════════════════════════════════════════════════════════════════


# ─────────── B-T1 list_pending_node_ids ──────────────────────────


async def test_backfill_list_pending_node_ids_returns_missing(
    db_session, backfill_dao, make_project, make_node
):
    """nodes 表有行但 embeddings 无对应行 → 应列出（ADR-003 规则 4 LEFT JOIN）。"""
    _u, proj = await make_project()
    node = await make_node(proj.id, name="n1")

    ids = await backfill_dao.list_pending_node_ids(
        db_session, proj.id, _PROVIDER, _MODEL_NAME, _MODEL_VERSION
    )
    assert node.id in ids


async def test_backfill_list_pending_node_ids_excludes_existing(
    db_session, backfill_dao, make_project, make_node
):
    """embeddings 表已有对应行 → 不再列出（LEFT JOIN IS NULL 过滤）。"""
    _u, proj = await make_project()
    node = await make_node(proj.id, name="n2")
    # 插入 embedding（node 已有 embedding）
    e = Embedding(**_emb_kwargs(project_id=proj.id, target_type="node", target_id=node.id))
    db_session.add(e)
    await db_session.flush()

    ids = await backfill_dao.list_pending_node_ids(
        db_session, proj.id, _PROVIDER, _MODEL_NAME, _MODEL_VERSION
    )
    assert node.id not in ids


async def test_backfill_list_pending_node_ids_cross_project_isolation(
    db_session, backfill_dao, make_project, make_node
):
    """强 tenant 过滤：project_id 不同的 node 不列出。"""
    _u, p1 = await make_project()
    _u2, p2 = await make_project()
    node_p1 = await make_node(p1.id, name="n-p1")

    ids = await backfill_dao.list_pending_node_ids(
        db_session, p2.id, _PROVIDER, _MODEL_NAME, _MODEL_VERSION
    )
    assert node_p1.id not in ids


# ─────────── B-T2 list_pending_competitor_ids ────────────────────


async def test_backfill_list_pending_competitor_ids_returns_missing(
    db_session, backfill_dao, make_project, make_competitor
):
    _u, proj = await make_project()
    c = await make_competitor(project=proj, user=_u)

    ids = await backfill_dao.list_pending_competitor_ids(
        db_session, proj.id, _PROVIDER, _MODEL_NAME, _MODEL_VERSION
    )
    assert c.id in ids


async def test_backfill_list_pending_competitor_ids_excludes_existing(
    db_session, backfill_dao, make_project, make_competitor
):
    _u, proj = await make_project()
    c = await make_competitor(project=proj, user=_u)
    e = Embedding(**_emb_kwargs(project_id=proj.id, target_type="competitor", target_id=c.id))
    db_session.add(e)
    await db_session.flush()

    ids = await backfill_dao.list_pending_competitor_ids(
        db_session, proj.id, _PROVIDER, _MODEL_NAME, _MODEL_VERSION
    )
    assert c.id not in ids


# ─────────── B-T3 list_pending_issue_ids ─────────────────────────


async def test_backfill_list_pending_issue_ids_returns_missing(
    db_session, backfill_dao, make_project, make_issue
):
    user, proj = await make_project()
    issue = await make_issue(user=user, project=proj)

    ids = await backfill_dao.list_pending_issue_ids(
        db_session, proj.id, _PROVIDER, _MODEL_NAME, _MODEL_VERSION
    )
    assert issue.id in ids


# ─────────── B-T4 list_pending_dimension_record_ids ──────────────


async def test_backfill_list_pending_dimension_record_ids_returns_missing(
    db_session, backfill_dao, make_project, make_node, make_dim_type, make_dim_record
):
    user, proj = await make_project()
    node = await make_node(proj.id)
    dt_id = await make_dim_type(key="t-backfill", project_id=proj.id)
    dr = await make_dim_record(user=user, project=proj, node=node, dim_type_id=dt_id)

    ids = await backfill_dao.list_pending_dimension_record_ids(
        db_session, proj.id, _PROVIDER, _MODEL_NAME, _MODEL_VERSION
    )
    assert dr.id in ids


async def test_backfill_list_pending_dimension_record_ids_excludes_existing(
    db_session, backfill_dao, make_project, make_node, make_dim_type, make_dim_record
):
    user, proj = await make_project()
    node = await make_node(proj.id)
    dt_id = await make_dim_type(key="t-backfill-e", project_id=proj.id)
    dr = await make_dim_record(user=user, project=proj, node=node, dim_type_id=dt_id)
    e = Embedding(
        **_emb_kwargs(project_id=proj.id, target_type="dimension_record", target_id=dr.id)
    )
    db_session.add(e)
    await db_session.flush()

    ids = await backfill_dao.list_pending_dimension_record_ids(
        db_session, proj.id, _PROVIDER, _MODEL_NAME, _MODEL_VERSION
    )
    assert dr.id not in ids
