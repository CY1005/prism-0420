"""M11 子片 3 — ColdStartOrchestratorService 测试。

覆盖 design §6 orchestrator + §10 activity_log + 异常契约：
- parse_csv：缺列 / 大小超阈值 / 行级校验失败 / golden
- process_csv：file too large / csv invalid / row validation fail / batch insert fail / golden
- 状态机转换：pending → validating → importing/failed → completed/failed
- savepoint 回滚（batch fail 后 task 记录仍存）
"""

from __future__ import annotations

import pytest

from api.errors.exceptions import (
    ColdStartBatchInsertFailedError,
    ColdStartCsvInvalidError,
    ColdStartFileTooLargeError,
    ColdStartRowValidationFailedError,
    ColdStartTaskNotFoundError,
)
from api.models.cold_start_task import ColdStartStatus
from api.services.cold_start_service import (
    MAX_FILE_BYTES,
    ColdStartOrchestratorService,
    parse_csv,
)


@pytest.fixture
def svc():
    return ColdStartOrchestratorService()


# ─────────────── M11-PARSE 解析 ───────────────


def test_parse_csv_minimal_node_only():
    csv_bytes = b"node_path\n/A\n/A/B\n"
    parsed = parse_csv(csv_bytes)
    assert parsed.errors == []
    assert parsed.total_rows == 2
    # /A + /A/B：父子拓扑 / A 只入一次
    names = [n["name"] for n in parsed.nodes_data]
    assert names == ["A", "B"]
    assert parsed.nodes_data[0]["parent_temp_id"] is None
    assert parsed.nodes_data[1]["parent_temp_id"] == parsed.nodes_data[0]["temp_id"]


def test_parse_csv_missing_required_column_raises():
    csv_bytes = b"foo,bar\n1,2\n"
    with pytest.raises(ColdStartCsvInvalidError):
        parse_csv(csv_bytes)


def test_parse_csv_no_header_raises():
    with pytest.raises(ColdStartCsvInvalidError):
        parse_csv(b"")


