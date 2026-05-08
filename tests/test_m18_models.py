"""M18 子片 1 — Embedding / EmbeddingFailure / EmbeddingTask / SearchEvaluationLog model 单元测试。

覆盖 design §3 SQLAlchemy block（line 212-462）：
- embeddings 表：7 字段复合 PK / 3 异维列 nullable / 4+1 CHECK 约束 / project CASCADE
- embedding_failures 表：单 UUID PK / target_type CHECK / 2 索引 / project CASCADE
- embedding_tasks 表：5 状态 StrEnum + tuple / 3 CHECK / 默认 status=pending / project CASCADE
- search_evaluation_log 表：JSONB 3 列 / nullable user_clicked_* / project CASCADE
- Embedding 7 字段 PK 联合唯一性测试
- dim 与 embedding_NNN 列 CHECK 互斥测试（dim=512 时 embedding_1536 必须 NULL）
- EmbeddingTaskStatus 5 值齐
- modality 默认 'text'
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.models.embedding import (
    _EMBEDDING_TASK_STATUSES,
    Embedding,
    EmbeddingFailure,
    EmbeddingTask,
    EmbeddingTaskStatus,
    SearchEvaluationLog,
)

# ─────────────── Helpers ───────────────────────────────────────────────────


def _make_embedding_kwargs(*, project_id, target_id=None, **overrides):
    """Valid Embedding row (dim=1536, embedding_1536 not-null, others null)."""
    base = {
        "project_id": project_id,
        "modality": "text",
        "target_type": "node",
        "target_id": target_id or uuid4(),
        "provider": "openai",
        "model_name": "text-embedding-3-small",
        "model_version": "v1",
        "dim": 1536,
        "embedding_512": None,
        "embedding_1536": [0.1] * 1536,
        "embedding_3072": None,
        "content_hash": "sha256:abc",
    }
    base.update(overrides)
    return base


def _make_failure_kwargs(*, project_id, **overrides):
    base = {
        "project_id": project_id,
        "target_type": "node",
        "target_id": uuid4(),
        "provider": "openai",
        "model_name": "text-embedding-3-small",
        "model_version": "v1",
        "error_code": "PROVIDER_TIMEOUT",
        "error_message": "Connection timed out",
    }
    base.update(overrides)
    return base


def _make_task_kwargs(*, project_id, **overrides):
    base = {
        "project_id": project_id,
        "target_type": "node",
        "target_id": uuid4(),
        "provider": "openai",
        "model_name": "text-embedding-3-small",
        "model_version": "v1",
        "enqueued_by": "incremental",
    }
    base.update(overrides)
    return base


def _make_eval_kwargs(*, project_id, **overrides):
    top5 = [{"target_type": "node", "target_id": str(uuid4()), "score": 0.9}]
    base = {
        "project_id": project_id,
        "user_id": uuid4(),
        "query": "auth service",
        "keyword_top5": top5,
        "semantic_top5": top5,
        "hybrid_top5": top5,
        "rrf_k": 60,
        "similarity_threshold": 0.7,
    }
    base.update(overrides)
    return base


# ─────────────── M18-EMBED-T1 Embedding 持久化 + 默认值 ────────────────────


async def test_embedding_persists_with_defaults(db_session, make_project):
    _user, proj = await make_project()
    emb = Embedding(**_make_embedding_kwargs(project_id=proj.id))
    db_session.add(emb)
    await db_session.flush()
    await db_session.refresh(emb)

    assert emb.project_id == proj.id
    assert emb.modality == "text"
    assert emb.dim == 1536
    assert emb.embedding_512 is None
    assert emb.embedding_3072 is None
    assert len(emb.embedding_1536) == 1536
    assert emb.content_hash == "sha256:abc"
    assert emb.created_at is not None


# ─────────────── M18-EMBED-T2 modality 默认值 'text' ──────────────────────


async def test_embedding_modality_default_is_text(db_session, make_project):
    """modality default='text'（设计 line 236 字面）。"""
    _user, proj = await make_project()
    kwargs = _make_embedding_kwargs(project_id=proj.id)
    # modality 不传，依赖 default
    kwargs.pop("modality")
    emb = Embedding(**kwargs)
    db_session.add(emb)
    await db_session.flush()
    await db_session.refresh(emb)
    assert emb.modality == "text"


# ─────────────── M18-EMBED-T3 7 字段 PK 联合唯一性 ────────────────────────


async def test_embedding_7field_pk_unique_violation(db_session, make_project):
    """同 7 字段 PK 值的两行触发 PK 冲突。"""
    _user, proj = await make_project()
    tid = uuid4()
    kwargs = _make_embedding_kwargs(project_id=proj.id, target_id=tid)
    db_session.add(Embedding(**kwargs))
    await db_session.flush()
    db_session.add(Embedding(**kwargs))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_embedding_7field_pk_different_provider_allowed(db_session, make_project):
    """provider 不同的两行可共存（7 字段 PK 中 provider 不同）。"""
    _user, proj = await make_project()
    tid = uuid4()
    db_session.add(
        Embedding(
            **_make_embedding_kwargs(
                project_id=proj.id,
                target_id=tid,
                provider="openai",
                dim=1536,
                embedding_512=None,
                embedding_1536=[0.1] * 1536,
                embedding_3072=None,
            )
        )
    )
    db_session.add(
        Embedding(
            **_make_embedding_kwargs(
                project_id=proj.id,
                target_id=tid,
                provider="mock",
                dim=512,
                embedding_512=[0.2] * 512,
                embedding_1536=None,
                embedding_3072=None,
            )
        )
    )
    await db_session.flush()  # 不应抛


async def test_embedding_7field_pk_different_model_version_allowed(db_session, make_project):
    """model_version 不同的两行可共存（多版本共存语义 fix v4.1 Q3=A）。"""
    _user, proj = await make_project()
    tid = uuid4()
    db_session.add(
        Embedding(**_make_embedding_kwargs(project_id=proj.id, target_id=tid, model_version="v1"))
    )
    db_session.add(
        Embedding(**_make_embedding_kwargs(project_id=proj.id, target_id=tid, model_version="v2"))
    )
    await db_session.flush()  # 不应抛


# ─────────────── M18-EMBED-T4 modality CHECK ──────────────────────────────


@pytest.mark.parametrize("modality", ["text", "image", "audio"])
async def test_embedding_modality_valid_values(db_session, make_project, modality):
    _user, proj = await make_project()
    db_session.add(Embedding(**_make_embedding_kwargs(project_id=proj.id, modality=modality)))
    await db_session.flush()


async def test_embedding_modality_invalid_violates(db_session, make_project):
    _user, proj = await make_project()
    db_session.add(Embedding(**_make_embedding_kwargs(project_id=proj.id, modality="video")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M18-EMBED-T5 target_type CHECK ───────────────────────────


@pytest.mark.parametrize("target_type", ["node", "dimension_record", "competitor", "issue"])
async def test_embedding_target_type_valid_values(db_session, make_project, target_type):
    _user, proj = await make_project()
    db_session.add(Embedding(**_make_embedding_kwargs(project_id=proj.id, target_type=target_type)))
    await db_session.flush()


async def test_embedding_target_type_invalid_violates(db_session, make_project):
    _user, proj = await make_project()
    db_session.add(Embedding(**_make_embedding_kwargs(project_id=proj.id, target_type="user")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M18-EMBED-T6 provider CHECK ──────────────────────────────


@pytest.mark.parametrize("provider", ["openai", "bge", "mock"])
async def test_embedding_provider_valid_values(db_session, make_project, provider):
    _user, proj = await make_project()
    db_session.add(Embedding(**_make_embedding_kwargs(project_id=proj.id, provider=provider)))
    await db_session.flush()


async def test_embedding_provider_invalid_violates(db_session, make_project):
    _user, proj = await make_project()
    db_session.add(Embedding(**_make_embedding_kwargs(project_id=proj.id, provider="cohere")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M18-EMBED-T7 dim CHECK ───────────────────────────────────


@pytest.mark.parametrize(
    "dim,col,vec",
    [
        (512, "embedding_512", [0.1] * 512),
        (1536, "embedding_1536", [0.1] * 1536),
        (3072, "embedding_3072", [0.1] * 3072),
    ],
)
async def test_embedding_dim_valid_values(db_session, make_project, dim, col, vec):
    _user, proj = await make_project()
    kwargs = _make_embedding_kwargs(
        project_id=proj.id,
        dim=dim,
        embedding_512=None,
        embedding_1536=None,
        embedding_3072=None,
    )
    kwargs[col] = vec
    db_session.add(Embedding(**kwargs))
    await db_session.flush()


async def test_embedding_dim_invalid_violates(db_session, make_project):
    """dim=768（不在 {512, 1536, 3072}）触发 CHECK 约束。"""
    _user, proj = await make_project()
    db_session.add(
        Embedding(
            **_make_embedding_kwargs(
                project_id=proj.id,
                dim=768,
                embedding_512=None,
                embedding_1536=[0.1] * 768,
                embedding_3072=None,
            )
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M18-EMBED-T8 dim_column_consistency CHECK ────────────────


async def test_embedding_dim512_embedding1536_not_null_violates(db_session, make_project):
    """dim=512 时 embedding_1536 必须 NULL（互斥约束）。"""
    _user, proj = await make_project()
    db_session.add(
        Embedding(
            **_make_embedding_kwargs(
                project_id=proj.id,
                dim=512,
                embedding_512=[0.1] * 512,
                embedding_1536=[0.1] * 1536,  # 违规：dim=512 但 1536 非 NULL
                embedding_3072=None,
            )
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_embedding_dim1536_embedding512_not_null_violates(db_session, make_project):
    """dim=1536 时 embedding_512 必须 NULL。"""
    _user, proj = await make_project()
    db_session.add(
        Embedding(
            **_make_embedding_kwargs(
                project_id=proj.id,
                dim=1536,
                embedding_512=[0.1] * 512,  # 违规
                embedding_1536=[0.1] * 1536,
                embedding_3072=None,
            )
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_embedding_all_null_columns_violates(db_session, make_project):
    """三列全 NULL 时触发 dim_column_consistency CHECK。"""
    _user, proj = await make_project()
    db_session.add(
        Embedding(
            **_make_embedding_kwargs(
                project_id=proj.id,
                dim=1536,
                embedding_512=None,
                embedding_1536=None,  # 违规：dim=1536 但 embedding_1536 为 NULL
                embedding_3072=None,
            )
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M18-EMBED-T9 project CASCADE ─────────────────────────────


async def test_embedding_cascade_when_project_deleted(db_session, make_project):
    _user, proj = await make_project()
    emb = Embedding(**_make_embedding_kwargs(project_id=proj.id))
    db_session.add(emb)
    await db_session.flush()
    pk = (
        emb.project_id,
        emb.modality,
        emb.target_type,
        emb.target_id,
        emb.provider,
        emb.model_name,
        emb.model_version,
    )

    await db_session.delete(proj)
    await db_session.flush()
    db_session.expire_all()

    found = await db_session.scalar(
        select(Embedding).where(
            Embedding.project_id == pk[0],
            Embedding.modality == pk[1],
            Embedding.target_type == pk[2],
            Embedding.target_id == pk[3],
            Embedding.provider == pk[4],
            Embedding.model_name == pk[5],
            Embedding.model_version == pk[6],
        )
    )
    assert found is None, "project 删除应级联删 embedding"


# ─────────────── M18-FAILURE-T1 EmbeddingFailure 持久化 + 默认值 ──────────


async def test_embedding_failure_persists_with_defaults(db_session, make_project):
    _user, proj = await make_project()
    failure = EmbeddingFailure(**_make_failure_kwargs(project_id=proj.id))
    db_session.add(failure)
    await db_session.flush()
    await db_session.refresh(failure)

    assert failure.id is not None
    assert failure.retry_count == 0
    assert failure.failed_at is not None
    assert failure.error_code == "PROVIDER_TIMEOUT"
    assert failure.created_at is not None


# ─────────────── M18-FAILURE-T2 target_type CHECK ─────────────────────────


@pytest.mark.parametrize("target_type", ["node", "dimension_record", "competitor", "issue"])
async def test_embedding_failure_target_type_valid(db_session, make_project, target_type):
    _user, proj = await make_project()
    db_session.add(
        EmbeddingFailure(**_make_failure_kwargs(project_id=proj.id, target_type=target_type))
    )
    await db_session.flush()


async def test_embedding_failure_target_type_invalid_violates(db_session, make_project):
    _user, proj = await make_project()
    db_session.add(
        EmbeddingFailure(**_make_failure_kwargs(project_id=proj.id, target_type="bogus"))
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M18-FAILURE-T3 project CASCADE ───────────────────────────


async def test_embedding_failure_cascade_when_project_deleted(db_session, make_project):
    _user, proj = await make_project()
    failure = EmbeddingFailure(**_make_failure_kwargs(project_id=proj.id))
    db_session.add(failure)
    await db_session.flush()
    fid = failure.id

    await db_session.delete(proj)
    await db_session.flush()
    db_session.expire_all()

    found = await db_session.scalar(select(EmbeddingFailure).where(EmbeddingFailure.id == fid))
    assert found is None, "project 删除应级联删 embedding_failure"


# ─────────────── M18-TASK-T1 EmbeddingTaskStatus enum 5 值齐 ──────────────


def test_embedding_task_status_enum_has_5_values():
    """EmbeddingTaskStatus 必须有 5 个值（design §3 line 313-319）。"""
    values = {s.value for s in EmbeddingTaskStatus}
    assert values == {"pending", "running", "succeeded", "failed", "dead_letter"}


def test_embedding_task_statuses_tuple_matches_enum():
    """_EMBEDDING_TASK_STATUSES tuple 与 EmbeddingTaskStatus enum 字面同步（R3-2）。"""
    assert set(_EMBEDDING_TASK_STATUSES) == {s.value for s in EmbeddingTaskStatus}


# ─────────────── M18-TASK-T2 EmbeddingTask 持久化 + 默认值 ───────────────


async def test_embedding_task_persists_with_defaults(db_session, make_project):
    _user, proj = await make_project()
    task = EmbeddingTask(**_make_task_kwargs(project_id=proj.id))
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)

    assert task.id is not None
    assert task.status == EmbeddingTaskStatus.pending.value
    assert task.retry_count == 0
    assert task.error_code is None
    assert task.error_message is None
    assert task.completed_at is None
    assert task.expires_at is None
    assert task.created_at is not None


# ─────────────── M18-TASK-T3 status CHECK 5 状态合法 + 非法拒 ────────────


@pytest.mark.parametrize(
    "status_value", ["pending", "running", "succeeded", "failed", "dead_letter"]
)
async def test_embedding_task_all_5_statuses_allowed(db_session, make_project, status_value):
    _user, proj = await make_project()
    db_session.add(EmbeddingTask(**_make_task_kwargs(project_id=proj.id, status=status_value)))
    await db_session.flush()


async def test_embedding_task_invalid_status_violates(db_session, make_project):
    _user, proj = await make_project()
    db_session.add(EmbeddingTask(**_make_task_kwargs(project_id=proj.id, status="cancelled")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M18-TASK-T4 target_type CHECK ────────────────────────────


async def test_embedding_task_target_type_invalid_violates(db_session, make_project):
    _user, proj = await make_project()
    db_session.add(EmbeddingTask(**_make_task_kwargs(project_id=proj.id, target_type="bogus")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M18-TASK-T5 enqueued_by CHECK ────────────────────────────


@pytest.mark.parametrize("enqueued_by", ["incremental", "backfill", "model_upgrade"])
async def test_embedding_task_enqueued_by_valid(db_session, make_project, enqueued_by):
    _user, proj = await make_project()
    db_session.add(EmbeddingTask(**_make_task_kwargs(project_id=proj.id, enqueued_by=enqueued_by)))
    await db_session.flush()


async def test_embedding_task_enqueued_by_invalid_violates(db_session, make_project):
    _user, proj = await make_project()
    db_session.add(EmbeddingTask(**_make_task_kwargs(project_id=proj.id, enqueued_by="manual")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ─────────────── M18-TASK-T6 project CASCADE ──────────────────────────────


async def test_embedding_task_cascade_when_project_deleted(db_session, make_project):
    _user, proj = await make_project()
    task = EmbeddingTask(**_make_task_kwargs(project_id=proj.id))
    db_session.add(task)
    await db_session.flush()
    tid = task.id

    await db_session.delete(proj)
    await db_session.flush()
    db_session.expire_all()

    found = await db_session.scalar(select(EmbeddingTask).where(EmbeddingTask.id == tid))
    assert found is None, "project 删除应级联删 embedding_task"


# ─────────────── M18-EVAL-T1 SearchEvaluationLog 持久化 ───────────────────


async def test_search_eval_log_persists(db_session, make_project):
    _user, proj = await make_project()
    log = SearchEvaluationLog(**_make_eval_kwargs(project_id=proj.id))
    db_session.add(log)
    await db_session.flush()
    await db_session.refresh(log)

    assert log.id is not None
    assert log.query == "auth service"
    assert log.rrf_k == 60
    assert log.similarity_threshold == 0.7
    assert log.user_clicked_target_type is None
    assert log.user_clicked_target_id is None
    assert log.sampled_at is not None
    assert log.created_at is not None


# ─────────────── M18-EVAL-T2 JSONB 三列 ──────────────────────────────────


async def test_search_eval_log_jsonb_columns(db_session, make_project):
    _user, proj = await make_project()
    top5 = [
        {"target_type": "node", "target_id": str(uuid4()), "score": 0.95},
        {"target_type": "competitor", "target_id": str(uuid4()), "score": 0.88},
    ]
    log = SearchEvaluationLog(
        **_make_eval_kwargs(
            project_id=proj.id,
            keyword_top5=top5,
            semantic_top5=top5,
            hybrid_top5=top5,
        )
    )
    db_session.add(log)
    await db_session.flush()
    await db_session.refresh(log)
    assert log.keyword_top5[0]["score"] == 0.95
    assert len(log.semantic_top5) == 2


# ─────────────── M18-EVAL-T3 user_clicked 字段可 nullable ────────────────


async def test_search_eval_log_nullable_clicked_fields(db_session, make_project):
    _user, proj = await make_project()
    uid = uuid4()
    log = SearchEvaluationLog(
        **_make_eval_kwargs(
            project_id=proj.id,
            user_clicked_target_type="node",
            user_clicked_target_id=uid,
        )
    )
    db_session.add(log)
    await db_session.flush()
    await db_session.refresh(log)
    assert log.user_clicked_target_type == "node"
    assert log.user_clicked_target_id == uid


# ─────────────── M18-EVAL-T4 project CASCADE ──────────────────────────────


async def test_search_eval_cascade_when_project_deleted(db_session, make_project):
    _user, proj = await make_project()
    log = SearchEvaluationLog(**_make_eval_kwargs(project_id=proj.id))
    db_session.add(log)
    await db_session.flush()
    lid = log.id

    await db_session.delete(proj)
    await db_session.flush()
    db_session.expire_all()

    found = await db_session.scalar(
        select(SearchEvaluationLog).where(SearchEvaluationLog.id == lid)
    )
    assert found is None, "project 删除应级联删 search_evaluation_log"


# ─────────────── M18-SYNC-T 横切 enum 对账 ────────────────────────────────


def test_action_type_enum_includes_m18_values():
    """M15 NEW：横切表 owner 模块 enum 字面同步（M18 baseline-patch 已落地）。"""
    from api.models.activity_log import _ACTION_TYPES

    m18_actions = {
        "embedding_model_upgrade_triggered",
        "embedding_backfill_triggered",
    }
    assert m18_actions <= set(_ACTION_TYPES), (
        f"_ACTION_TYPES 缺 M18 值：{m18_actions - set(_ACTION_TYPES)}"
    )


def test_schema_action_type_includes_m18_values():
    """schema StrEnum 与 model._ACTION_TYPES 字面一致（含 M18 新值）。"""
    from api.schemas.activity_stream_schema import ActionType

    assert "embedding_model_upgrade_triggered" in {a.value for a in ActionType}
    assert "embedding_backfill_triggered" in {a.value for a in ActionType}
