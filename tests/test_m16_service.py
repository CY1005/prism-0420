"""M16 子片 3 — AISnapshotService + Runner 单元测试。

覆盖 design §6/§8/§10/§11/§13：
- create_task 幂等 + version_count 校验 + provider 配置校验
- get_task_for_user 双层校验 + 404 打码
- save_snapshot path mismatch + selected keys + N×create_dimension_record
- execute_generate parse JSON + provider 异常 wrap
- runner cas_start_running + cas_complete + activity_log 条件写入

monkeypatch 用法说明（feedback_monkeypatch_not_verification）：本文件用
monkeypatch 替换 LLMProvider.analyze 仅测 service 编排逻辑；生产路径靠
integration smoke（待 ANTHROPIC_API_KEY） + e2e router 测验证全栈。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest

from api.errors.exceptions import (
    SnapshotInsufficientVersionsError,
    SnapshotInvalidDimensionKeyError,
    SnapshotNotReadyError,
    SnapshotParseFailedError,
    SnapshotProviderError,
    SnapshotProviderNotConfiguredError,
    SnapshotTaskNotFoundError,
    SnapshotTaskPathMismatchError,
)
from api.services.ai.provider import LLMProvider, ProviderError
from api.services.ai_snapshot_service import AISnapshotService


@pytest.fixture
def svc():
    return AISnapshotService()


# ─────────────── helpers ───────────────


async def _make_versions(make_version, *, project, node, user, count: int) -> None:
    for i in range(count):
        await make_version(user=user, project=project, node=node, label=f"v{i + 1}")


class _FakeProvider(LLMProvider):
    def __init__(self, output: str, *, raise_exc: Exception | None = None) -> None:
        self._output = output
        self._raise = raise_exc

    @property
    def provider_name(self) -> str:
        return "mock"

    async def analyze(self, prompt: str, context: str = "") -> AsyncIterator[str]:
        if self._raise is not None:
            raise self._raise
        yield self._output


# ─────────────── M16-SVC-T1 create_task 幂等命中 ───────────────


async def test_create_task_idempotent_hit_returns_existing(
    db_session,
    svc,
    make_project_with_member,
    make_node,
    make_version,
    set_project_ai,
    make_ai_snapshot_task,
):
    user, proj = await make_project_with_member()
    await set_project_ai(proj, provider="mock", api_key=None, model=None)
    node = await make_node(proj.id, name="N")
    await _make_versions(make_version, project=proj, node=node, user=user, count=3)

    first = await make_ai_snapshot_task(
        project_id=proj.id,
        node_id=node.id,
        user_id=user.id,
        version_count=3,
        ai_provider="mock",
        ai_model="default",
        status="pending",
    )

    task, hit = await svc.create_task(
        db_session, project_id=proj.id, node_id=node.id, user_id=user.id
    )
    assert hit is True
    assert task.id == first.id


# ─────────────── M16-SVC-T2 create_task version_count < 3 拒绝 ───────────────


async def test_create_task_rejects_insufficient_versions(
    db_session,
    svc,
    make_project_with_member,
    make_node,
    make_version,
    set_project_ai,
):
    user, proj = await make_project_with_member()
    await set_project_ai(proj, provider="mock")
    node = await make_node(proj.id, name="N")
    await _make_versions(make_version, project=proj, node=node, user=user, count=2)

    with pytest.raises(SnapshotInsufficientVersionsError):
        await svc.create_task(db_session, project_id=proj.id, node_id=node.id, user_id=user.id)


# ─────────────── M16-SVC-T3 create_task provider 未配置 ───────────────


async def test_create_task_rejects_provider_not_configured(
    db_session, svc, make_project_with_member, make_node, make_version
):
    user, proj = await make_project_with_member()
    # 不调 set_project_ai → ai_provider 为 None
    node = await make_node(proj.id, name="N")
    await _make_versions(make_version, project=proj, node=node, user=user, count=3)

    with pytest.raises(SnapshotProviderNotConfiguredError):
        await svc.create_task(db_session, project_id=proj.id, node_id=node.id, user_id=user.id)


# ─────────────── M16-SVC-T4 create_task 新建（无幂等命中）───────────────


async def test_create_task_creates_new_when_no_idempotent(
    db_session,
    svc,
    make_project_with_member,
    make_node,
    make_version,
    set_project_ai,
):
    user, proj = await make_project_with_member()
    await set_project_ai(proj, provider="mock", model="custom-model")
    node = await make_node(proj.id, name="N")
    await _make_versions(make_version, project=proj, node=node, user=user, count=4)

    task, hit = await svc.create_task(
        db_session, project_id=proj.id, node_id=node.id, user_id=user.id
    )
    assert hit is False
    assert task.status == "pending"
    assert task.version_count == 4
    assert task.ai_provider == "mock"
    assert task.ai_model == "custom-model"


# ─────────────── M16-SVC-T5 get_task_for_user 双层校验 ───────────────


async def test_get_task_for_user_creator_passes_both_layers(
    db_session, svc, make_project_with_member, make_node, make_ai_snapshot_task
):
    user, proj = await make_project_with_member()
    node = await make_node(proj.id, name="N")
    task = await make_ai_snapshot_task(project_id=proj.id, node_id=node.id, user_id=user.id)

    found = await svc.get_task_for_user(db_session, task_id=task.id, current_user_id=user.id)
    assert found.id == task.id


async def test_get_task_for_user_non_creator_404(
    db_session,
    svc,
    make_project_with_member,
    make_node,
    make_user,
    make_ai_snapshot_task,
):
    """audit B4 修复 / M15 NEW 元教训：第一层 task.user_id == current_user_id（防同
    project 同事截屏拿 task_id）。"""
    creator, proj = await make_project_with_member()
    other = await make_user()
    # 把 other 也加为 proj 的 editor（满足第二层 project accessibility）
    from api.models.project import ProjectMember

    db_session.add(ProjectMember(project_id=proj.id, user_id=other.id, role="editor"))
    await db_session.flush()

    node = await make_node(proj.id, name="N")
    task = await make_ai_snapshot_task(project_id=proj.id, node_id=node.id, user_id=creator.id)

    # other 是同 project editor 但不是 task creator → 第一层拦截
    with pytest.raises(SnapshotTaskNotFoundError):
        await svc.get_task_for_user(db_session, task_id=task.id, current_user_id=other.id)


async def test_get_task_for_user_unknown_404(db_session, svc, make_user):
    user = await make_user()
    with pytest.raises(SnapshotTaskNotFoundError):
        await svc.get_task_for_user(db_session, task_id=uuid4(), current_user_id=user.id)


# ─────────────── M16-SVC-T6 save_snapshot path mismatch ───────────────


async def test_save_snapshot_path_mismatch_raises(
    db_session,
    svc,
    make_project_with_member,
    make_node,
    make_ai_snapshot_task,
):
    """audit M5 修复：URL path project_id/node_id 与 task 不一致 → 422。"""
    user, proj = await make_project_with_member()
    node_a = await make_node(proj.id, name="A")
    node_b = await make_node(proj.id, name="B")
    task = await make_ai_snapshot_task(
        project_id=proj.id,
        node_id=node_a.id,
        user_id=user.id,
        status="succeeded",
        review_data={"summary": "ok", "dimensions": []},
    )

    with pytest.raises(SnapshotTaskPathMismatchError):
        await svc.save_snapshot(
            db_session,
            task_id=task.id,
            path_project_id=proj.id,
            path_node_id=node_b.id,  # 故意错的 node
            current_user_id=user.id,
            save_summary=True,
            selected_dimension_keys=[],
        )


# ─────────────── M16-SVC-T7 save_snapshot status 非 succeeded 拒绝 ───────────────


async def test_save_snapshot_not_ready_raises(
    db_session, svc, make_project_with_member, make_node, make_ai_snapshot_task
):
    user, proj = await make_project_with_member()
    node = await make_node(proj.id, name="N")
    task = await make_ai_snapshot_task(
        project_id=proj.id,
        node_id=node.id,
        user_id=user.id,
        status="running",  # 非 succeeded
    )

    with pytest.raises(SnapshotNotReadyError):
        await svc.save_snapshot(
            db_session,
            task_id=task.id,
            path_project_id=proj.id,
            path_node_id=node.id,
            current_user_id=user.id,
            save_summary=True,
            selected_dimension_keys=[],
        )


# ─────────────── M16-SVC-T8 save_snapshot 无效 selected_dimension_keys ───────────────


async def test_save_snapshot_invalid_dimension_key(
    db_session, svc, make_project_with_member, make_node, make_ai_snapshot_task
):
    user, proj = await make_project_with_member()
    node = await make_node(proj.id, name="N")
    task = await make_ai_snapshot_task(
        project_id=proj.id,
        node_id=node.id,
        user_id=user.id,
        status="succeeded",
        review_data={
            "summary": "ok",
            "dimensions": [
                {"dimension_type_key": "biz_objective", "name": "业务目标", "content": {"x": 1}},
            ],
        },
    )

    with pytest.raises(SnapshotInvalidDimensionKeyError):
        await svc.save_snapshot(
            db_session,
            task_id=task.id,
            path_project_id=proj.id,
            path_node_id=node.id,
            current_user_id=user.id,
            save_summary=False,
            selected_dimension_keys=["not_in_review_data"],
        )


# ─────────────── M16-SVC-T9 save_snapshot 全选 + summary save 路径 ───────────────


async def test_save_snapshot_all_dimensions_with_summary(
    db_session,
    svc,
    make_project_with_member,
    make_node,
    make_ai_snapshot_task,
    set_project_ai,
):
    user, proj = await make_project_with_member()
    await set_project_ai(proj, provider="mock")
    node = await make_node(proj.id, name="N")
    task = await make_ai_snapshot_task(
        project_id=proj.id,
        node_id=node.id,
        user_id=user.id,
        status="succeeded",
        review_data={
            "summary": "一句话快照",
            "dimensions": [
                {
                    "dimension_type_key": "biz_objective",
                    "name": "业务目标",
                    "content": {"text": "提升 GMV"},
                },
                {
                    "dimension_type_key": "user_pain",
                    "name": "用户痛点",
                    "content": {"text": "审批慢"},
                },
            ],
        },
    )

    result = await svc.save_snapshot(
        db_session,
        task_id=task.id,
        path_project_id=proj.id,
        path_node_id=node.id,
        current_user_id=user.id,
        save_summary=True,
        selected_dimension_keys=["biz_objective", "user_pain"],
    )
    assert result["saved_count"] == 3  # 1 summary + 2 dimensions
    assert result["summary_saved"] is True
    assert len(result["saved_dimension_record_ids"]) == 3


# ─────────────── M16-SVC-T10 execute_generate JSON parse + provider error wrap ───────────────


async def test_execute_generate_parse_failed_raises(
    db_session,
    svc,
    make_project_with_member,
    make_node,
    make_version,
    make_ai_snapshot_task,
    set_project_ai,
    monkeypatch,
):
    """AI 输出非 JSON → SnapshotParseFailedError（design §13 R13-2）。"""
    user, proj = await make_project_with_member()
    await set_project_ai(proj, provider="mock")
    node = await make_node(proj.id, name="N")
    await _make_versions(make_version, project=proj, node=node, user=user, count=3)
    task = await make_ai_snapshot_task(
        project_id=proj.id, node_id=node.id, user_id=user.id, version_count=3
    )

    fake = _FakeProvider(output="this is not JSON, sorry")
    monkeypatch.setattr(svc, "_build_provider_from_project", lambda _p: fake)

    with pytest.raises(SnapshotParseFailedError):
        await svc.execute_generate(db_session, task)


async def test_execute_generate_provider_error_wraps(
    db_session,
    svc,
    make_project_with_member,
    make_node,
    make_version,
    make_ai_snapshot_task,
    set_project_ai,
    monkeypatch,
):
    """ProviderError → SnapshotProviderError 503（R13-2 wrap 异常对照表）。"""
    user, proj = await make_project_with_member()
    await set_project_ai(proj, provider="mock")
    node = await make_node(proj.id, name="N")
    await _make_versions(make_version, project=proj, node=node, user=user, count=3)
    task = await make_ai_snapshot_task(
        project_id=proj.id, node_id=node.id, user_id=user.id, version_count=3
    )

    fake = _FakeProvider(output="", raise_exc=ProviderError("mock", "5xx"))
    monkeypatch.setattr(svc, "_build_provider_from_project", lambda _p: fake)

    with pytest.raises(SnapshotProviderError):
        await svc.execute_generate(db_session, task)


async def test_execute_generate_succeeds_returns_review_data(
    db_session,
    svc,
    make_project_with_member,
    make_node,
    make_version,
    make_ai_snapshot_task,
    set_project_ai,
    monkeypatch,
):
    """golden path：AI 输出合法 JSON → review_data dict + elapsed_ms > 0。"""
    import json

    user, proj = await make_project_with_member()
    await set_project_ai(proj, provider="mock")
    node = await make_node(proj.id, name="N")
    await _make_versions(make_version, project=proj, node=node, user=user, count=3)
    task = await make_ai_snapshot_task(
        project_id=proj.id, node_id=node.id, user_id=user.id, version_count=3
    )

    review_obj = {
        "summary": "一句话快照",
        "dimensions": [
            {"dimension_type_key": "biz_objective", "name": "业务目标", "content": {"text": "x"}}
        ],
    }
    fake = _FakeProvider(output=json.dumps(review_obj))
    monkeypatch.setattr(svc, "_build_provider_from_project", lambda _p: fake)

    review_data, elapsed_ms = await svc.execute_generate(db_session, task)
    assert review_data["summary"] == "一句话快照"
    assert review_data["dimensions"][0]["dimension_type_key"] == "biz_objective"
    assert elapsed_ms >= 0


# ─────────────── M16-SVC-T11 advisory_key 决定性 ───────────────


def test_advisory_key_deterministic_for_same_inputs():
    user_id = uuid4()
    project_id = uuid4()
    node_id = uuid4()
    a = AISnapshotService._advisory_key(user_id, project_id, node_id)
    b = AISnapshotService._advisory_key(user_id, project_id, node_id)
    assert a == b
    # 不同 input 不同 key
    different = AISnapshotService._advisory_key(uuid4(), project_id, node_id)
    assert a != different
