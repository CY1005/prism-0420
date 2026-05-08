"""M13 真 SDK provider integration smoke。

CY 拍板（2026-05-08）：本 sprint 真 SDK 实装范围 = Mock + Claude；本文件验
ClaudeProvider 真 anthropic httpx stream 端到端可用 + PEP 533 aclose 协议正确。

CI 默认跳过（无 ANTHROPIC_API_KEY）；本机手动 export 后跑：
    export ANTHROPIC_API_KEY=sk-ant-...
    uv run pytest tests/integration/test_m13_provider_smoke.py -v -s

feedback_monkeypatch_not_verification 触发：unit 测试用 fake httpx 验协议形态，
真 SDK 验证靠本文件——sprint DONE 必须区分 unit pass 和 integration pass，
未跑过本文件则 sprint 状态标 NEEDS_CONTEXT 而非 DONE。
"""

from __future__ import annotations

import os

import pytest

from api.services.ai import ClaudeProvider, ProviderError

_REAL_KEY = os.getenv("ANTHROPIC_API_KEY")

pytestmark = pytest.mark.skipif(
    not _REAL_KEY,
    reason="ANTHROPIC_API_KEY not set — integration smoke skipped (unit suite covers协议形态)",
)


async def test_claude_real_sdk_streams_at_least_one_chunk():
    """真 anthropic API 跑一个极短 prompt，断言至少 1 chunk yield。"""
    p = ClaudeProvider(api_key=_REAL_KEY, model="claude-haiku-4-5-20251001")
    chunks: list[str] = []
    async for c in p.analyze("Say hi in exactly one word."):
        chunks.append(c)
        if len(chunks) >= 1:
            # 拿到 ≥1 chunk 即满足 smoke；继续迭代验完整路径不抛
            pass
    assert len(chunks) >= 1
    full = "".join(chunks)
    assert len(full) > 0


async def test_claude_real_sdk_aclose_releases_resources_mid_stream():
    """真 anthropic API：拿前 2 chunk 后 aclose；不抛异常 = 资源释放路径接通。"""
    p = ClaudeProvider(api_key=_REAL_KEY, model="claude-haiku-4-5-20251001")
    stream = p.analyze("Count slowly from 1 to 20, one number per line.")
    seen: list[str] = []
    async for c in stream:
        seen.append(c)
        if len(seen) >= 2:
            break
    # 主动 aclose；底层 httpx async with 应自动展开释放 HTTP 连接
    await stream.aclose()
    assert len(seen) >= 1


async def test_claude_real_sdk_bad_key_maps_to_provider_error():
    """配置 sk-ant-INVALID_KEY 真打 anthropic，验 401/403 wrap 路径。"""
    p = ClaudeProvider(api_key="sk-ant-deliberately-invalid-12345")
    with pytest.raises(ProviderError):
        async for _ in p.analyze("hi"):
            pass
