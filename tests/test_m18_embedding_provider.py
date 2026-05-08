"""M18 子片 0 prep — EmbeddingProvider 抽象 + MockEmbeddingProvider + factory 单元测试。

范围：
  - MockEmbeddingProvider 确定性 hash 向量 + L2 归一化
  - mock-* 前缀强制（fix v4.2 R2=A）
  - dim 档位 {512, 1536, 3072} 强制（fix v3 决策 1=D）
  - factory 未知 provider / openai-bge 子片 3 NotImplemented 分支
  - 抽象基类不能直接实例化

OpenAI / bge 真 SDK 集成留子片 3 落地（参 M13 ClaudeProvider integration smoke 范式）。
"""

from __future__ import annotations

import math

import pytest

from api.services.embedding_provider import (
    MOCK_MODEL_NAME_PREFIX,
    SUPPORTED_DIMS,
    SUPPORTED_PROVIDERS,
    BgeEmbeddingProvider,
    EmbeddingProvider,
    EmbeddingProviderConfigError,
    EmbeddingProviderError,
    EmbeddingProviderTimeoutError,
    MockEmbeddingProvider,
    OpenAIEmbeddingProvider,
    get_embedding_provider,
)

# ─────────────── 抽象基类 ───────────────


def test_abstract_provider_cannot_instantiate():
    with pytest.raises(TypeError):
        EmbeddingProvider()  # type: ignore[abstract]


# ─────────────── MockEmbeddingProvider ───────────────


def test_mock_default_dim_1536_and_provider_name_mock():
    p = MockEmbeddingProvider()
    assert p.provider_name == "mock"
    assert p.model_name == "mock-default"
    assert p.dim == 1536


@pytest.mark.parametrize("dim", [512, 1536, 3072])
def test_mock_supports_all_three_dims(dim: int):
    p = MockEmbeddingProvider(dim=dim)
    assert p.dim == dim


@pytest.mark.parametrize("bad_dim", [0, 100, 768, 1024, 4096])
def test_mock_rejects_unsupported_dim(bad_dim: int):
    with pytest.raises(EmbeddingProviderConfigError) as exc:
        MockEmbeddingProvider(dim=bad_dim)
    assert "dim_must_be_in" in exc.value.reason


@pytest.mark.parametrize("bad_name", ["default", "openai-mock", "MOCK-x", "", "test-mock"])
def test_mock_rejects_non_mock_prefix_model_name(bad_name: str):
    with pytest.raises(EmbeddingProviderConfigError) as exc:
        MockEmbeddingProvider(model_name=bad_name)
    assert "mock_model_name_must_start_with" in exc.value.reason


def test_mock_accepts_mock_prefix_variants():
    for name in ("mock-default", "mock-test", "mock-x-y-z"):
        p = MockEmbeddingProvider(model_name=name)
        assert p.model_name == name


async def test_mock_embed_single_returns_list_with_correct_dim():
    p = MockEmbeddingProvider(dim=512)
    vec = await p.embed_single("hello world")
    assert isinstance(vec, list)
    assert len(vec) == 512
    assert all(isinstance(x, float) for x in vec)


async def test_mock_embed_single_deterministic():
    """同 text 同 dim 必返完全一致向量（content_hash 兜底测试可断言）。"""
    p = MockEmbeddingProvider(dim=1536)
    v1 = await p.embed_single("identical text")
    v2 = await p.embed_single("identical text")
    assert v1 == v2


async def test_mock_embed_single_different_texts_differ():
    p = MockEmbeddingProvider(dim=512)
    v1 = await p.embed_single("text a")
    v2 = await p.embed_single("text b")
    assert v1 != v2


async def test_mock_embed_single_l2_normalized():
    """pgvector cosine_ops 期望已归一化向量。"""
    p = MockEmbeddingProvider(dim=1536)
    vec = await p.embed_single("normalize me")
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-6


async def test_mock_embed_batch_returns_n_vectors():
    p = MockEmbeddingProvider(dim=512)
    texts = ["a", "b", "c", "d", "e"]
    vecs = await p.embed_batch(texts)
    assert len(vecs) == 5
    assert all(len(v) == 512 for v in vecs)


