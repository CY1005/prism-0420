"""LLM Provider 抽象 (ADR-001 §4.1 / M13 design §12 字段⑥)。

LLMProvider.analyze 返回 AsyncIterator[str]（文本 chunk 流式 yield）。
AsyncIterator 必须支持 PEP 533 ``aclose()`` 协议——M13 SSE endpoint 在
``Request.is_disconnected()`` 检测到客户端断开时调用 ``await stream.aclose()``
释放底层流资源（HTTP 连接 / token 浪费截止）。

约定：
  - 子类 ``analyze`` 用 ``async def ... yield ...`` async generator 写法，
    Python 自动支持 PEP 533 aclose（GeneratorExit 抛入 yield 点 → finally 段
    清理 ``async with`` 上下文）。
  - MockProvider 额外暴露 ``aclose_called: bool`` 公共属性供测试断言（design §12
    字段⑥ 显式要求"必须实现可断言的 aclose_called 标志"）。
  - 真 SDK provider（ClaudeProvider 等）不暴露 aclose_called——其 aclose
    协议正确性由 integration smoke 端到端验证（见 tests/integration/）。

异常约定（service 层 wrap 见 M13 §13 R13-2）：
  - ProviderConfigError(provider="...", reason="missing_api_key" | ...) — 配置
    错误（→ M13 wrap AnalysisProviderNotConfiguredError 422）
  - ProviderTimeoutError(provider, timeout_seconds) — 流式超时（→ M13 wrap
    AnalysisTimeoutError 504）
  - ProviderError(provider, reason) — 网络/5xx/quota 等瞬时（→ M13 wrap
    AnalysisProviderError 503）
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class ProviderError(Exception):
    """Provider 调用瞬时失败（网络 / 5xx / SDK 抛错）。"""

    def __init__(self, provider: str, reason: str) -> None:
        self.provider = provider
        self.reason = reason
        super().__init__(f"provider={provider} failed: {reason}")


class ProviderTimeoutError(ProviderError):
    """Provider 流式超时（asyncio.timeout 触发或下游 httpx 超时）。"""

    def __init__(self, provider: str, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        # 不调 ProviderError.__init__ 让 reason 同时简洁
        Exception.__init__(self, f"provider={provider} timed out after {timeout_seconds}s")
        self.provider = provider
        self.reason = f"timeout_{timeout_seconds}s"


class ProviderConfigError(ProviderError):
    """Provider 配置错误（key 缺失 / 模型未知 / 参数非法）。"""

    def __init__(self, provider: str, reason: str) -> None:
        super().__init__(provider, reason)


class LLMProvider(ABC):
    """LLM provider 抽象 (ADR-001 §4.1)。

    M13 SSE endpoint 消费协议：
        provider = get_provider(name, api_key, model)
        stream = provider.analyze(prompt, context)
        try:
            async for chunk in stream:
                yield SSEChunkEvent(text=chunk)
                if await request.is_disconnected():
                    break
        finally:
            await stream.aclose()  # PEP 533 释放底层资源
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider 标识符，对齐 projects.ai_provider 字段值（'claude' / 'mock' / ...）。"""
        ...

    @abstractmethod
    async def analyze(self, prompt: str, context: str = "") -> AsyncIterator[str]:
        """流式 yield 文本 chunk。

        子类实现以 ``async def ... yield ...`` 形式，自动支持 PEP 533 aclose。
        失败抛 ProviderError 子类（ProviderConfigError / ProviderTimeoutError）。
        """
        if False:  # pragma: no cover — make abstract method an async generator
            yield ""
