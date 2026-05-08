"""ClaudeProvider — Anthropic Messages API httpx 流式 (ADR-001 §4.1)。

不引入 ``anthropic`` 库依赖（避免 SDK 升级耦合）；直用 ``httpx.AsyncClient.stream``
消费 Anthropic 官方 SSE 协议（``data: {...}`` 行 / ``content_block_delta`` 事件）。

PEP 533 aclose 协议：
  - 本类 ``analyze`` 是 async generator，``async with httpx.AsyncClient(...)`` +
    ``async with client.stream(...)`` 嵌套上下文确保 caller 调 ``aclose()`` 触发
    GeneratorExit 时自动展开 ``async with`` 释放底层 HTTP 连接。
  - 测试 fixture 用 monkeypatch ``httpx.AsyncClient`` 替换为 fake stream（unit 路径）；
    integration smoke 走真 ANTHROPIC_API_KEY 端到端验证 aclose 行为
    （见 tests/integration/test_m13_provider_smoke.py + skipif）。

参考：design/02-modules/M13-requirement-analysis/00-design.md §12 字段①-⑥
异常映射（M13 §13 R13-2）：
  - 401/403 → ProviderConfigError(reason="auth_failed")
  - 429 → ProviderError(reason="rate_limited") — M13 wrap AnalysisQuotaExceededError 429
  - 5xx / 网络错 → ProviderError(reason="upstream_error")
  - httpx.TimeoutException → ProviderTimeoutError
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from api.services.ai.provider import (
    LLMProvider,
    ProviderConfigError,
    ProviderError,
    ProviderTimeoutError,
)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-4-5"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT_SECONDS = 120.0


class ClaudeProvider(LLMProvider):
    """Anthropic Messages API 流式 provider。

    Args:
        api_key: ANTHROPIC_API_KEY（明文；caller 已 AES 解密，见 M02 crypto.decrypt）
        model: Anthropic 模型 ID，默认 ``claude-sonnet-4-5``
        max_tokens: 单次 stream 最大 token 数，默认 4096
        timeout_seconds: httpx client 总超时（含连接 + 读），默认 120s；
            注意 M13 服务器层另有 ``asyncio.timeout(300)`` 包住 ``async for chunk``
            循环，本字段是 httpx 单连接超时（design §12 字段⑤）
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if not api_key:
            raise ProviderConfigError("claude", "missing_api_key")
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "claude"

    async def analyze(self, prompt: str, context: str = "") -> AsyncIterator[str]:
        messages = [
            {
                "role": "user",
                "content": f"{context}\n\n{prompt}" if context else prompt,
            }
        ]
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        payload = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "stream": True,
            "messages": messages,
        }

        try:
            async with (
                httpx.AsyncClient(timeout=self._timeout_seconds) as client,
                client.stream("POST", ANTHROPIC_API_URL, headers=headers, json=payload) as resp,
            ):
                self._raise_for_status(resp)
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    if event.get("type") != "content_block_delta":
                        continue
                    delta = event.get("delta", {})
                    # R1-A P1-3 立修：anthropic 同名事件下 delta 有多种 type
                    # （text_delta / input_json_delta / thinking_delta / signature_delta）。
                    # 只 yield text_delta；防 thinking_delta 文本污染输出（design §12 字段③）。
                    if delta.get("type") != "text_delta":
                        continue
                    text = delta.get("text", "")
                    if text:
                        yield text
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError("claude", self._timeout_seconds) from e
        except httpx.RequestError as e:
            # R1-C P1-02 立修：删 `except httpx.HTTPStatusError: raise` 死代码
            # （_raise_for_status 抛 ProviderError 子类，httpx.HTTPStatusError 此路径不会触发）。
            # httpx.RequestError 是基类，覆盖 NetworkError / ConnectError / ProxyError 等
            # （httpx.NetworkError 是 RequestError 的子类，单一捕获已足）。
            raise ProviderError("claude", f"network_error: {type(e).__name__}") from e

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        """非 2xx 抛 Provider* — 区分配置错（401/403）/ 限流（429）/ 上游错（5xx）。"""
        sc = resp.status_code
        if sc < 400:
            return
        if sc in (401, 403):
            raise ProviderConfigError("claude", f"auth_failed_{sc}")
        if sc == 429:
            raise ProviderError("claude", "rate_limited")
        if 400 <= sc < 500:
            raise ProviderError("claude", f"client_error_{sc}")
        raise ProviderError("claude", f"upstream_error_{sc}")
