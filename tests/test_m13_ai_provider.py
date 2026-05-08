"""M13 子片 1 — AI Provider 抽象 + MockProvider + ClaudeProvider + Registry 单元测试。

范围：
  - MockProvider 流式 yield + aclose_called PEP 533 协议断言
  - ClaudeProvider httpx 流式（monkeypatch httpx.AsyncClient 模拟 anthropic SSE）
  - ProviderRegistry get 工厂 + 错误分支

monkeypatch ≠ 生产路径（feedback_monkeypatch_not_verification）：
  本文件全 unit；ClaudeProvider 真 SDK 集成走 tests/integration/test_m13_provider_smoke.py
  + @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'))。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import pytest

from api.services.ai import (
    ClaudeProvider,
    LLMProvider,
    MockProvider,
    ProviderConfigError,
    ProviderError,
    ProviderTimeoutError,
    get_provider,
)

# ─────────────── MockProvider ───────────────


async def test_mock_yields_default_chunks_in_order():
    p = MockProvider()
    out = [c async for c in p.analyze("test prompt")]
    assert len(out) == 5
    assert out[0] == "需求分析："
    assert out[-1] == "（END）"


async def test_mock_yields_custom_chunks():
    p = MockProvider(chunks=["a", "b", "c"])
    out = [c async for c in p.analyze("ignore")]
    assert out == ["a", "b", "c"]


async def test_mock_natural_completion_does_not_set_aclose_called():
    """自然完成（迭代到末尾）不应触发 aclose_called（PEP 533 语义区分）。"""
    p = MockProvider(chunks=["x", "y"])
    async for _ in p.analyze("p"):
        pass
    assert p.aclose_called is False


async def test_mock_aclose_called_set_when_caller_aborts():
    """显式 aclose() → GeneratorExit → finally → aclose_called=True（M13 cancel 路径核心）。"""
    p = MockProvider(chunks=["a", "b", "c", "d", "e"])
    stream = p.analyze("p")
    # 拿前两个 chunk 后主动 aclose
    chunks_seen: list[str] = []
    async for c in stream:
        chunks_seen.append(c)
        if len(chunks_seen) == 2:
            break
    await stream.aclose()
    assert p.aclose_called is True
    assert chunks_seen == ["a", "b"]


async def test_mock_raise_after_emits_provider_error_mid_stream():
    p = MockProvider(chunks=["a", "b", "c", "d"], raise_after=2)
    seen: list[str] = []
    with pytest.raises(ProviderError) as ei:
        async for c in p.analyze("p"):
            seen.append(c)
    assert seen == ["a", "b"]
    assert "simulated_failure_at_chunk_2" in str(ei.value)


async def test_mock_provider_name_is_mock():
    p = MockProvider()
    assert p.provider_name == "mock"
    assert isinstance(p, LLMProvider)


# ─────────────── ClaudeProvider (monkeypatch httpx) ───────────────


class _FakeResp:
    def __init__(self, status_code: int, lines: list[str]) -> None:
        self.status_code = status_code
        self._lines = lines

    async def aiter_lines(self):  # noqa: ANN201 — match httpx.Response signature
        for line in self._lines:
            yield line


class _FakeStreamCM:
    """模拟 ``async with client.stream(...) as resp`` 上下文。"""

    def __init__(self, resp: _FakeResp) -> None:
        self._resp = resp

    async def __aenter__(self):  # noqa: ANN204
        return self._resp

    async def __aexit__(self, *exc):  # noqa: ANN204
        return False


class _FakeAsyncClient:
    """模拟 ``async with httpx.AsyncClient(...) as client`` 上下文。

    每个测试通过 fake_httpx fixture 预设 class-level ``next_status`` + ``next_lines``，
    所有 new instance 共享当前测试的响应配置（避免 lambda __init__ 重写 hack）。
    """

    next_status: int = 200
    next_lines: list[str] = []
    instances: list[_FakeAsyncClient] = []

    def __init__(self, *args, **kwargs) -> None:
        self.timeout = kwargs.get("timeout")
        self.calls: list[dict] = []
        _FakeAsyncClient.instances.append(self)

    def stream(self, method, url, **kwargs):  # noqa: ANN201
        self.calls.append({"method": method, "url": url, **kwargs})
        return _FakeStreamCM(_FakeResp(_FakeAsyncClient.next_status, _FakeAsyncClient.next_lines))

    async def __aenter__(self):  # noqa: ANN204
        return self

    async def __aexit__(self, *exc):  # noqa: ANN204
        return False


def _anthropic_sse(text_chunks: list[str]) -> list[str]:
    """构造 anthropic 风格 SSE data: 行序列。"""
    out = []
    for t in text_chunks:
        ev = {"type": "content_block_delta", "delta": {"type": "text_delta", "text": t}}
        out.append(f"data: {json.dumps(ev)}")
    out.append("data: [DONE]")
    return out


@pytest.fixture
def fake_httpx(monkeypatch):
    _FakeAsyncClient.instances.clear()
    _FakeAsyncClient.next_status = 200
    _FakeAsyncClient.next_lines = []
    monkeypatch.setattr("api.services.ai.claude_provider.httpx.AsyncClient", _FakeAsyncClient)
    return _FakeAsyncClient


async def test_claude_streams_anthropic_deltas(fake_httpx):
    fake_httpx.next_lines = _anthropic_sse(["Hello, ", "world", "!"])
    p = ClaudeProvider(api_key="sk-test", model="claude-sonnet-4-5")
    out = [c async for c in p.analyze("test", context="ctx")]
    assert out == ["Hello, ", "world", "!"]


async def test_claude_skips_non_data_lines_and_other_events(fake_httpx):
    fake_httpx.next_lines = [
        "event: message_start",  # 非 data: 行，跳过
        'data: {"type": "message_start"}',  # 非 content_block_delta，跳过
        'data: {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "ok"}}',
        "data: not-json-skip",  # JSONDecodeError 跳过
        'data: {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "done"}}',
        "data: [DONE]",
    ]
    p = ClaudeProvider(api_key="sk-test")
    out = [c async for c in p.analyze("p")]
    assert out == ["ok", "done"]


async def test_claude_skips_non_text_delta_types(fake_httpx):
    """R1-A P1-3 立修验证：anthropic content_block_delta 下 delta.type 多种
    （text_delta / input_json_delta / thinking_delta / signature_delta），
    只 yield text_delta；防 thinking_delta 文本污染输出（design §12 字段③）。"""
    fake_httpx.next_lines = [
        'data: {"type": "content_block_delta", "delta": {"type": "thinking_delta", "thinking": "let me think..."}}',
        'data: {"type": "content_block_delta", "delta": {"type": "input_json_delta", "partial_json": "{\\"a\\":"}}',
        'data: {"type": "content_block_delta", "delta": {"type": "signature_delta", "signature": "abc"}}',
        'data: {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "real output"}}',
        "data: [DONE]",
    ]
    p = ClaudeProvider(api_key="sk-test")
    out = [c async for c in p.analyze("p")]
    # 只应拿到 text_delta；thinking/json/signature 三类全 skip
    assert out == ["real output"]


async def test_claude_401_maps_to_provider_config_error(fake_httpx):
    fake_httpx.next_status = 401
    p = ClaudeProvider(api_key="bad-key")
    with pytest.raises(ProviderConfigError) as ei:
        async for _ in p.analyze("p"):
            pass
    assert "auth_failed_401" in ei.value.reason


async def test_claude_429_maps_to_provider_error_rate_limited(fake_httpx):
    fake_httpx.next_status = 429
    p = ClaudeProvider(api_key="sk-test")
    with pytest.raises(ProviderError) as ei:
        async for _ in p.analyze("p"):
            pass
    assert ei.value.reason == "rate_limited"
    assert not isinstance(ei.value, ProviderConfigError)


async def test_claude_500_maps_to_provider_error_upstream(fake_httpx):
    fake_httpx.next_status = 500
    p = ClaudeProvider(api_key="sk-test")
    with pytest.raises(ProviderError) as ei:
        async for _ in p.analyze("p"):
            pass
    assert "upstream_error_500" in ei.value.reason


async def test_claude_timeout_maps_to_provider_timeout_error(monkeypatch):
    import httpx

    def raising_client(*args, **kwargs):
        class _C:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            def stream(self, *a, **kw):
                raise httpx.TimeoutException("simulated timeout")

        return _C()

    monkeypatch.setattr("api.services.ai.claude_provider.httpx.AsyncClient", raising_client)

    p = ClaudeProvider(api_key="sk-test", timeout_seconds=2.0)
    with pytest.raises(ProviderTimeoutError) as ei:
        async for _ in p.analyze("p"):
            pass
    assert ei.value.timeout_seconds == 2.0
    assert ei.value.provider == "claude"


async def test_claude_missing_api_key_at_init_raises_provider_config_error():
    with pytest.raises(ProviderConfigError) as ei:
        ClaudeProvider(api_key="")
    assert ei.value.reason == "missing_api_key"


async def test_claude_aclose_releases_via_async_with(fake_httpx):
    """主动 aclose() async generator 应让 async with httpx 正常退出（无异常泄漏）。

    本测试验证 PEP 533 协议在 ClaudeProvider 上的"协议接通"——真实底层资源
    释放靠 async with 自动展开，integration smoke 端到端再验。
    """
    fake_httpx.next_lines = _anthropic_sse(["a", "b", "c", "d", "e"])
    p = ClaudeProvider(api_key="sk-test")
    stream: AsyncIterator[str] = p.analyze("p")
    seen: list[str] = []
    async for chunk in stream:
        seen.append(chunk)
        if len(seen) == 2:
            break
    # 应能正常 aclose 不抛
    await stream.aclose()
    assert seen == ["a", "b"]


# ─────────────── Registry ───────────────


async def test_registry_default_returns_mock_provider():
    p = get_provider(None)
    assert isinstance(p, MockProvider)
    p2 = get_provider("")
    assert isinstance(p2, MockProvider)
    p3 = get_provider("mock")
    assert isinstance(p3, MockProvider)


async def test_registry_claude_requires_api_key():
    with pytest.raises(ProviderConfigError) as ei:
        get_provider("claude", api_key=None)
    assert ei.value.reason == "missing_api_key"
    with pytest.raises(ProviderConfigError):
        get_provider("claude", api_key="")


async def test_registry_claude_returns_claude_provider_with_model():
    p = get_provider("claude", api_key="sk-test", model="claude-opus-4-7")
    assert isinstance(p, ClaudeProvider)
    assert p._model == "claude-opus-4-7"
    assert p.provider_name == "claude"


async def test_registry_unknown_provider_raises():
    with pytest.raises(ProviderConfigError) as ei:
        get_provider("gpt-9000", api_key="x")
    assert ei.value.provider == "gpt-9000"
    assert ei.value.reason == "unknown_provider"


async def test_registry_case_insensitive_and_strips():
    p = get_provider("  CLAUDE  ", api_key="sk-test")
    assert isinstance(p, ClaudeProvider)
