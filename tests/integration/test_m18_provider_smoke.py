"""M18 provider integration smoke test（@skipif OPENAI_API_KEY）。

仿 M13 ClaudeProvider integration smoke 范式。
当前 OpenAI / bge embed_single 仍是 NotImplementedError（子片 4+ 真做）。
"""

from __future__ import annotations

import os

import pytest

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


@pytest.mark.skipif(not OPENAI_API_KEY, reason="OPENAI_API_KEY not set")
async def test_openai_embed_single_smoke():
    """OpenAI 真调 smoke test（仅当 OPENAI_API_KEY 设置时跑）。

    当前占位：embed_single 仍 NotImplementedError（子片 4+ 接通后去掉 skipif）。
    """
    from api.services.embedding_provider import OpenAIEmbeddingProvider

    provider = OpenAIEmbeddingProvider(
        api_key=OPENAI_API_KEY,
        model_name="text-embedding-3-small",
        dim=1536,
    )
    # 子片 3：embed_single 仍 NotImplementedError（pgvector 装后真做）
    with pytest.raises(NotImplementedError):
        await provider.embed_single("hello world")


async def test_openai_provider_attributes():
    """OpenAIEmbeddingProvider 属性正常（不调 API）。"""
    from api.services.embedding_provider import OpenAIEmbeddingProvider

    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        model_name="text-embedding-3-small",
        dim=1536,
    )
    assert provider.provider_name == "openai"
    assert provider.model_name == "text-embedding-3-small"
    assert provider.dim == 1536


async def test_bge_provider_attributes():
    """BgeEmbeddingProvider 属性正常（不调模型）。"""
    from api.services.embedding_provider import BgeEmbeddingProvider

    provider = BgeEmbeddingProvider(model_name="bge-small-zh-v1.5", dim=512)
    assert provider.provider_name == "bge"
    assert provider.model_name == "bge-small-zh-v1.5"
    assert provider.dim == 512


async def test_bge_embed_single_raises_not_implemented():
    """BGE embed_single 子片 4+ 之前仍 NotImplementedError。"""
    from api.services.embedding_provider import BgeEmbeddingProvider

    provider = BgeEmbeddingProvider()
    with pytest.raises(NotImplementedError):
        await provider.embed_single("test")


async def test_openai_embed_single_raises_not_implemented():
    """OpenAI embed_single 子片 4+ 之前仍 NotImplementedError。"""
    from api.services.embedding_provider import OpenAIEmbeddingProvider

    provider = OpenAIEmbeddingProvider(api_key="fake")
    with pytest.raises(NotImplementedError):
        await provider.embed_single("test")
