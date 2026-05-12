"""EmbeddingProvider 抽象 (M18 §6 horizontal helper / 仿 ADR-001 §4.1 LLM provider 抽象).

design §6 line 579 字面：``EmbeddingProvider`` 基类 + OpenAI / bge / Mock 实现，仿
ADR-001 §4.1（详见 ``api/services/ai/provider.py`` LLMProvider）。

横切归属（design §6 line 579 + 2026-05-07 对齐原则 6 + R-X6）：
  - horizontal helper（embedding 提供者抽象 / M03 / M04 / M06 / M07 多模块 owner=M18 caller）
  - owner = M18
  - 位置在横切层 ``api/services/`` 与 ``api/services/ai/`` 同级（不属业务模块名下）

约束（M18 design §3 / fix v3 决策 1=D / fix v4.2 R2=A）：
  - dim ∈ {512, 1536, 3072} 三档，CHECK ``ck_embeddings_dim_range`` 字面对齐
  - provider ∈ {openai, bge, mock}，CHECK ``ck_embeddings_provider`` 字面对齐
  - mock provider 的 model_name 必须 ``mock-*`` 前缀（fix v4.2 R2=A startup sanity check）

子片 0 prep 范围（mini-sprint / 2026-05-09）：
  - EmbeddingProvider 抽象基类 + 异常族（仿 LLMProvider 三类）
  - MockEmbeddingProvider 确定性 hash 向量实现（测试 + 开发期 fallback）
  - get_embedding_provider 工厂（仅 mock 实装；openai/bge 留 子片 3 落地）

子片 3 范围（后续）：
  - OpenAIEmbeddingProvider（httpx 直连或 sdk）
  - BgeEmbeddingProvider（本地 sentence-transformers / bge-small-zh-v1.5）
  - 接通 EmbeddingService.embed_query / get_or_compute_embedding
"""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod

# Scaffold 简化决策（2026-05-09 / 子片 0 prep mini-sprint）
# ① 决策内容：EmbeddingProvider 抽象基类 + MockEmbeddingProvider + factory；
#    OpenAI/bge 真实现留子片 3，本子片仅落 abstract + Mock + factory + 单元测试
# ② 简化理由：openai sdk + bge 模型加载需要外部依赖（httpx + sentence-transformers）
#    + 真集成测试需要 API key / 模型文件，子片 0 prep 范围内不引入；先锁接口契约
# ③ 由 M18 sprint 子片 3 EmbeddingService 实装时扩齐到完整 OpenAI + bge 形态
# ④ 触发回写动作：子片 3 commit 加 OpenAIEmbeddingProvider / BgeEmbeddingProvider
#    类 + factory 内 if name == 'openai' / 'bge' 分支 + integration smoke skipif 测试

# 维度档位常量（design §3 ck_embeddings_dim_range 字面 / fix v3 决策 1=D）
SUPPORTED_DIMS: tuple[int, ...] = (512, 1536, 3072)

# Provider 名常量（design §3 ck_embeddings_provider 字面）
SUPPORTED_PROVIDERS: tuple[str, ...] = ("openai", "bge", "mock")

# Mock 前缀约束（fix v4.2 R2=A startup sanity check 字面）
MOCK_MODEL_NAME_PREFIX: str = "mock-"


class EmbeddingProviderError(Exception):
    """Embedding provider 调用瞬时失败（网络 / 5xx / SDK 抛错 / 维度不匹配）。"""

    def __init__(self, provider: str, reason: str) -> None:
        self.provider = provider
        self.reason = reason
        super().__init__(f"embedding_provider={provider} failed: {reason}")


