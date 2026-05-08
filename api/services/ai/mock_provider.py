"""MockProvider — 测试 / 开发用 stub provider。

design §12 字段⑥ 显式要求：MockProvider 必须实现可断言的 ``aclose_called: bool`` 标志。
M13 router e2e + AnalyzeService unit 测试均依赖此标志验证 PEP 533 aclose 协议触发。
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from api.services.ai.provider import LLMProvider, ProviderError


class MockProvider(LLMProvider):
    """流式 yield 预设 chunks 的 mock。

    Args:
        chunks: 预设输出 chunk 列表，默认 5 段日文+中文混合短句模拟真流式。
        raise_after: 如果 ≥0，在 yield 第 N 个 chunk 后抛 ProviderError（模拟瞬时失败）。
        chunk_delay: 每 chunk 之间 ``await asyncio.sleep(...)``（模拟流式延迟，默认 0）。

    Attributes:
        aclose_called: ``analyze`` 返回的 generator 触发 PEP 533 aclose 时设为 True；
            generator 自然完成（迭代到末尾）**不**会设此标志为 True，仅 ``aclose()``
            或 GeneratorExit 才会。测试断言此标志验证 SSE 端点 cancel 路径真停。
    """

    def __init__(
        self,
        chunks: list[str] | None = None,
        raise_after: int = -1,
        chunk_delay: float = 0.0,
    ) -> None:
        self._chunks = (
            chunks
            if chunks is not None
            else [
                "需求分析：",
                "本节点的核心场景是",
                "用户在主流程中触发",
                "建议拆分为 3 个子任务",
                "（END）",
            ]
        )
        self._raise_after = raise_after
        self._chunk_delay = chunk_delay
        self.aclose_called = False

    @property
    def provider_name(self) -> str:
        return "mock"

    async def analyze(self, prompt: str, context: str = "") -> AsyncIterator[str]:
        import asyncio  # 局部 import 避免顶层引入

        try:
            for i, chunk in enumerate(self._chunks):
                if self._raise_after >= 0 and i >= self._raise_after:
                    raise ProviderError("mock", f"simulated_failure_at_chunk_{i}")
                if self._chunk_delay > 0:
                    await asyncio.sleep(self._chunk_delay)
                yield chunk
        except GeneratorExit:
            # PEP 533: caller 调 stream.aclose() 时 Python 抛 GeneratorExit 进
            # async generator；此分支即"被显式取消"——区别于 yield 完所有 chunk
            # 的自然完成路径（自然完成不进此分支，aclose_called 保持 False）。
            self.aclose_called = True
            raise
