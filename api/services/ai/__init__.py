"""M13 AI Provider 体系 (ADR-001 §4.1)。

抽象 + 实现 + 工厂：
  - provider.LLMProvider — ABC（analyze 流式 + PEP 533 aclose 协议）
  - mock_provider.MockProvider — 测试用，含 aclose_called: bool 可断言标志
  - claude_provider.ClaudeProvider — Anthropic Messages API httpx 流式
  - registry.get_provider — 工厂，按 (provider_name, api_key, model) 分发

设计依据：
  - ADR-001 §4.1（AI Provider stream() 接口 + aclose 协议约定）
  - design/02-modules/M13-requirement-analysis/00-design.md §12 字段⑥
  - feedback_monkeypatch_not_verification（DONE 区分 unit pass vs integration pass）
"""

from api.services.ai.claude_provider import ClaudeProvider
from api.services.ai.mock_provider import MockProvider
from api.services.ai.provider import (
    LLMProvider,
    ProviderConfigError,
    ProviderError,
    ProviderTimeoutError,
)
from api.services.ai.registry import get_provider

__all__ = [
    "ClaudeProvider",
    "LLMProvider",
    "MockProvider",
    "ProviderConfigError",
    "ProviderError",
    "ProviderTimeoutError",
    "get_provider",
]
