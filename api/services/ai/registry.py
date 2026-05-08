"""ProviderRegistry — 按 (provider_name, api_key, model) 工厂分发 LLMProvider 实例。

M13 AnalyzeService 调用：
    provider = get_provider(
        ai_provider=project.ai_provider,        # "claude" / "mock" / ...
        api_key=decrypt(project.ai_api_key_enc) if project.ai_api_key_enc else None,
        model=project.ai_model,
    )

子片 1 实装范围（CY 2026-05-08 拍）：仅 ``mock`` + ``claude``。
后续 sprint 顺手抄 prism 补 ``kimi`` / ``codex`` / ``deepseek``，时机参 M13 audit。
"""

from __future__ import annotations

from api.services.ai.claude_provider import DEFAULT_MODEL as CLAUDE_DEFAULT
from api.services.ai.claude_provider import ClaudeProvider
from api.services.ai.mock_provider import MockProvider
from api.services.ai.provider import LLMProvider, ProviderConfigError


def get_provider(
    ai_provider: str | None,
    api_key: str | None = None,
    model: str | None = None,
) -> LLMProvider:
    """工厂：按 ai_provider 字段值返回对应 Provider 实例。

    Args:
        ai_provider: projects.ai_provider 字段值；None / "" / "mock" 都走 MockProvider
            （M13 design line 720 约定：项目未配置 AI → wrap 为
            AnalysisProviderNotConfiguredError 422 引导用户去配置页；本工厂层不抛
            该错——by-design 把"未配置则走 mock"作为开发期 fallback。
            生产 caller AnalyzeService 在调用本工厂前应已校验 ai_provider 非空，
            未配置时走 422 错误响应）。
        api_key: 已 AES 解密的明文 api key；mock 不需要
        model: 模型 ID；None 则用 provider 默认

    Raises:
        ProviderConfigError: 未知 provider 名 / claude 缺 api_key
    """
    name = (ai_provider or "mock").strip().lower()

    if name == "mock":
        return MockProvider()

    if name == "claude":
        if not api_key:
            raise ProviderConfigError("claude", "missing_api_key")
        return ClaudeProvider(api_key=api_key, model=model or CLAUDE_DEFAULT)

    raise ProviderConfigError(name, "unknown_provider")
