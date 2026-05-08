"""api/queue/base.py 单元测试 — 闸门 2.6 mini-sprint（2026-05-09 M17 sprint 启动期）。

覆盖：
- TaskPayload 强制 user_id + project_id（缺则 ValidationError）
- TaskPayload extra='forbid'（多字段 / 拼错字段名抛错防漂移）
- SYSTEM_USER_UUID 字面值固定（cron user_id 边界 ADR-002 §1.1）
- dummy 子类继承父字段约束 + 自身字段
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from api.queue.base import SYSTEM_USER_UUID, TaskPayload


class DummyImportPayload(TaskPayload):
    """闸门 2.6 mini-sprint dummy 子类（仅测试用）；M17 业务子类在 sprint 子片 3 落。"""

    task_id: UUID


def test_system_user_uuid_value_fixed() -> None:
    assert str(SYSTEM_USER_UUID) == "00000000-0000-0000-0000-00000000fe00"


def test_task_payload_requires_user_id() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TaskPayload(project_id=uuid4())  # type: ignore[call-arg]
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("user_id",) and e["type"] == "missing" for e in errors)


def test_task_payload_requires_project_id() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TaskPayload(user_id=uuid4())  # type: ignore[call-arg]
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("project_id",) and e["type"] == "missing" for e in errors)


def test_task_payload_forbids_extra_fields() -> None:
    """防上游漂移（多打字段 / 拼错字段名静默丢失）。"""
    with pytest.raises(ValidationError) as exc_info:
        TaskPayload(
            user_id=uuid4(),
            project_id=uuid4(),
            unexpected_field="anything",  # type: ignore[call-arg]
        )
    errors = exc_info.value.errors()
    assert any(e["type"] == "extra_forbidden" for e in errors)


def test_task_payload_user_id_must_be_uuid() -> None:
    with pytest.raises(ValidationError):
        TaskPayload(user_id="not-a-uuid", project_id=uuid4())  # type: ignore[arg-type]


def test_task_payload_project_id_must_be_uuid() -> None:
    with pytest.raises(ValidationError):
        TaskPayload(user_id=uuid4(), project_id="not-a-uuid")  # type: ignore[arg-type]


def test_task_payload_accepts_uuid_strings_via_pydantic_coercion() -> None:
    """Pydantic v2 会把合法 UUID 字符串自动 coerce 为 UUID 类型。"""
    user_id_str = str(uuid4())
    project_id_str = str(uuid4())
    payload = TaskPayload(user_id=user_id_str, project_id=project_id_str)  # type: ignore[arg-type]
    assert isinstance(payload.user_id, UUID)
    assert isinstance(payload.project_id, UUID)
    assert str(payload.user_id) == user_id_str
    assert str(payload.project_id) == project_id_str


def test_task_payload_with_system_user_uuid() -> None:
    """cron / 系统任务必须用 SYSTEM_USER_UUID（ADR-002 §1.1）。"""
    payload = TaskPayload(user_id=SYSTEM_USER_UUID, project_id=uuid4())
    assert payload.user_id == SYSTEM_USER_UUID


def test_dummy_subclass_inherits_parent_validation() -> None:
    """子类必须继承父字段约束（user_id + project_id 强制）。"""
    with pytest.raises(ValidationError) as exc_info:
        DummyImportPayload(task_id=uuid4())  # type: ignore[call-arg]
    errors = exc_info.value.errors()
    missing_fields = {tuple(e["loc"]) for e in errors if e["type"] == "missing"}
    assert ("user_id",) in missing_fields
    assert ("project_id",) in missing_fields


def test_dummy_subclass_accepts_all_required_fields() -> None:
    user_id = uuid4()
    project_id = uuid4()
    task_id = uuid4()
    payload = DummyImportPayload(
        user_id=user_id,
        project_id=project_id,
        task_id=task_id,
    )
    assert payload.user_id == user_id
    assert payload.project_id == project_id
    assert payload.task_id == task_id


def test_dummy_subclass_also_forbids_extra_fields() -> None:
    """extra='forbid' 通过 ConfigDict 继承到子类。"""
    with pytest.raises(ValidationError) as exc_info:
        DummyImportPayload(
            user_id=uuid4(),
            project_id=uuid4(),
            task_id=uuid4(),
            unexpected="x",  # type: ignore[call-arg]
        )
    errors = exc_info.value.errors()
    assert any(e["type"] == "extra_forbidden" for e in errors)


def test_task_payload_round_trip_via_model_dump() -> None:
    """arq raw payload (dict) ↔ TaskPayload round-trip（Queue 消费者入口范式）。"""
    original = DummyImportPayload(user_id=uuid4(), project_id=uuid4(), task_id=uuid4())
    raw = original.model_dump(mode="json")
    assert isinstance(raw["user_id"], str)
    assert isinstance(raw["project_id"], str)
    assert isinstance(raw["task_id"], str)

    restored = DummyImportPayload.model_validate(raw)
    assert restored == original
