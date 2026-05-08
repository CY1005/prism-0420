"""M18 ErrorCode + AppError 子类 + SilentFailure 单元测试（design §13 line 1195-1309）。

5+ 个测试用例：
- 12 ErrorCode 注册验证
- 11 AppError 子类 http_status / code 对应
- SilentFailure 基类继承 BaseException（非 Exception）
- EmbeddingDeleteFailedError 继承 SilentFailure
- R13-1 parity：所有 M18 ErrorCode 有对应子类
"""

from __future__ import annotations

from api.errors.codes import ErrorCode
from api.errors.exceptions import (
    AppError,
    EmbeddingBackfillAlreadyRunningError,
    EmbeddingDeleteFailedError,
    EmbeddingModelUpgradeInvalidError,
    EmbeddingProviderFailedError,
    EmbeddingProviderTimeoutError,
    EmbeddingTargetNotFoundError,
    EmbeddingTaskInvalidTransitionError,
    EmbeddingTaskTerminalViolationError,
    EmbeddingZombieError,
    InvalidQueryLengthError,
    PgvectorUnavailableError,
    SearchTimeoutError,
    SilentFailure,
)

# ─── 12 ErrorCode 注册验证 ─────────────────────────────────────────────────


def test_m18_errorcodes_registered():
    """12 M18 ErrorCode 必须全部注册在 ErrorCode 枚举中。"""
    m18_codes = [
        ErrorCode.INVALID_QUERY_LENGTH,
        ErrorCode.SEARCH_TIMEOUT,
        ErrorCode.PGVECTOR_UNAVAILABLE,
        ErrorCode.EMBEDDING_PROVIDER_FAILED,
        ErrorCode.EMBEDDING_PROVIDER_TIMEOUT,
        ErrorCode.EMBEDDING_TARGET_NOT_FOUND,
        ErrorCode.EMBEDDING_ZOMBIE,
        ErrorCode.EMBEDDING_TASK_TERMINAL_VIOLATION,
        ErrorCode.EMBEDDING_TASK_INVALID_TRANSITION,
        ErrorCode.EMBEDDING_BACKFILL_ALREADY_RUNNING,
        ErrorCode.EMBEDDING_MODEL_UPGRADE_INVALID,
        ErrorCode.EMBEDDING_DELETE_FAILED,
    ]
    assert len(m18_codes) == 12
    # 验证字面值
    assert ErrorCode.INVALID_QUERY_LENGTH == "invalid_query_length"
    assert ErrorCode.EMBEDDING_DELETE_FAILED == "embedding_delete_failed"


def test_errorcodes_are_str_enum():
    """ErrorCode 是 StrEnum——直接比对字符串。"""
    assert str(ErrorCode.INVALID_QUERY_LENGTH) == "invalid_query_length"
    assert ErrorCode.EMBEDDING_PROVIDER_FAILED == "embedding_provider_failed"


# ─── 11 AppError 子类（http_status + code 对应）────────────────────────────


def test_invalid_query_length_error():
    err = InvalidQueryLengthError()
    assert err.code == ErrorCode.INVALID_QUERY_LENGTH
    assert err.http_status == 400
    assert isinstance(err, AppError)


def test_search_timeout_error():
    err = SearchTimeoutError()
    assert err.code == ErrorCode.SEARCH_TIMEOUT
    assert err.http_status == 504


def test_pgvector_unavailable_error():
    err = PgvectorUnavailableError()
    assert err.code == ErrorCode.PGVECTOR_UNAVAILABLE
    assert isinstance(err, AppError)


def test_embedding_provider_failed_error():
    err = EmbeddingProviderFailedError("provider failed")
    assert err.code == ErrorCode.EMBEDDING_PROVIDER_FAILED
    assert err.http_status == 503


def test_embedding_provider_timeout_error():
    err = EmbeddingProviderTimeoutError("timed out")
    assert err.code == ErrorCode.EMBEDDING_PROVIDER_TIMEOUT
    assert err.http_status == 504


def test_embedding_target_not_found_error():
    err = EmbeddingTargetNotFoundError()
    assert err.code == ErrorCode.EMBEDDING_TARGET_NOT_FOUND
    assert isinstance(err, AppError)


def test_embedding_zombie_error():
    err = EmbeddingZombieError()
    assert err.code == ErrorCode.EMBEDDING_ZOMBIE
    assert isinstance(err, AppError)


def test_embedding_task_terminal_violation_error():
    err = EmbeddingTaskTerminalViolationError()
    assert err.code == ErrorCode.EMBEDDING_TASK_TERMINAL_VIOLATION
    assert err.http_status == 500


def test_embedding_task_invalid_transition_error():
    err = EmbeddingTaskInvalidTransitionError()
    assert err.code == ErrorCode.EMBEDDING_TASK_INVALID_TRANSITION
    assert err.http_status == 500


def test_embedding_backfill_already_running_error():
    err = EmbeddingBackfillAlreadyRunningError()
    assert err.code == ErrorCode.EMBEDDING_BACKFILL_ALREADY_RUNNING
    assert err.http_status == 409