def test_parse_csv_file_too_large_raises():
    big = b"node_path\n" + (b"/A\n" * (MAX_FILE_BYTES // 3 + 100))
    with pytest.raises(ColdStartFileTooLargeError):
        parse_csv(big)


def test_parse_csv_path_must_start_with_slash():
    csv_bytes = b"node_path\nA\n"
    parsed = parse_csv(csv_bytes)
    assert parsed.errors and parsed.errors[0]["field"] == "node_path"


def test_parse_csv_invalid_issue_category():
    csv_bytes = b"node_path,issue_title,issue_category\n/A,bug-x,not_a_category\n"
    parsed = parse_csv(csv_bytes)
    assert parsed.errors
    assert parsed.errors[0]["field"] == "issue_category"


def test_parse_csv_full_row():
    csv_bytes = (
        b"node_path,node_type,competitor_name,competitor_url,issue_title,"
        b"issue_category,issue_description\n"
        b"/A,folder,CompX,https://x.com,Bug-1,bug,desc\n"
    )
    parsed = parse_csv(csv_bytes)
    assert parsed.errors == []
    assert len(parsed.nodes_data) == 1
    assert len(parsed.competitors_data) == 1
    assert parsed.competitors_data[0]["display_name"] == "CompX"
    assert len(parsed.issues_pending) == 1
    assert parsed.issues_pending[0]["category"] == "bug"


# ─────────────── M11-SVC get_by_id ───────────────


async def test_svc_get_by_id_not_found(db_session, svc, make_project):
    from uuid import uuid4

    _, proj = await make_project()
    with pytest.raises(ColdStartTaskNotFoundError):
        await svc.get_by_id(db_session, project_id=proj.id, task_id=uuid4())


# ─────────────── M11-SVC process_csv golden ───────────────


async def test_svc_process_csv_golden_completes(db_session, svc, make_project):
    user, proj = await make_project()
    csv_bytes = b"node_path\n/A\n/A/B\n/A/C\n"
    task = await svc.process_csv(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        content_bytes=csv_bytes,
        source_filename="test.csv",
    )
    assert task.status == ColdStartStatus.COMPLETED.value
    assert task.total_rows == 3
    assert task.success_rows == 3
    assert task.failed_rows == 0
    assert task.error_report is None
    assert task.completed_at is not None


async def test_svc_process_csv_with_competitors_and_issues(db_session, svc, make_project):
    user, proj = await make_project()
    csv_bytes = (
        b"node_path,competitor_name,issue_title,issue_category\n/A,CompX,Bug-1,bug\n/A/B,CompY,,\n"
    )
    task = await svc.process_csv(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        content_bytes=csv_bytes,
        source_filename="x.csv",
    )
    assert task.status == ColdStartStatus.COMPLETED.value


# ─────────────── M11-SVC process_csv 失败路径 ───────────────


async def test_svc_process_csv_file_too_large_raises(db_session, svc, make_project):
    user, proj = await make_project()
    big = b"x" * (MAX_FILE_BYTES + 1)
    with pytest.raises(ColdStartFileTooLargeError):
        await svc.process_csv(
            db_session,
            project_id=proj.id,
            actor_user_id=user.id,
            content_bytes=big,
            source_filename="big.csv",
        )


async def test_svc_process_csv_invalid_format_marks_failed(db_session, svc, make_project):
    """缺必填列 → ColdStartCsvInvalidError + task 状态=failed + error_report 写入。"""
    user, proj = await make_project()
    csv_bytes = b"foo,bar\n1,2\n"  # 缺 node_path
    with pytest.raises(ColdStartCsvInvalidError):
        await svc.process_csv(
            db_session,
            project_id=proj.id,
            actor_user_id=user.id,
            content_bytes=csv_bytes,
            source_filename="bad.csv",
        )
    # task 仍然存在（pending → validating → failed）
    rows = await svc.list_by_project(db_session, project_id=proj.id, user_id=user.id)
    assert len(rows) == 1
    assert rows[0].status == ColdStartStatus.FAILED.value
    assert rows[0].error_report is not None


async def test_svc_process_csv_row_validation_fail_marks_failed(db_session, svc, make_project):
    """行级校验失败 → ColdStartRowValidationFailedError + status=failed + error_report 行级。"""
    user, proj = await make_project()
    csv_bytes = (
        b"node_path,issue_title,issue_category\n"
        b"/A,Bug-1,not_a_category\n"  # 非法 category
    )
    with pytest.raises(ColdStartRowValidationFailedError):
        await svc.process_csv(
            db_session,
            project_id=proj.id,
            actor_user_id=user.id,
            content_bytes=csv_bytes,
            source_filename="bad.csv",
        )
    rows = await svc.list_by_project(db_session, project_id=proj.id, user_id=user.id)
    assert len(rows) == 1
    assert rows[0].status == ColdStartStatus.FAILED.value
    assert rows[0].failed_rows == 1
    assert rows[0].error_report
    assert rows[0].error_report[0]["field"] == "issue_category"


async def test_svc_process_csv_batch_fail_rolls_back_keeps_task(
    db_session, svc, make_project, monkeypatch
):
    """4 batch_create 任一抛异常 → savepoint 回滚 + task 仍存活 + status=failed。"""
    user, proj = await make_project()

    async def _boom(self, db, **kwargs):
        raise RuntimeError("simulated batch insert failure")

    monkeypatch.setattr("api.services.node_service.NodeService.batch_create_in_transaction", _boom)

    csv_bytes = b"node_path\n/A\n"
    with pytest.raises(ColdStartBatchInsertFailedError):
        await svc.process_csv(
            db_session,
            project_id=proj.id,
            actor_user_id=user.id,
            content_bytes=csv_bytes,
            source_filename="x.csv",
        )

    # task 记录仍存活（外层 txn 没回滚）
    rows = await svc.list_by_project(db_session, project_id=proj.id, user_id=user.id)
    assert len(rows) == 1
    assert rows[0].status == ColdStartStatus.FAILED.value
    assert rows[0].error_report
    assert "_batch" in rows[0].error_report[0]["field"]


async def test_svc_process_csv_pending_to_completed_status_chain(db_session, svc, make_project):
    """状态最终是 completed（已隐式覆盖中间过渡）。"""
    user, proj = await make_project()
    csv_bytes = b"node_path\n/A\n"
    task = await svc.process_csv(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        content_bytes=csv_bytes,
        source_filename="x.csv",
    )
    assert task.status == ColdStartStatus.COMPLETED.value


# ─────────────── M11-SVC list ───────────────


async def test_svc_list_by_project_empty(db_session, svc, make_project):
    user, proj = await make_project()
    rows = await svc.list_by_project(db_session, project_id=proj.id, user_id=user.id)
    assert rows == []


# ─────────────── M11-SVC write_event 异常传播（M04+ 范式） ───────────────


async def test_svc_write_event_exception_propagates(db_session, svc, make_project, monkeypatch):
    """write_event 抛异常应向上传播（M04/M06/M07/M08 范式）。"""
    user, proj = await make_project()

    async def _boom(*args, **kwargs):
        raise RuntimeError("activity log down")

    monkeypatch.setattr("api.services.cold_start_service.write_event", _boom)
    csv_bytes = b"node_path\n/A\n"
    with pytest.raises(RuntimeError, match="activity log down"):
        await svc.process_csv(
            db_session,
            project_id=proj.id,
            actor_user_id=user.id,
            content_bytes=csv_bytes,
            source_filename="x.csv",
        )


# ─────────────── M11-SVC R1-A P1-03 / R1-C P1-03 立修验证 ───────────────


async def test_svc_dimensions_explicit_raise_not_silent(db_session, svc, make_project):
    """R1-A P1-03 立修：dimension_key 列存在但 sprint 未实装 → 必须抛 CsvInvalid，
    不允许静默 completed（保护 R-X1 完整性）。"""
    user, proj = await make_project()
    csv_bytes = b"node_path,dimension_key,dimension_content\n/A,specs,some-content\n"
    with pytest.raises(ColdStartCsvInvalidError):
        await svc.process_csv(
            db_session,
            project_id=proj.id,
            actor_user_id=user.id,
            content_bytes=csv_bytes,
            source_filename="x.csv",
        )
    rows = await svc.list_by_project(db_session, project_id=proj.id, user_id=user.id)
    assert len(rows) == 1
    assert rows[0].status == ColdStartStatus.FAILED.value
    assert rows[0].error_report
    assert rows[0].error_report[0]["field"] == "dimension_key"


# ─────────────── M11-SVC R1-A P1-04 / R1-C P1-01 立修验证 ───────────────


async def test_svc_mark_failed_tolerates_write_event_failure(
    db_session, svc, make_project, monkeypatch
):
    """_mark_failed 内 write_event 抛异常不应遮盖 task 状态落盘 + 不应吞原始异常。

    路径：parse 失败 → _mark_failed → dao.update（落盘 failed）→ write_event 抛 →
    被 _mark_failed 内 try/except 吞 + log warning → process_csv 继续 raise 原始
    ColdStartCsvInvalidError（不是 write_event 的 RuntimeError）。
    """
    user, proj = await make_project()

    async def _selective_boom(*args, **kwargs):
        # 仅 _mark_failed 内的 cold_start.failed 事件抛
        if kwargs.get("action_type") == "cold_start.failed":
            raise RuntimeError("activity log down at failure path")

    monkeypatch.setattr("api.services.cold_start_service.write_event", _selective_boom)

    csv_bytes = b"foo,bar\n1,2\n"  # 缺 node_path → CsvInvalid
    with pytest.raises(ColdStartCsvInvalidError):
        # 关键：上层收到的是 ColdStartCsvInvalidError，不是 RuntimeError
        await svc.process_csv(
            db_session,
            project_id=proj.id,
            actor_user_id=user.id,
            content_bytes=csv_bytes,
            source_filename="x.csv",
        )
    # task 状态仍落 failed（即使 activity_log 抛错）
    rows = await svc.list_by_project(db_session, project_id=proj.id, user_id=user.id)
    assert len(rows) == 1
    assert rows[0].status == ColdStartStatus.FAILED.value
