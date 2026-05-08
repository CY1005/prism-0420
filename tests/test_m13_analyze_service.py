"""M13 子片 2 — AnalyzeService 单元测试。

覆盖：
  - analyze_stream: ai_provider 配置缺失/解密失败/未知 provider/超时/限流/普通错 全 wrap
  - analyze_stream: cross-tenant project 拦截（M02 范式）+ cross-project node 404
  - analyze_stream: prompt 上下文聚合（subtree 2 层 + issues + breadcrumb 进 prompt）
  - save_analysis: 写 M04 ✅ + extra_metadata 合并 + caller 异常 wrap AnalysisSaveFailedError
  - save_analysis: cross-project node → AnalysisNodeNotFoundError 404（M04 _check_node_belongs_to_project 透传）
  - get_affected_nodes: 无历史 → empty result + 有历史 → 解析 affected_node_ids
  - viewer 写 N/A（service 层不查角色，由 router check_project_access editor 拦；e2e 子片 4 验）
  - LLM monkeypatch 用 MockProvider（ProviderRegistry 注入）替代 monkeypatch httpx

monkeypatch ≠ 生产路径（feedback_monkeypatch_not_verification）：本文件全 unit；
真 SDK e2e 验证靠 tests/integration/test_m13_provider_smoke.py + skipif key。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest

from api.auth.crypto import encrypt
from api.errors.exceptions import (
    AnalysisNodeNotFoundError,
    AnalysisProviderError,
    AnalysisProviderNotConfiguredError,
    AnalysisQuotaExceededError,
    AnalysisSaveFailedError,
    AnalysisTimeoutError,
    ProjectNotFoundError,
)
from api.schemas.analyze_schema import AnalysisLevel
from api.services.ai import (
    LLMProvider,
    MockProvider,
    ProviderError,
    ProviderTimeoutError,
)
from api.services.analyze_service import REQUIREMENT_ANALYSIS_KEY, AnalyzeService

# ─────────────── helpers ───────────────


@pytest.fixture
def svc():
    return AnalyzeService()


async def _add_member(db_session, project, user, *, role="owner"):
    """make_project 不自动建 ProjectMember，service 层 get_for_user 校验 member 关系——
    M13 service 测试都依赖此校验，所以测试 setup 中显式 add 一条 owner ProjectMember。"""
    from api.models.project import ProjectMember

    db_session.add(ProjectMember(project_id=project.id, user_id=user.id, role=role))
    await db_session.flush()


async def _set_project_ai(db_session, project, *, provider="mock", api_key=None, model=None):
    """配置 project 的 ai_provider / ai_api_key_enc / ai_model 字段。"""
    project.ai_provider = provider
    if api_key is not None:
        project.ai_api_key_enc = encrypt(api_key)
    if model is not None:
        project.ai_model = model
    await db_session.flush()


async def _make_proj_with_member(make_project, db_session, *, name_suffix="", owner=None):
    """make_project + add owner membership（M13 service 测试默认形态）。"""
    user, proj = await make_project(name_suffix=name_suffix, owner=owner)
    await _add_member(db_session, proj, user)
    return user, proj


class _ScriptedProvider(LLMProvider):
    """测试用 provider — 可控 yield + 可主动抛异常。"""

    def __init__(self, chunks=None, raise_exc: Exception | None = None):
        self._chunks = chunks if chunks is not None else ["x"]
        self._raise_exc = raise_exc
        self.aclose_called = False

    @property
    def provider_name(self) -> str:
        return "scripted"

    async def analyze(self, prompt: str, context: str = "") -> AsyncIterator[str]:
        try:
            for c in self._chunks:
                yield c
            if self._raise_exc:
                raise self._raise_exc
        except GeneratorExit:
            self.aclose_called = True
            raise


def _patch_get_provider(monkeypatch, fixed_provider: LLMProvider):
    """让 AnalyzeService._build_provider_from_project 内部 get_provider 返回固定 provider。"""

    def fake_get_provider(name, api_key=None, model=None):
        return fixed_provider

    monkeypatch.setattr("api.services.analyze_service.get_provider", fake_get_provider)


# ─────────────── analyze_stream — config 路径 ───────────────


async def test_analyze_stream_raises_when_ai_provider_unset(
    db_session, svc, make_project, make_node
):
    user, proj = await _make_proj_with_member(make_project, db_session)
    node = await make_node(proj.id, name="N1")
    # 不配 ai_provider
    with pytest.raises(AnalysisProviderNotConfiguredError) as ei:
        async for _ in svc.analyze_stream(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            user_id=user.id,
            requirement_text="加个登录功能",
            level=AnalysisLevel.L2,
        ):
            pass
    assert ei.value.details.get("reason") == "ai_provider_unset"


async def test_analyze_stream_raises_when_api_key_decrypt_fails(
    db_session, svc, make_project, make_node, monkeypatch
):
    user, proj = await _make_proj_with_member(make_project, db_session)
    node = await make_node(proj.id, name="N1")
    proj.ai_provider = "claude"
    proj.ai_api_key_enc = "this-is-not-valid-base64!!!" * 3  # 触发 decrypt 错
    await db_session.flush()
    with pytest.raises(AnalysisProviderNotConfiguredError) as ei:
        async for _ in svc.analyze_stream(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            user_id=user.id,
            requirement_text="加个登录功能",
            level=AnalysisLevel.L1,
        ):
            pass
    assert ei.value.details.get("reason") == "api_key_decrypt_failed"


async def test_analyze_stream_unknown_provider_wraps_to_not_configured(
    db_session, svc, make_project, make_node
):
    user, proj = await _make_proj_with_member(make_project, db_session)
    node = await make_node(proj.id, name="N1")
    proj.ai_provider = "gpt-9000"  # 未知
    await db_session.flush()
    with pytest.raises(AnalysisProviderNotConfiguredError):
        async for _ in svc.analyze_stream(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            user_id=user.id,
            requirement_text="加个登录功能",
            level=AnalysisLevel.L2,
        ):
            pass


# ─────────────── analyze_stream — provider 调用路径 ───────────────


async def test_analyze_stream_yields_provider_chunks(
    db_session, svc, make_project, make_node, monkeypatch
):
    user, proj = await _make_proj_with_member(make_project, db_session)
    node = await make_node(proj.id, name="N1")
    await _set_project_ai(db_session, proj, provider="mock")

    fixed = MockProvider(chunks=["chunk-1", "chunk-2", "chunk-3"])
    _patch_get_provider(monkeypatch, fixed)

    out = []
    async for c in svc.analyze_stream(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        user_id=user.id,
        requirement_text="加个登录功能",
        level=AnalysisLevel.L2,
    ):
        out.append(c)
    assert out == ["chunk-1", "chunk-2", "chunk-3"]


async def test_analyze_stream_wraps_provider_timeout(
    db_session, svc, make_project, make_node, monkeypatch
):
    user, proj = await _make_proj_with_member(make_project, db_session)
    node = await make_node(proj.id, name="N1")
    await _set_project_ai(db_session, proj, provider="mock")

    scripted = _ScriptedProvider(
        chunks=["partial"], raise_exc=ProviderTimeoutError("scripted", 5.0)
    )
    _patch_get_provider(monkeypatch, scripted)

    seen = []
    with pytest.raises(AnalysisTimeoutError):
        async for c in svc.analyze_stream(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            user_id=user.id,
            requirement_text="...",
            level=AnalysisLevel.L1,
        ):
            seen.append(c)
    assert seen == ["partial"]


async def test_analyze_stream_wraps_rate_limited_to_quota_exceeded(
    db_session, svc, make_project, make_node, monkeypatch
):
    user, proj = await _make_proj_with_member(make_project, db_session)
    node = await make_node(proj.id, name="N1")
    await _set_project_ai(db_session, proj, provider="mock")

    scripted = _ScriptedProvider(chunks=["a"], raise_exc=ProviderError("scripted", "rate_limited"))
    _patch_get_provider(monkeypatch, scripted)

    with pytest.raises(AnalysisQuotaExceededError):
        async for _ in svc.analyze_stream(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            user_id=user.id,
            requirement_text="...",
            level=AnalysisLevel.L1,
        ):
            pass


async def test_analyze_stream_wraps_other_provider_error(
    db_session, svc, make_project, make_node, monkeypatch
):
    user, proj = await _make_proj_with_member(make_project, db_session)
    node = await make_node(proj.id, name="N1")
    await _set_project_ai(db_session, proj, provider="mock")

    scripted = _ScriptedProvider(
        chunks=[], raise_exc=ProviderError("scripted", "upstream_error_500")
    )
    _patch_get_provider(monkeypatch, scripted)

    with pytest.raises(AnalysisProviderError):
        async for _ in svc.analyze_stream(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            user_id=user.id,
            requirement_text="...",
            level=AnalysisLevel.L1,
        ):
            pass


# ─────────────── analyze_stream — tenant + node 防御 ───────────────


async def test_analyze_stream_blocks_cross_tenant_project(
    db_session, svc, make_project, make_node, monkeypatch
):
    """跨 user 访问 project → ProjectNotFoundError（M02 范式）。"""
    userA, projA = await _make_proj_with_member(make_project, db_session, name_suffix="-A")
    userB, _projB = await _make_proj_with_member(make_project, db_session, name_suffix="-B")
    # userB 不是 projA 成员
    node = await make_node(projA.id, name="N1")
    await _set_project_ai(db_session, projA, provider="mock")

    _patch_get_provider(monkeypatch, MockProvider())

    with pytest.raises(ProjectNotFoundError):
        async for _ in svc.analyze_stream(
            db_session,
            project_id=projA.id,
            node_id=node.id,
            user_id=userB.id,
            requirement_text="...",
            level=AnalysisLevel.L1,
        ):
            pass


async def test_analyze_stream_blocks_cross_project_node(
    db_session, svc, make_project, make_node, monkeypatch
):
    """node 不在传入 project 下 → AnalysisNodeNotFoundError 404（design §13）。"""
    user, projA = await _make_proj_with_member(make_project, db_session, name_suffix="-A")
    _, projB = await _make_proj_with_member(make_project, db_session, owner=user, name_suffix="-B")
    node_b = await make_node(projB.id, name="NB")
    await _set_project_ai(db_session, projA, provider="mock")

    _patch_get_provider(monkeypatch, MockProvider())

    with pytest.raises(AnalysisNodeNotFoundError):
        async for _ in svc.analyze_stream(
            db_session,
            project_id=projA.id,
            node_id=node_b.id,
            user_id=user.id,
            requirement_text="...",
            level=AnalysisLevel.L1,
        ):
            pass


# ─────────────── analyze_stream — prompt 上下文聚合 ───────────────


class _PromptCapturingProvider(LLMProvider):
    def __init__(self):
        self.captured_prompt: str | None = None
        self.captured_context: str | None = None

    @property
    def provider_name(self) -> str:
        return "capture"

    async def analyze(self, prompt: str, context: str = "") -> AsyncIterator[str]:
        self.captured_prompt = prompt
        self.captured_context = context
        yield "ok"


async def test_analyze_stream_includes_subtree_and_issues_in_prompt_context(
    db_session, svc, make_project, make_node, make_issue, monkeypatch
):
    user, proj = await _make_proj_with_member(make_project, db_session)
    root = await make_node(proj.id, name="root-feature")
    child1 = await make_node(proj.id, name="子节点-A", parent=root)
    await make_node(proj.id, name="孙节点-A1", parent=child1)  # 2 层深
    await make_node(proj.id, name="不相关节点")  # 不在 subtree

    await make_issue(
        user=user, project=proj, node=root, title="登录失败概率", category="bug", status="open"
    )

    await _set_project_ai(db_session, proj, provider="mock")

    capture = _PromptCapturingProvider()
    _patch_get_provider(monkeypatch, capture)

    out = []
    async for c in svc.analyze_stream(
        db_session,
        project_id=proj.id,
        node_id=root.id,
        user_id=user.id,
        requirement_text="支持微信扫码登录",
        level=AnalysisLevel.L3,
    ):
        out.append(c)

    assert out == ["ok"]
    assert capture.captured_context is not None
    # subtree 包含子+孙
    assert "子节点-A" in capture.captured_context
    assert "孙节点-A1" in capture.captured_context
    # 不相关节点不在
    assert "不相关节点" not in capture.captured_context
    # issue 注入
    assert "登录失败概率" in capture.captured_context
    # L3 指令前缀
    assert capture.captured_prompt is not None
    assert "L3" in capture.captured_prompt
    assert "支持微信扫码登录" in capture.captured_prompt


# ─────────────── save_analysis ───────────────


async def test_save_analysis_persists_record_and_metadata(db_session, svc, make_project, make_node):
    user, proj = await _make_proj_with_member(make_project, db_session)
    node = await make_node(proj.id, name="N1")

    aff_ids = [uuid4(), uuid4()]
    rec = await svc.save_analysis(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        user_id=user.id,
        analysis_result="**核心场景**：...",
        requirement_text="加个微信登录",
        level=AnalysisLevel.L2,
        ai_provider="claude",
        ai_model="claude-sonnet-4-5",
        analysis_time_ms=12345,
        affected_node_ids=aff_ids,
    )
    assert rec.id is not None
    assert rec.content["analysis_level"] == "L2"
    assert rec.content["analysis_result"] == "**核心场景**：..."
    assert set(rec.content["affected_node_ids"]) == {str(x) for x in aff_ids}


async def test_save_analysis_blocks_cross_project_node(db_session, svc, make_project, make_node):
    user, projA = await _make_proj_with_member(make_project, db_session, name_suffix="-A")
    _, projB = await _make_proj_with_member(make_project, db_session, owner=user, name_suffix="-B")
    nB = await make_node(projB.id, name="NB")

    with pytest.raises(AnalysisNodeNotFoundError):
        await svc.save_analysis(
            db_session,
            project_id=projA.id,
            node_id=nB.id,
            user_id=user.id,
            analysis_result="...",
            requirement_text="x",
            level=AnalysisLevel.L1,
            ai_provider="mock",
            ai_model="m",
            analysis_time_ms=1,
        )


async def test_save_analysis_wraps_underlying_failure_to_save_failed_error(
    db_session, svc, make_project, make_node, monkeypatch
):
    """M04 create_dimension_record 抛非 NodeNotFound → AnalysisSaveFailedError."""
    user, proj = await _make_proj_with_member(make_project, db_session)
    node = await make_node(proj.id, name="N1")

    async def boom(*args, **kwargs):
        raise RuntimeError("downstream burst")

    monkeypatch.setattr(svc.dimensions, "create_dimension_record", boom)

    with pytest.raises(AnalysisSaveFailedError) as ei:
        await svc.save_analysis(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            user_id=user.id,
            analysis_result="r",
            requirement_text="t",
            level=AnalysisLevel.L1,
            ai_provider="mock",
            ai_model="m",
            analysis_time_ms=1,
        )
    assert isinstance(ei.value.__cause__, RuntimeError)


async def test_save_analysis_blocks_cross_tenant_project(db_session, svc, make_project, make_node):
    """跨 user 访问 project → ProjectNotFoundError；写入路径同样防越权（M02 范式）。"""
    _userA, projA = await _make_proj_with_member(make_project, db_session, name_suffix="-A")
    userB, _projB = await _make_proj_with_member(make_project, db_session, name_suffix="-B")
    nA = await make_node(projA.id, name="NA")

    with pytest.raises(ProjectNotFoundError):
        await svc.save_analysis(
            db_session,
            project_id=projA.id,
            node_id=nA.id,
            user_id=userB.id,
            analysis_result="r",
            requirement_text="t",
            level=AnalysisLevel.L1,
            ai_provider="mock",
            ai_model="m",
            analysis_time_ms=1,
        )


# ─────────────── get_affected_nodes ───────────────


async def test_get_affected_nodes_returns_empty_when_no_history(
    db_session, svc, make_project, make_node
):
    user, proj = await _make_proj_with_member(make_project, db_session)
    node = await make_node(proj.id, name="N1")

    res = await svc.get_affected_nodes(
        db_session, project_id=proj.id, node_id=node.id, user_id=user.id
    )
    assert res.node_id == node.id
    assert res.affected_node_ids == []
    assert res.analysis_record_id is None
    assert res.analysis_saved_at is None


async def test_get_affected_nodes_returns_latest_record(db_session, svc, make_project, make_node):
    user, proj = await _make_proj_with_member(make_project, db_session)
    node = await make_node(proj.id, name="N1")
    aff = [uuid4(), uuid4(), uuid4()]
    rec = await svc.save_analysis(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        user_id=user.id,
        analysis_result="r",
        requirement_text="t",
        level=AnalysisLevel.L2,
        ai_provider="mock",
        ai_model="m",
        analysis_time_ms=42,
        affected_node_ids=aff,
    )

    res = await svc.get_affected_nodes(
        db_session, project_id=proj.id, node_id=node.id, user_id=user.id
    )
    assert res.analysis_record_id == rec.id
    assert set(res.affected_node_ids) == set(aff)
    assert res.analysis_saved_at is not None


async def test_get_affected_nodes_blocks_cross_tenant(db_session, svc, make_project, make_node):
    _, projA = await _make_proj_with_member(make_project, db_session, name_suffix="-A")
    userB, _ = await _make_proj_with_member(make_project, db_session, name_suffix="-B")
    nA = await make_node(projA.id, name="NA")
    with pytest.raises(ProjectNotFoundError):
        await svc.get_affected_nodes(
            db_session, project_id=projA.id, node_id=nA.id, user_id=userB.id
        )


async def test_get_affected_nodes_404_on_cross_project_node(
    db_session, svc, make_project, make_node
):
    user, projA = await _make_proj_with_member(make_project, db_session, name_suffix="-A")
    _, projB = await _make_proj_with_member(make_project, db_session, owner=user, name_suffix="-B")
    nB = await make_node(projB.id, name="NB")
    with pytest.raises(AnalysisNodeNotFoundError):
        await svc.get_affected_nodes(
            db_session, project_id=projA.id, node_id=nB.id, user_id=user.id
        )


# ─────────────── REQUIREMENT_ANALYSIS_KEY 常量 ───────────────


async def test_requirement_analysis_key_constant():
    """design line 175-177 字面：dimension_type_key='requirement_analysis'。"""
    assert REQUIREMENT_ANALYSIS_KEY == "requirement_analysis"


# ─────────────── write_event 异常传播（M04+ 元教训）───────────────


async def test_save_analysis_propagates_write_event_failure_via_save_failed(
    db_session, svc, make_project, make_node, monkeypatch
):
    """M04 内部 write_event 异常 → M04 抛 → M13 wrap AnalysisSaveFailedError（不吞错）。

    M04+ 元教训应用：write_event 异常传播测试覆盖；本场景 monkeypatch
    DimensionService 内部的 write_event 走 fault path，验异常向上传播 + wrap 形态。
    """
    user, proj = await _make_proj_with_member(make_project, db_session)
    node = await make_node(proj.id, name="N1")

    async def fake_write_event(**kwargs):
        raise RuntimeError("activity_log structlog crashed")

    monkeypatch.setattr("api.services.dimension_service.write_event", fake_write_event)

    with pytest.raises(AnalysisSaveFailedError) as ei:
        await svc.save_analysis(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            user_id=user.id,
            analysis_result="r",
            requirement_text="t",
            level=AnalysisLevel.L1,
            ai_provider="mock",
            ai_model="m",
            analysis_time_ms=1,
        )
    assert isinstance(ei.value.__cause__, RuntimeError)