def test_embedding_model_upgrade_invalid_error():
    err = EmbeddingModelUpgradeInvalidError()
    assert err.code == ErrorCode.EMBEDDING_MODEL_UPGRADE_INVALID
    assert err.http_status == 400


# ─── SilentFailure 基类 ─────────────────────────────────────────────────────


def test_silent_failure_inherits_base_exception_not_exception():
    """SilentFailure 继承 BaseException 而非 Exception——不被通用 except Exception 捕获。"""
    assert issubclass(SilentFailure, BaseException)
    assert not issubclass(SilentFailure, Exception)


def test_silent_failure_not_caught_by_except_exception():
    """通用 except Exception 不捕获 SilentFailure——验证 issubclass 层次。"""
    # 行为验证：SilentFailure 不是 Exception 的子类，因此 except Exception 不会捕获
    assert not issubclass(SilentFailure, Exception)
    # 进一步验证捕获语义：在函数内部正确捕获到 SilentFailure 必须用显式子句
    sf = SilentFailure(ErrorCode.EMBEDDING_DELETE_FAILED, "test")
    caught_as_base_exception = False
    try:
        raise sf
    except SilentFailure:
        caught_as_base_exception = True
    assert caught_as_base_exception


def test_silent_failure_caught_by_explicit_except():
    """显式 except SilentFailure 可捕获。"""
    sf = SilentFailure(ErrorCode.EMBEDDING_DELETE_FAILED, "delete failed")
    caught = False
    try:
        raise sf
    except SilentFailure:
        caught = True
    assert caught


def test_silent_failure_carries_code_message_metadata():
    from uuid import uuid4

    pid = uuid4()
    sf = SilentFailure(
        ErrorCode.EMBEDDING_DELETE_FAILED,
        "some message",
        project_id=pid,
    )
    assert sf.code == ErrorCode.EMBEDDING_DELETE_FAILED
    assert sf.message == "some message"
    assert sf.metadata["project_id"] == pid


# ─── EmbeddingDeleteFailedError ──────────────────────────────────────────────


def test_embedding_delete_failed_inherits_silent_failure():
    assert issubclass(EmbeddingDeleteFailedError, SilentFailure)
    assert not issubclass(EmbeddingDeleteFailedError, Exception)


def test_embedding_delete_failed_carries_context():
    from uuid import uuid4

    tid = uuid4()
    pid = uuid4()
    err = EmbeddingDeleteFailedError(
        target_type="node",
        target_id=tid,
        project_id=pid,
    )
    assert err.code == ErrorCode.EMBEDDING_DELETE_FAILED
    assert "node" in err.message
    assert str(tid) in err.message
    assert err.metadata["project_id"] == pid


def test_embedding_delete_failed_not_caught_by_except_exception():
    """EmbeddingDeleteFailedError 继承 SilentFailure → 不被 except Exception 捕获。"""

    # 验证继承链：EmbeddingDeleteFailedError → SilentFailure → BaseException（非 Exception）
    assert not issubclass(EmbeddingDeleteFailedError, Exception)
    assert issubclass(EmbeddingDeleteFailedError, SilentFailure)
    assert issubclass(EmbeddingDeleteFailedError, BaseException)


# ─── R13-1 parity 验证（12 ErrorCode 各有子类）─────────────────────────────


def test_r13_1_parity_all_m18_error_codes_have_subclass():
    """R13-1：12 M18 ErrorCode 必须各对应 1 AppError 或 SilentFailure 子类。"""
    mapping = {
        ErrorCode.INVALID_QUERY_LENGTH: InvalidQueryLengthError,
        ErrorCode.SEARCH_TIMEOUT: SearchTimeoutError,
        ErrorCode.PGVECTOR_UNAVAILABLE: PgvectorUnavailableError,
        ErrorCode.EMBEDDING_PROVIDER_FAILED: EmbeddingProviderFailedError,
        ErrorCode.EMBEDDING_PROVIDER_TIMEOUT: EmbeddingProviderTimeoutError,
        ErrorCode.EMBEDDING_TARGET_NOT_FOUND: EmbeddingTargetNotFoundError,
        ErrorCode.EMBEDDING_ZOMBIE: EmbeddingZombieError,
        ErrorCode.EMBEDDING_TASK_TERMINAL_VIOLATION: EmbeddingTaskTerminalViolationError,
        ErrorCode.EMBEDDING_TASK_INVALID_TRANSITION: EmbeddingTaskInvalidTransitionError,
        ErrorCode.EMBEDDING_BACKFILL_ALREADY_RUNNING: EmbeddingBackfillAlreadyRunningError,
        ErrorCode.EMBEDDING_MODEL_UPGRADE_INVALID: EmbeddingModelUpgradeInvalidError,
        ErrorCode.EMBEDDING_DELETE_FAILED: EmbeddingDeleteFailedError,
    }
    assert len(mapping) == 12, "R13-1: must have exactly 12 M18 error code mappings"
    for _code, cls in mapping.items():
        if cls is EmbeddingDeleteFailedError:
            assert issubclass(cls, SilentFailure), f"{cls} must be SilentFailure subclass"
        else:
            assert issubclass(cls, AppError), f"{cls} must be AppError subclass"