async def test_mock_embed_batch_each_deterministic_and_matches_single():
    p = MockEmbeddingProvider(dim=512)
    single_a = await p.embed_single("a")
    single_b = await p.embed_single("b")
    batch = await p.embed_batch(["a", "b"])
    assert batch[0] == single_a
    assert batch[1] == single_b


async def test_mock_embed_batch_empty_input():
    p = MockEmbeddingProvider()
    vecs = await p.embed_batch([])
    assert vecs == []


# ─────────────── 工厂 get_embedding_provider ───────────────


def test_factory_default_returns_mock():
    p = get_embedding_provider(provider_name=None)
    assert isinstance(p, MockEmbeddingProvider)
    assert p.provider_name == "mock"


def test_factory_empty_string_returns_mock():
    p = get_embedding_provider(provider_name="")
    assert isinstance(p, MockEmbeddingProvider)


def test_factory_mock_uses_provided_model_name_and_dim():
    p = get_embedding_provider(provider_name="mock", model_name="mock-test", dim=512)
    assert p.model_name == "mock-test"
    assert p.dim == 512


def test_factory_mock_default_model_name():
    p = get_embedding_provider(provider_name="mock")
    assert p.model_name == "mock-default"
    assert p.dim == 1536


def test_factory_mock_rejects_non_mock_prefix():
    with pytest.raises(EmbeddingProviderConfigError):
        get_embedding_provider(provider_name="mock", model_name="text-embedding-3-small")


@pytest.mark.parametrize("provider", ["openai", "bge"])
async def test_factory_openai_and_bge_not_yet_implemented_subpiece_3(provider: str):
    """子片 3 更新：factory 返回 provider 实例（不再 ConfigError），
    但 embed_single / embed_batch 调用时抛 NotImplementedError（pgvector 装后真做）。"""

    import os

    with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
        os.environ, {"OPENAI_API_KEY": "test-key"}
    ):
        p = get_embedding_provider(provider_name=provider)
    # 工厂返回实例（不再 ConfigError）
    if provider == "openai":
        assert isinstance(p, OpenAIEmbeddingProvider)
    else:
        assert isinstance(p, BgeEmbeddingProvider)
    # embed_single 仍是 NotImplementedError（子片 4+ 真做）
    with pytest.raises(NotImplementedError):
        await p.embed_single("test")


@pytest.mark.parametrize("bad", ["unknown", "anthropic", "cohere", "azure"])
def test_factory_unknown_provider_raises(bad: str):
    with pytest.raises(EmbeddingProviderConfigError) as exc:
        get_embedding_provider(provider_name=bad)
    assert "unknown_provider" in exc.value.reason


def test_factory_case_insensitive_normalization():
    p = get_embedding_provider(provider_name="MOCK")
    assert p.provider_name == "mock"


# ─────────────── 异常族 ───────────────


def test_provider_error_hierarchy():
    """ProviderTimeoutError + ConfigError 都继承 ProviderError（caller try/except 单点）。"""
    assert issubclass(EmbeddingProviderTimeoutError, EmbeddingProviderError)
    assert issubclass(EmbeddingProviderConfigError, EmbeddingProviderError)


def test_provider_error_carries_provider_and_reason():
    err = EmbeddingProviderError("openai", "rate_limit")
    assert err.provider == "openai"
    assert err.reason == "rate_limit"
    assert "openai" in str(err)
    assert "rate_limit" in str(err)


def test_timeout_error_carries_seconds():
    err = EmbeddingProviderTimeoutError("openai", 1.5)
    assert err.timeout_seconds == 1.5
    assert err.provider == "openai"
    assert "1.5s" in str(err)


# ─────────────── 模块级常量 ───────────────


def test_supported_dims_constant():
    assert SUPPORTED_DIMS == (512, 1536, 3072)


def test_supported_providers_constant():
    assert set(SUPPORTED_PROVIDERS) == {"openai", "bge", "mock"}


def test_mock_prefix_constant():
    assert MOCK_MODEL_NAME_PREFIX == "mock-"
