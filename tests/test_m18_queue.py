"""M18 embed_single queue task 单元测试（10+）。

mock SessionLocal + CAS 状态机 + advisory lock 占位 + payload 校验。
不需要真实 DB / arq。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from api.errors.exceptions import EmbeddingTargetNotFoundError
from api.models.embedding import EmbeddingTaskStatus
from api.queue.base import SYSTEM_USER_UUID, TaskPayload
from api.schemas.embedding_schema import EmbedSinglePayload
from api.schemas.search_schema import EmbeddingTargetType

# ─── Payload 校验 ────────────────────────────────────────────────────────────


def test_embed_single_payload_valid():
    p = EmbedSinglePayload(
        user_id=uuid4(),
        project_id=uuid4(),
        target_type=EmbeddingTargetType.NODE,
        target_id=uuid4(),
        provider="mock",
        model_name="mock-default",
        model_version="v1",
        enqueued_by="incremental",
    )
    assert p.provider == "mock"


def test_embed_single_payload_system_user_uuid():
    """cron 触发时使用 SYSTEM_USER_UUID。"""
    p = EmbedSinglePayload(
        user_id=SYSTEM_USER_UUID,
        project_id=uuid4(),
        target_type=EmbeddingTargetType.NODE,
        target_id=uuid4(),
        provider="mock",
        model_name="mock-default",
        model_version="v1",
        enqueued_by="backfill",
    )
    assert p.user_id == SYSTEM_USER_UUID


def test_embed_single_payload_extra_forbid():
    """extra='forbid' 防漂移——未知字段应抛 ValidationError。"""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        EmbedSinglePayload(
            user_id=uuid4(),
            project_id=uuid4(),
            target_type=EmbeddingTargetType.NODE,
            target_id=uuid4(),
            provider="mock",
            model_name="mock-default",
            model_version="v1",
            enqueued_by="incremental",
            unknown_field="oops",
        )


def test_embed_single_payload_no_source_text():
    """source_text 禁放 payload（design §12D line 954）。"""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        EmbedSinglePayload(
            user_id=uuid4(),
            project_id=uuid4(),
            target_type=EmbeddingTargetType.NODE,
            target_id=uuid4(),
            provider="mock",
            model_name="mock-default",
            model_version="v1",
            enqueued_by="incremental",
            source_text="forbidden",
        )


# ─── embed_single task mock 测试 ─────────────────────────────────────────────


async def _run_embed_single_with_mock(
    payload: dict,
    *,
    task_found: bool = True,
    provider_raises: Exception | None = None,
    target_not_found: bool = False,
) -> dict:
    """测试辅助：mock 掉所有 DB / provider，直接跑 embed_single 逻辑。"""
    from api.queue.embedding_tasks import embed_single

    mock_task = MagicMock()
    mock_task.id = uuid4()
    mock_task.project_id = payload.get("project_id")
    mock_task.status = "pending"

    mock_running_task = MagicMock()
    mock_running_task.id = mock_task.id

    cas_called_with = {}

    mock_task_dao = AsyncMock()
    mock_task_dao.cas_start_running = AsyncMock(
        return_value=mock_running_task if task_found else None
    )
    mock_task_dao.cas_complete = AsyncMock(
        side_effect=lambda db, tid, status, **kw: cas_called_with.update({"status": status}) or None
    )

    mock_failure_dao = AsyncMock()
    mock_failure_dao.record_failure = AsyncMock()

    mock_embedding_svc = AsyncMock()
    if target_not_found:
        mock_embedding_svc.check_payload_consistency = AsyncMock(
            side_effect=EmbeddingTargetNotFoundError("noop")
        )
    else:
        mock_embedding_svc.check_payload_consistency = AsyncMock()

    if provider_raises:
        mock_embedding_svc.get_or_compute_embedding = AsyncMock(side_effect=provider_raises)
    else:
        mock_embedding_svc.get_or_compute_embedding = AsyncMock(return_value=MagicMock())

    # mock 查询返回 mock_task
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none = MagicMock(return_value=mock_task if task_found else None)
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_scalar)
    mock_db.commit = AsyncMock()
    mock_db.flush = AsyncMock()

    ctx = {}

    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("api.queue.embedding_tasks.EmbeddingTaskDAO", return_value=mock_task_dao),
        patch("api.queue.embedding_tasks.EmbeddingFailureDAO", return_value=mock_failure_dao),
        patch("api.queue.embedding_tasks.EmbeddingService", return_value=mock_embedding_svc),
        patch("api.core.db.SessionLocal", return_value=mock_session_ctx),
    ):
        await embed_single(ctx, raw=payload)

    return {
        "cas_called_with": cas_called_with,
        "failure_recorded": mock_failure_dao.record_failure.called,
        "get_or_compute_called": mock_embedding_svc.get_or_compute_embedding.called,
    }


def _make_raw_payload(**overrides):
    base = {
        "user_id": str(uuid4()),
        "project_id": str(uuid4()),
        "target_type": "node",
        "target_id": str(uuid4()),
        "provider": "mock",
        "model_name": "mock-default",
        "model_version": "v1",
        "enqueued_by": "incremental",
    }
    base.update(overrides)
    return base


async def test_embed_single_success_path():
    result = await _run_embed_single_with_mock(_make_raw_payload())
    assert result["get_or_compute_called"]
    assert result["cas_called_with"]["status"] == EmbeddingTaskStatus.succeeded


async def test_embed_single_target_not_found_noop():
    """target 已删 → noop（不写 failures，不抛）。"""
    result = await _run_embed_single_with_mock(_make_raw_payload(), target_not_found=True)
    assert not result["failure_recorded"]
    assert not result["get_or_compute_called"]


async def test_embed_single_provider_error_records_failure():
    from api.errors.exceptions import EmbeddingProviderFailedError

    result = await _run_embed_single_with_mock(
        _make_raw_payload(),
        provider_raises=EmbeddingProviderFailedError("provider fail"),
    )
    assert result["failure_recorded"]
    assert result["cas_called_with"]["status"] == EmbeddingTaskStatus.failed


async def test_embed_single_invalid_payload_returns_early():
    """无效 payload → model_validate 失败 → 直接 return（不调 DB）。"""
    from api.queue.embedding_tasks import embed_single

    ctx = {}
    invalid_raw = {"not_a_valid": "payload"}

    # 不应抛，只是 return（SessionLocal 不会被调用）
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__ = AsyncMock(
        side_effect=lambda: (_ for _ in ()).throw(Exception("should not reach"))
    )
    mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("api.core.db.SessionLocal", return_value=mock_session_ctx):
        await embed_single(ctx, raw=invalid_raw)

    # 只要不抛即通过
    assert True


async def test_embed_single_no_pending_task_returns_early():
    """DB 中无 pending task → early return，不写 failure。"""
    result = await _run_embed_single_with_mock(_make_raw_payload(), task_found=False)
    assert not result["failure_recorded"]
    assert not result["get_or_compute_called"]


# ─── SYSTEM_USER_UUID 常量 ────────────────────────────────────────────────────


def test_system_user_uuid_format():
    """SYSTEM_USER_UUID 是有效 UUID，不与普通 user.id 撞。"""
    assert str(SYSTEM_USER_UUID) == "00000000-0000-0000-0000-00000000fe00"


def test_task_payload_base_requires_user_and_project():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TaskPayload(user_id=uuid4())  # 缺 project_id

    with pytest.raises(ValidationError):
        TaskPayload(project_id=uuid4())  # 缺 user_id


# ─── advisory lock 占位注释验证 ──────────────────────────────────────────────


def test_advisory_lock_comment_in_source():
    """advisory_xact_lock 双 namespace 实现存在（TODO 注释占位）。"""
    import inspect

    from api.queue import embedding_tasks

    src = inspect.getsource(embedding_tasks)
    assert "pg_advisory_xact_lock" in src
    assert "m18_text_embedding" in src


# ─── 状态机保护 ──────────────────────────────────────────────────────────────


def test_embedding_task_status_values():
    assert EmbeddingTaskStatus.pending == "pending"
    assert EmbeddingTaskStatus.running == "running"
    assert EmbeddingTaskStatus.succeeded == "succeeded"
    assert EmbeddingTaskStatus.failed == "failed"
    assert EmbeddingTaskStatus.dead_letter == "dead_letter"