class EmbeddingProviderTimeoutError(EmbeddingProviderError):
    """Embedding provider 超时（query embed > QUERY_EMBEDDING_TIMEOUT_MS / batch > BACKFILL_BATCH_TIMEOUT_S）。"""

    def __init__(self, provider: str, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        Exception.__init__(
            self, f"embedding_provider={provider} timed out after {timeout_seconds}s"
        )
        self.provider = provider
        self.reason = f"timeout_{timeout_seconds}s"


class EmbeddingProviderConfigError(EmbeddingProviderError):
    """Embedding provider 配置错误（key 缺失 / 模型未知 / dim 档位非法 / mock 前缀违反）。"""

    def __init__(self, provider: str, reason: str) -> None:
        super().__init__(provider, reason)


class EmbeddingProvider(ABC):
    """Embedding provider 抽象 (M18 design §6 / 仿 ADR-001 §4.1 LLMProvider)。

    子类必须：
      - 实现 ``provider_name`` / ``model_name`` / ``dim`` 三个属性（部署期固定）
      - 实现 ``embed_single`` 单文本 embed（query path 用）
      - 实现 ``embed_batch`` 批量 embed（backfill path 用）

    调用协议（M18 EmbeddingService 消费）：
        provider = get_embedding_provider(name='mock', model_name='mock-default', dim=1536)
        vec = await provider.embed_single("query text")  # → list[float] len == provider.dim
        vecs = await provider.embed_batch(["a", "b"])    # → list[list[float]] 各 len == provider.dim
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """对齐 embeddings.provider 字段值（'openai' / 'bge' / 'mock'）。"""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """对齐 embeddings.model_name 字段值（'text-embedding-3-small' / 'mock-default' 等）。"""
        ...

    @property
    @abstractmethod
    def dim(self) -> int:
        """向量维度，必须 ∈ SUPPORTED_DIMS = {512, 1536, 3072}。"""
        ...

    @abstractmethod
    async def embed_single(self, text: str) -> list[float]:
        """单文本 embed（query path）。返回长度必须 == dim。"""
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量 embed（backfill path）。返回 len(texts) 个向量，各长度 == dim。"""
        ...


class MockEmbeddingProvider(EmbeddingProvider):
    """确定性 hash 向量实现，用于测试 / 开发期 fallback。

    Args:
        model_name: 必须 ``mock-*`` 前缀（fix v4.2 R2=A 强制约束）。默认 ``mock-default``。
        dim: 向量维度，必须 ∈ SUPPORTED_DIMS。默认 1536（与 OpenAI text-embedding-3-small 同档）。

    确定性算法：sha256(text).digest() → 用作 PRNG seed → 生成 dim 维 [-1, 1] 浮点向量
    然后 L2 归一化（pgvector cosine_ops 期望已归一化）。
    """

    def __init__(self, model_name: str = "mock-default", dim: int = 1536) -> None:
        if not model_name.startswith(MOCK_MODEL_NAME_PREFIX):
            raise EmbeddingProviderConfigError(
                "mock",
                f"mock_model_name_must_start_with_{MOCK_MODEL_NAME_PREFIX!r}_got_{model_name!r}",
            )
        if dim not in SUPPORTED_DIMS:
            raise EmbeddingProviderConfigError(
                "mock",
                f"dim_must_be_in_{SUPPORTED_DIMS}_got_{dim}",
            )
        self._model_name = model_name
        self._dim = dim

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dim(self) -> int:
        return self._dim

    async def embed_single(self, text: str) -> list[float]:
        return _deterministic_vector(text, self._dim)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [_deterministic_vector(t, self._dim) for t in texts]


def _deterministic_vector(text: str, dim: int) -> list[float]:
    """sha256-seeded 浮点向量，L2 归一化。

    同 text + 同 dim 必返完全一致向量（content_hash 兜底测试可断言）。
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    # 把 32-byte digest 拉成 dim 长度的 [-1, 1] 浮点序列
    raw: list[float] = []
    for i in range(dim):
        # 复用 digest 字节 + 位置扰动，保证不同位置不同值
        b = digest[i % 32]
        raw.append((b / 127.5) - 1.0 + (i % 7) * 1e-4)
    # L2 归一化（pgvector cosine_ops 期望）
    norm = math.sqrt(sum(x * x for x in raw))
    if norm == 0.0:
        # 退化场景：极小概率（hash 全 0），返回单位向量
        return [1.0 / math.sqrt(dim)] * dim
    return [x / norm for x in raw]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider skeleton（子片 3 范围）。

    embed_single / embed_batch 暂 raise NotImplementedError（子片 4+ pgvector 装后真做）。
    provider_name / model_name / dim 属性正常——工厂、schema、配置 sanity check 可用。

    子片 4+ 集成 TODO：
      - httpx 直连 api.openai.com/v1/embeddings 或 openai SDK
      - 超时 = EMBEDDING_TASK_TIMEOUT_S（single）/ BACKFILL_BATCH_TIMEOUT_S（batch）
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "text-embedding-3-small",
        dim: int = 1536,
    ) -> None:
        if dim not in SUPPORTED_DIMS:
            raise EmbeddingProviderConfigError(
                "openai",
                f"dim_must_be_in_{SUPPORTED_DIMS}_got_{dim}",
            )
        self._api_key = api_key
        self._model_name = model_name
        self._dim = dim

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dim(self) -> int:
        return self._dim

    async def embed_single(self, text: str) -> list[float]:
        raise NotImplementedError("OpenAI integration TODO 子片 4+ / pgvector 装后真做")

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("OpenAI integration TODO 子片 4+ / pgvector 装后真做")


class BgeEmbeddingProvider(EmbeddingProvider):
    """BGE (BAAI General Embedding) provider skeleton（子片 3 范围）。

    embed_single / embed_batch 暂 raise NotImplementedError（子片 4+ 真做）。
    provider_name / model_name / dim 属性正常。

    子片 4+ 集成 TODO：
      - sentence-transformers 加载 BAAI/bge-small-zh-v1.5 本地模型
      - 支持 CPU / GPU 推理
    """

    def __init__(
        self,
        model_name: str = "bge-small-zh-v1.5",
        dim: int = 512,
    ) -> None:
        if dim not in SUPPORTED_DIMS:
            raise EmbeddingProviderConfigError(
                "bge",
                f"dim_must_be_in_{SUPPORTED_DIMS}_got_{dim}",
            )
        self._model_name = model_name
        self._dim = dim

    @property
    def provider_name(self) -> str:
        return "bge"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dim(self) -> int:
        return self._dim

    async def embed_single(self, text: str) -> list[float]:
        raise NotImplementedError("BGE integration TODO 子片 4+ / pgvector 装后真做")

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("BGE integration TODO 子片 4+ / pgvector 装后真做")


def get_embedding_provider(
    provider_name: str | None,
    model_name: str | None = None,
    dim: int | None = None,
    api_key: str | None = None,
) -> EmbeddingProvider:
    """工厂：按 provider_name 字段值返回对应 EmbeddingProvider 实例。

    Args:
        provider_name: ∈ SUPPORTED_PROVIDERS = {'openai', 'bge', 'mock'}；None / "" → 'mock'
        model_name: 模型名（mock 必须 ``mock-*`` 前缀；openai 'text-embedding-3-small' 等）
        dim: 向量维度，必须 ∈ SUPPORTED_DIMS
        api_key: OpenAI api_key（默认从 env `OPENAI_API_KEY` 读 / 部署期 secrets manager 或 env 注入；
                 caller 可显式传入 override（用于测试 / 未来多租户演进）；范式差异参 ADR-006 §Consequences）

    Raises:
        EmbeddingProviderConfigError: 未知 provider / mock 前缀违反 / dim 档位非法

    子片 0 prep（2026-05-09）：实装 ``mock``。
    子片 3（2026-05-09）：OpenAI + bge skeleton（embed_single/batch 暂 NotImplementedError）。
    子片 4+：pgvector 装后接通 OpenAI + bge 真实现。

    api_key 范式（F9 决策 2026-05-12 / CY 拍方案 A 接受 env-only）：
        - M18 (embedding) = 基础设施级 / 全局 OPENAI_API_KEY env / 与 ADR-001 §4 "embedding provider 部署期固定" 自洽
        - M13 (LLM analysis) = 业务级 / ProjectSettings.ai_api_key_enc + AES decrypt / 每 project 独立 key
        - 范式差异是显式决策（基础设施 vs 业务功能不同语义），非 drift
        - 未来若需多租户 SaaS / per-project embedding key → 升级方案 B (ProjectSettings.embedding_api_key_enc + alembic 迁移 + admin UI)
    """
    name = (provider_name or "mock").strip().lower()

    if name not in SUPPORTED_PROVIDERS:
        raise EmbeddingProviderConfigError(
            name, f"unknown_provider_must_be_in_{SUPPORTED_PROVIDERS}"
        )

    if name == "mock":
        return MockEmbeddingProvider(
            model_name=model_name or "mock-default",
            dim=dim if dim is not None else 1536,
        )

    if name == "openai":
        import os

        # F9 决策（2026-05-12 / CY 拍方案 A）：M18 = 基础设施级 env-only / 与 ADR-001 §4 自洽
        # caller 可显式传 api_key override (用于测试 / 多租户演进)，否则 env OPENAI_API_KEY
        resolved_api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        return OpenAIEmbeddingProvider(
            api_key=resolved_api_key,
            model_name=model_name or "text-embedding-3-small",
            dim=dim if dim is not None else 1536,
        )

    if name == "bge":
        return BgeEmbeddingProvider(
            model_name=model_name or "bge-small-zh-v1.5",
            dim=dim if dim is not None else 512,
        )

    # 不可达（above branches exhaustive over SUPPORTED_PROVIDERS）
    raise EmbeddingProviderConfigError(name, "unreachable_branch")  # pragma: no cover
