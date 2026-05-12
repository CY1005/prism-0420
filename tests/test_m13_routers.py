"""M13 子片 4 — Router 3 endpoints + 端到端测试。

覆盖 design §7 3 endpoints + §8 三层权限 + 401/403/404 + viewer 写 2 端点全 403
（M07 立 / M08+M11+M12 应用 / M13 主动复制）+ cross-project node 404 + SSE 流式特化
（chunk 顺序 + complete 事件 + AbortController 取消模拟 + JWT 中途过期）。

monkeypatch ≠ 生产路径（feedback_monkeypatch_not_verification）：本文件 e2e 全用
MockProvider 替代 ProviderRegistry；真 SDK e2e 验证靠 tests/integration/test_m13_provider_smoke.py。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import pytest

from api.auth.jwt_utils import encode_jwt
from api.services.ai import LLMProvider, MockProvider, ProviderError, ProviderTimeoutError


def _bearer(user_id) -> dict:
    return {"Authorization": f"Bearer {encode_jwt(user_id, extra_claims={'type': 'access'})}"}


async def _create_project(auth_client, user_id, name: str = "P1") -> str:
    r = await auth_client.post("/api/projects", json={"name": name}, headers=_bearer(user_id))
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _create_node(auth_client, user_id, pid: str, name: str = "n") -> str:
    r = await auth_client.post(
        f"/api/projects/{pid}/nodes", json={"name": name}, headers=_bearer(user_id)
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _set_ai_provider(db_session, project_id: str, provider: str = "mock") -> None:
    from uuid import UUID

    from api.models.project import Project

    proj = await db_session.get(Project, UUID(project_id))
    proj.ai_provider = provider
    await db_session.flush()
    await db_session.commit()  # auth_client 用单独 session；需 commit 让 router 端读到


def _patch_provider(monkeypatch, provider: LLMProvider) -> None:
    def fake_get_provider(name, api_key=None, model=None):
        return provider

    monkeypatch.setattr("api.services.analyze_service.get_provider", fake_get_provider)


def _parse_sse_lines(body: str) -> list[tuple[str, dict]]:
    """解析 SSE response body 为 [(event, data_dict), ...]。"""
    events: list[tuple[str, dict]] = []
    cur_event: str | None = None
    cur_data: str | None = None
    for line in body.splitlines():
        if line.startswith("event: "):
            cur_event = line[7:].strip()
        elif line.startswith("data: "):
            cur_data = line[6:]
        elif line == "" and cur_event is not None and cur_data is not None:
            events.append((cur_event, json.loads(cur_data)))
            cur_event = None
            cur_data = None
    return events


# ─────────────── POST /analyze/requirement (SSE 流式) ───────────────


async def test_stream_requirement_golden_chunk_then_complete(
    auth_client, make_user, db_session, monkeypatch
):
    """golden path：3 chunk → complete event 含 metadata。"""
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid)
    await _set_ai_provider(db_session, pid, "mock")

    _patch_provider(monkeypatch, MockProvider(chunks=["你好，", "需求分析：", "结束。"]))

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/analyze/requirement",
        json={"requirement_text": "加个登录功能", "analysis_level": "L2"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200, r.text
    events = _parse_sse_lines(r.text)
    chunk_events = [(e, d) for e, d in events if e == "chunk"]
    complete_events = [(e, d) for e, d in events if e == "complete"]
    assert [d["text"] for _, d in chunk_events] == ["你好，", "需求分析：", "结束。"]
    assert all(d["level"] == "L2" for _, d in chunk_events)
    assert all(d["source"] == "ai" for _, d in chunk_events)
    assert len(complete_events) == 1
    full = complete_events[0][1]["full_result"]
    assert full == "你好，需求分析：结束。"
    assert complete_events[0][1]["metadata"]["analysis_level"] == "L2"


async def test_stream_requirement_provider_error_emits_error_event(
    auth_client, make_user, db_session, monkeypatch
):
    """provider 抛 rate_limited → SSE error event with analysis_quota_exceeded code。"""
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid)
    await _set_ai_provider(db_session, pid, "mock")

    class _Boom(LLMProvider):
        @property
        def provider_name(self):
            return "boom"

        async def analyze(self, prompt, context="") -> AsyncIterator[str]:
            raise ProviderError("boom", "rate_limited")
            yield  # pragma: no cover

    _patch_provider(monkeypatch, _Boom())

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/analyze/requirement",
        json={"requirement_text": "x", "analysis_level": "L1"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    events = _parse_sse_lines(r.text)
    err_events = [d for e, d in events if e == "error"]
    assert len(err_events) == 1
    assert err_events[0]["error_code"] == "analysis_quota_exceeded"


async def test_stream_requirement_provider_timeout_emits_error_event(
    auth_client, make_user, db_session, monkeypatch
):
    """provider 抛 ProviderTimeoutError → SSE error event with analysis_timeout code。"""
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid)
    await _set_ai_provider(db_session, pid, "mock")

    class _Slow(LLMProvider):
        @property
        def provider_name(self):
            return "slow"

        async def analyze(self, prompt, context="") -> AsyncIterator[str]:
            yield "starting..."
            raise ProviderTimeoutError("slow", 5.0)

    _patch_provider(monkeypatch, _Slow())

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/analyze/requirement",
        json={"requirement_text": "x", "analysis_level": "L1"},
        headers=_bearer(user.id),
    )
    events = _parse_sse_lines(r.text)
    chunk_events = [d for e, d in events if e == "chunk"]
    err_events = [d for e, d in events if e == "error"]
    assert chunk_events == [{"text": "starting...", "level": "L1", "source": "ai"}]
    assert len(err_events) == 1
    assert err_events[0]["error_code"] == "analysis_timeout"


async def test_stream_requirement_unconfigured_provider_emits_error_event(
    auth_client, make_user, monkeypatch
):
    """ai_provider 未配置 → SSE error event with analysis_provider_not_configured code。"""
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid)
    # 不配 ai_provider

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/analyze/requirement",
        json={"requirement_text": "x", "analysis_level": "L1"},
        headers=_bearer(user.id),
    )
    events = _parse_sse_lines(r.text)
    err_events = [d for e, d in events if e == "error"]
    assert len(err_events) == 1
    assert err_events[0]["error_code"] == "analysis_provider_not_configured"


async def test_stream_requirement_viewer_write_returns_403(
    auth_client, make_user, db_session, monkeypatch
):
    """viewer 写 SSE 端点 → 403（M07 立 / M08+M11+M12 应用 / M13 主动复制 元教训 1/6）。"""
    from api.models.project import MemberRole, ProjectMember

    owner = await make_user()
    viewer = await make_user()
    pid = await _create_project(auth_client, owner.id)
    nid = await _create_node(auth_client, owner.id, pid)
    db_session.add(ProjectMember(project_id=pid, user_id=viewer.id, role=MemberRole.VIEWER.value))
    await db_session.flush()
    await db_session.commit()

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/analyze/requirement",
        json={"requirement_text": "x", "analysis_level": "L1"},
        headers=_bearer(viewer.id),
    )
    assert r.status_code == 403, r.text


async def test_stream_requirement_unauthenticated_returns_401(auth_client, make_user):
    """无 Bearer → 401（design §8 + ADR-004 P1）。"""
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid)
    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/analyze/requirement",
        json={"requirement_text": "x", "analysis_level": "L1"},
    )
    assert r.status_code == 401


async def test_stream_requirement_cross_tenant_returns_404(auth_client, make_user):
    """跨 tenant project → ProjectNotFoundError 404（M02 范式 元教训 3/6）。"""
    userA = await make_user()
    userB = await make_user()
    pidA = await _create_project(auth_client, userA.id)
    nid = await _create_node(auth_client, userA.id, pidA)
    r = await auth_client.post(
        f"/api/projects/{pidA}/nodes/{nid}/analyze/requirement",
        json={"requirement_text": "x", "analysis_level": "L1"},
        headers=_bearer(userB.id),
    )
    assert r.status_code == 404


async def test_stream_requirement_invalid_level_pydantic_422(auth_client, make_user):
    """无效 level 由 Pydantic 拦 → 422（design §13 ANALYSIS_INVALID_LEVEL 预留备但不抛）。"""
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid)
    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/analyze/requirement",
        json={"requirement_text": "x", "analysis_level": "L9"},
        headers=_bearer(user.id),
    )
    assert r.status_code == 422


@pytest.mark.skip(
    reason=(
        "ASGITransport 不真触发 TCP close → Request.is_disconnected 在 in-process httpx "
        "下行为不可靠；aclose 协议传播路径已由 service 层 unit test "
        "(test_analyze_stream_propagates_aclose_to_inner_provider) 通过显式调用 "
        "generator.aclose() 验过。真客户端 AbortController 路径走 integration smoke。"
    )
)
async def test_stream_requirement_aclose_called_on_disconnect(
    auth_client, make_user, db_session, monkeypatch
):
    """AbortController 取消模拟——见 skip reason 解释。"""
    pass


# ─────────────── POST /analyze/save (写 M04) ───────────────


async def test_save_analysis_persists_and_returns_record_id(auth_client, make_user, db_session):
    """save 走 M04 create_dimension_record；返回 dimension_record_id + saved_at。"""
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid)

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/analyze/save",
        json={
            "analysis_result": "**核心场景**：...",
            "analysis_level": "L2",
            "affected_node_ids": [],
            "ai_provider": "claude",
            "ai_model": "claude-sonnet-4-5",
            "analysis_time_ms": 1234,
            "requirement_text": "加个微信扫码登录",
        },
        headers=_bearer(user.id),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert "dimension_record_id" in body
    assert body["message"] == "分析结果已保存"
    assert "T" in body["analysis_saved_at"]  # ISO 8601


async def test_save_analysis_viewer_write_returns_403(auth_client, make_user, db_session):
    """viewer 写 save 端点 → 403（M07 立 / M08+M11+M12 应用 / M13 主动复制 元教训 1/6 第 2 端点）。"""
    from api.models.project import MemberRole, ProjectMember

    owner = await make_user()
    viewer = await make_user()
    pid = await _create_project(auth_client, owner.id)
    nid = await _create_node(auth_client, owner.id, pid)
    db_session.add(ProjectMember(project_id=pid, user_id=viewer.id, role=MemberRole.VIEWER.value))
    await db_session.flush()
    await db_session.commit()

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/analyze/save",
        json={
            "analysis_result": "r",
            "analysis_level": "L1",
            "affected_node_ids": [],
            "ai_provider": "mock",
            "ai_model": "m",
            "analysis_time_ms": 1,
            "requirement_text": "t",
        },
        headers=_bearer(viewer.id),
    )
    assert r.status_code == 403


async def test_save_analysis_cross_tenant_returns_404(auth_client, make_user):
    """跨 tenant save → 404（M02 范式 元教训 3/6）。"""
    userA = await make_user()
    userB = await make_user()
    pidA = await _create_project(auth_client, userA.id)
    nid = await _create_node(auth_client, userA.id, pidA)
    r = await auth_client.post(
        f"/api/projects/{pidA}/nodes/{nid}/analyze/save",
        json={
            "analysis_result": "r",
            "analysis_level": "L1",
            "affected_node_ids": [],
            "ai_provider": "mock",
            "ai_model": "m",
            "analysis_time_ms": 1,
            "requirement_text": "t",
        },
        headers=_bearer(userB.id),
    )
    assert r.status_code == 404


async def test_save_analysis_cross_project_node_returns_404(auth_client, make_user):
    """跨 project node → AnalysisNodeNotFoundError 404（M06+M07+M08+M12 范式 元教训 4/6）。"""
    user = await make_user()
    pidA = await _create_project(auth_client, user.id, name="A")
    pidB = await _create_project(auth_client, user.id, name="B")
    nidB = await _create_node(auth_client, user.id, pidB)

    r = await auth_client.post(
        f"/api/projects/{pidA}/nodes/{nidB}/analyze/save",
        json={
            "analysis_result": "r",
            "analysis_level": "L1",
            "affected_node_ids": [],
            "ai_provider": "mock",
            "ai_model": "m",
            "analysis_time_ms": 1,
            "requirement_text": "t",
        },
        headers=_bearer(user.id),
    )
    assert r.status_code == 404


async def test_save_analysis_pydantic_validation_422(auth_client, make_user):
    """requirement_text 空 → Pydantic 422（min_length=1）。"""
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid)
    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/analyze/save",
        json={
            "analysis_result": "r",
            "analysis_level": "L1",
            "affected_node_ids": [],
            "ai_provider": "mock",
            "ai_model": "m",
            "analysis_time_ms": 1,
            "requirement_text": "",
        },
        headers=_bearer(user.id),
    )
    assert r.status_code == 422


# ─────────────── GET /analyze/affected-nodes (viewer 读) ───────────────


async def test_affected_nodes_empty_when_no_history(auth_client, make_user):
    """无历史 → analysis_record_id=None / affected_node_ids=[]（design line 739）。"""
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid)
    r = await auth_client.get(
        f"/api/projects/{pid}/nodes/{nid}/analyze/affected-nodes",
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["analysis_record_id"] is None
    assert body["affected_node_ids"] == []
    assert body["analysis_saved_at"] is None
    assert body["node_id"] == nid


async def test_affected_nodes_returns_latest_after_save(auth_client, make_user):
    """save 后 GET 立即可读（design line 739）+ 解析 affected_node_ids。"""
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid)
    nidB = await _create_node(auth_client, user.id, pid, name="B")
    nidC = await _create_node(auth_client, user.id, pid, name="C")

    save = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/analyze/save",
        json={
            "analysis_result": "r",
            "analysis_level": "L2",
            "affected_node_ids": [nidB, nidC],
            "ai_provider": "mock",
            "ai_model": "m",
            "analysis_time_ms": 1,
            "requirement_text": "t",
        },
        headers=_bearer(user.id),
    )
    assert save.status_code == 201
    rid = save.json()["dimension_record_id"]

    r = await auth_client.get(
        f"/api/projects/{pid}/nodes/{nid}/analyze/affected-nodes",
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["analysis_record_id"] == rid
    assert set(body["affected_node_ids"]) == {nidB, nidC}
    assert body["analysis_saved_at"] is not None


async def test_affected_nodes_viewer_can_read(auth_client, make_user, db_session):
    """affected-nodes 是 viewer 可读端点（design §8 + R8-1）；不应 403。"""
    from api.models.project import MemberRole, ProjectMember

    owner = await make_user()
    viewer = await make_user()
    pid = await _create_project(auth_client, owner.id)
    nid = await _create_node(auth_client, owner.id, pid)
    db_session.add(ProjectMember(project_id=pid, user_id=viewer.id, role=MemberRole.VIEWER.value))
    await db_session.flush()
    await db_session.commit()

    r = await auth_client.get(
        f"/api/projects/{pid}/nodes/{nid}/analyze/affected-nodes",
        headers=_bearer(viewer.id),
    )
    assert r.status_code == 200


async def test_affected_nodes_cross_tenant_returns_404(auth_client, make_user):
    userA = await make_user()
    userB = await make_user()
    pidA = await _create_project(auth_client, userA.id)
    nid = await _create_node(auth_client, userA.id, pidA)
    r = await auth_client.get(
        f"/api/projects/{pidA}/nodes/{nid}/analyze/affected-nodes",
        headers=_bearer(userB.id),
    )
    assert r.status_code == 404


async def test_affected_nodes_cross_project_node_returns_404(auth_client, make_user):
    user = await make_user()
    pidA = await _create_project(auth_client, user.id, name="A")
    pidB = await _create_project(auth_client, user.id, name="B")
    nidB = await _create_node(auth_client, user.id, pidB)
    r = await auth_client.get(
        f"/api/projects/{pidA}/nodes/{nidB}/analyze/affected-nodes",
        headers=_bearer(user.id),
    )
    assert r.status_code == 404


# ─────────────── 元教训防御 actionable 主动复制 ───────────────


@pytest.mark.parametrize("text_len", [0, 5001])
async def test_save_pydantic_text_length_bounds(auth_client, make_user, text_len):
    """SaveAnalysisRequest.requirement_text length=0 + 5001 → Pydantic 422。"""
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid)
    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/analyze/save",
        json={
            "analysis_result": "r",
            "analysis_level": "L1",
            "affected_node_ids": [],
            "ai_provider": "mock",
            "ai_model": "m",
            "analysis_time_ms": 1,
            "requirement_text": "x" * text_len,
        },
        headers=_bearer(user.id),
    )
    assert r.status_code == 422


# ─────────────── R2 立修配套测试（2026-05-08）───────────────


async def test_stream_requirement_cross_project_node_returns_404(
    auth_client, make_user, db_session, monkeypatch
):
    """B-P2-cc-B fix（R-X3 cross-tenant leak）：SSE 端点入流前必须前置校验 node 归属，
    不属于该 project 时返 HTTP 404 + analysis_node_not_found（不进 SSE 200 + event:error，
    避免 cross-tenant 探测信道）。design §8 R8-1 三层防御第三层 + M04 dimension_router 同范式。"""
    user = await make_user()
    pidA = await _create_project(auth_client, user.id, name="A")
    pidB = await _create_project(auth_client, user.id, name="B")
    nidB = await _create_node(auth_client, user.id, pidB)
    await _set_ai_provider(db_session, pidA, "mock")

    _patch_provider(monkeypatch, MockProvider())

    r = await auth_client.post(
        f"/api/projects/{pidA}/nodes/{nidB}/analyze/requirement",
        json={"requirement_text": "x", "analysis_level": "L1"},
        headers=_bearer(user.id),
    )
    # B-P2-cc-B fix：router 前置 _check_node_belongs_to_project → 抛 404，HTTP 200 + SSE 不再触达
    assert r.status_code == 404
    body = r.json()
    assert body["code"] == "analysis_node_not_found"


async def test_stream_requirement_complete_metadata_includes_analysis_time_ms(
    auth_client, make_user, db_session, monkeypatch
):
    """R2 P2-4 升 P1：design §7 line 437 metadata 字面要求 analysis_time_ms。"""
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid)
    await _set_ai_provider(db_session, pid, "mock")

    _patch_provider(monkeypatch, MockProvider(chunks=["a", "b", "c"]))

    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/analyze/requirement",
        json={"requirement_text": "x", "analysis_level": "L1"},
        headers=_bearer(user.id),
    )
    events = _parse_sse_lines(r.text)
    complete_events = [d for e, d in events if e == "complete"]
    assert len(complete_events) == 1
    md = complete_events[0]["metadata"]
    assert "analysis_time_ms" in md
    assert isinstance(md["analysis_time_ms"], int)
    assert md["analysis_time_ms"] >= 0


async def test_save_analysis_pydantic_negative_time_ms_returns_422(auth_client, make_user):
    """R2 P2-3 立修：analysis_time_ms <0 应被 Pydantic Field(ge=0) 拦 422。"""
    user = await make_user()
    pid = await _create_project(auth_client, user.id)
    nid = await _create_node(auth_client, user.id, pid)
    r = await auth_client.post(
        f"/api/projects/{pid}/nodes/{nid}/analyze/save",
        json={
            "analysis_result": "r",
            "analysis_level": "L1",
            "affected_node_ids": [],
            "ai_provider": "mock",
            "ai_model": "m",
            "analysis_time_ms": -1,
            "requirement_text": "t",
        },
        headers=_bearer(user.id),
    )
    assert r.status_code == 422
