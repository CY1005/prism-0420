"""M18 cron 函数单元测试（8+）。

mock SessionLocal + DAO，测试：
- zombie 识别 + CAS 转换
- 三维阈值告警（ABS / PCT / PER_PROJECT）
- 清理 cron 调 DAO
- backfill_recovery cron 调 detect_and_resume
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from api.cron.embedding_backfill import (
    cron_failure_monitor,
    cron_old_terminal_cleanup,
    cron_zombie_cleanup,
)
from api.cron.embedding_backfill_recovery import cron_backfill_recovery


def _make_mock_db(execute_return=None):
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=[])
    mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


def _patch_session(mock_db):
    """返回 contextmanager mock。"""
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
    return mock_session_ctx


# ─── cron_zombie_cleanup ──────────────────────────────────────────────────────


async def test_cron_zombie_cleanup_no_zombies():
    """无 zombie task → 不调 cas_zombie_transition。"""
    mock_task_dao = AsyncMock()
    mock_task_dao.find_zombie_tasks = AsyncMock(return_value=[])
    mock_task_dao.cas_zombie_transition = AsyncMock()
    mock_db = _make_mock_db()

    with (
        patch("api.dao.embedding_task_dao.EmbeddingTaskDAO", return_value=mock_task_dao),
        patch("api.core.db.SessionLocal", return_value=_patch_session(mock_db)),
        patch("api.cron.embedding_backfill.EmbeddingTaskDAO", return_value=mock_task_dao),
    ):
        # 直接 mock EmbeddingTaskDAO 构造函数
        await cron_zombie_cleanup({})

    mock_task_dao.cas_zombie_transition.assert_not_called()


async def test_cron_zombie_cleanup_transitions_zombies():
    """有 zombie → 逐条调 cas_zombie_transition。"""
    zombie1 = MagicMock()
    zombie1.id = uuid4()
    zombie1.project_id = uuid4()

    zombie2 = MagicMock()
    zombie2.id = uuid4()
    zombie2.project_id = uuid4()

    mock_task_dao = AsyncMock()
    mock_task_dao.find_zombie_tasks = AsyncMock(return_value=[zombie1, zombie2])
    mock_task_dao.cas_zombie_transition = AsyncMock(return_value=MagicMock())
    mock_db = _make_mock_db()

    with (
        patch("api.cron.embedding_backfill.EmbeddingTaskDAO", return_value=mock_task_dao),
        patch("api.core.db.SessionLocal", return_value=_patch_session(mock_db)),
    ):
        await cron_zombie_cleanup({})

    assert mock_task_dao.cas_zombie_transition.call_count == 2


async def test_cron_zombie_cleanup_cas_returns_none_when_race():
    """cas 返回 None（已被其他 worker 处理）→ 不抛。"""
    zombie = MagicMock()
    zombie.id = uuid4()
    zombie.project_id = uuid4()

    mock_task_dao = AsyncMock()
    mock_task_dao.find_zombie_tasks = AsyncMock(return_value=[zombie])
    mock_task_dao.cas_zombie_transition = AsyncMock(return_value=None)
    mock_db = _make_mock_db()

    with (
        patch("api.cron.embedding_backfill.EmbeddingTaskDAO", return_value=mock_task_dao),
        patch("api.core.db.SessionLocal", return_value=_patch_session(mock_db)),
    ):
        await cron_zombie_cleanup({})


# ─── cron_failure_monitor ─────────────────────────────────────────────────────


async def test_cron_failure_monitor_abs_threshold_exceeded_logs_error():
    """全局失败数 >= ABS 阈值 → logger.error（直接 mock 阈值判断逻辑验证）。"""
    # 直接测试 cron 的告警触发逻辑：模拟 count_failures_in_window 返回超阈值
    # per-project 查询返回空
    mock_execute_result = MagicMock()
    mock_execute_result.all = MagicMock(return_value=[])
    mock_db = _make_mock_db()
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    mock_failure_dao = AsyncMock()
    # 600 > _FAILURE_THRESHOLD_ABS = 500 → 应触发告警
    mock_failure_dao.count_failures_in_window = AsyncMock(return_value=600)

    logged_errors = []

    import api.cron.embedding_backfill as cron_mod

    mock_logger = MagicMock()
    mock_logger.debug = MagicMock()
    mock_logger.info = MagicMock()
    mock_logger.warning = MagicMock()
    mock_logger.error = MagicMock(
        side_effect=lambda msg, *a, **kw: logged_errors.append(msg % a if a else msg)
    )

    with (
        patch("api.cron.embedding_backfill.EmbeddingFailureDAO", return_value=mock_failure_dao),
        patch("api.core.db.SessionLocal", return_value=_patch_session(mock_db)),
        patch.object(cron_mod, "log", mock_logger),
    ):
        await cron_failure_monitor({})

    assert any("ABS threshold" in msg for msg in logged_errors), f"logged_errors={logged_errors}"


async def test_cron_failure_monitor_per_project_threshold():
    """単 project 失败数 >= PER_PROJECT 阈值 → logger.error。"""
    # per-project 查询返回超阈值的 row
    project_id = uuid4()
    mock_row = MagicMock()
    mock_row.project_id = project_id
    mock_row.cnt = 150  # > 100

    mock_execute_result = MagicMock()
    mock_execute_result.all = MagicMock(return_value=[mock_row])
    mock_db = _make_mock_db()
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    mock_failure_dao = AsyncMock()
    mock_failure_dao.count_failures_in_window = AsyncMock(return_value=10)  # < ABS

    logged_errors = []
    import api.cron.embedding_backfill as cron_mod

    mock_logger = MagicMock()
    mock_logger.debug = MagicMock()
    mock_logger.info = MagicMock()
    mock_logger.warning = MagicMock()
    mock_logger.error = MagicMock(
        side_effect=lambda msg, *a, **kw: logged_errors.append(msg % a if a else msg)
    )

    with (
        patch("api.cron.embedding_backfill.EmbeddingFailureDAO", return_value=mock_failure_dao),
        patch("api.core.db.SessionLocal", return_value=_patch_session(mock_db)),
        patch.object(cron_mod, "log", mock_logger),
    ):
        await cron_failure_monitor({})

    assert any("PER_PROJECT threshold" in msg for msg in logged_errors), (
        f"logged_errors={logged_errors}"
    )


async def test_cron_failure_monitor_no_alert_when_below_threshold():
    """全局失败数 < ABS 阈值 → 无 threshold exceeded 告警。"""
    mock_execute_result = MagicMock()
    mock_execute_result.all = MagicMock(return_value=[])
    mock_db = _make_mock_db()
    mock_db.execute = AsyncMock(return_value=mock_execute_result)

    mock_failure_dao = AsyncMock()
    mock_failure_dao.count_failures_in_window = AsyncMock(return_value=5)  # < 500

    logged_errors = []
    import api.cron.embedding_backfill as cron_mod

    mock_logger = MagicMock()
    mock_logger.debug = MagicMock()
    mock_logger.info = MagicMock()
    mock_logger.warning = MagicMock()
    mock_logger.error = MagicMock(
        side_effect=lambda msg, *a, **kw: logged_errors.append(msg % a if a else msg)
    )

    with (
        patch("api.cron.embedding_backfill.EmbeddingFailureDAO", return_value=mock_failure_dao),
        patch("api.core.db.SessionLocal", return_value=_patch_session(mock_db)),
        patch.object(cron_mod, "log", mock_logger),
    ):
        await cron_failure_monitor({})

    assert not any("threshold exceeded" in msg for msg in logged_errors)


# ─── cron_old_terminal_cleanup ───────────────────────────────────────────────


async def test_cron_old_terminal_cleanup_calls_delete_methods():
    mock_task_dao = AsyncMock()
    mock_task_dao.delete_old_terminal = AsyncMock(return_value=15)
    mock_failure_dao = AsyncMock()
    mock_failure_dao.delete_old = AsyncMock(return_value=30)
    mock_db = _make_mock_db()

    with (
        patch("api.cron.embedding_backfill.EmbeddingTaskDAO", return_value=mock_task_dao),
        patch("api.cron.embedding_backfill.EmbeddingFailureDAO", return_value=mock_failure_dao),
        patch("api.core.db.SessionLocal", return_value=_patch_session(mock_db)),
    ):
        await cron_old_terminal_cleanup({})

    mock_task_dao.delete_old_terminal.assert_called_once()
    mock_failure_dao.delete_old.assert_called_once()


# ─── cron_backfill_recovery ──────────────────────────────────────────────────


async def test_cron_backfill_recovery_calls_detect_and_resume():
    mock_db = _make_mock_db()
    mock_svc = AsyncMock()
    mock_svc.detect_and_resume_pending_backfill = AsyncMock(return_value=3)

    with (
        patch("api.services.embedding.EmbeddingBackfillService", return_value=mock_svc),
        patch("api.core.db.SessionLocal", return_value=_patch_session(mock_db)),
    ):
        await cron_backfill_recovery({"redis": None})

    mock_svc.detect_and_resume_pending_backfill.assert_called_once()
