"""M17 AIOrchestrationService 单元测试（无 DB 依赖）。

覆盖：
- run_step1 / run_step2：mock provider + JSON parse
- consolidate_step3：纯逻辑去重 + skipped 节点过滤
- _parse_json：missing key / non-JSON 抛 ImportAIProviderError
- _collect：rate_limited → ImportQuotaExceededError；timeout → ImportAIProviderError
- build_provider_from_project：缺 ai_provider → ImportAIProviderError
"""

from __future__ import annotations

import pytest

from api.errors.exceptions import ImportAIProviderError, ImportQuotaExceededError
from api.services.ai.provider import (
    LLMProvider,
    ProviderError,
    ProviderTimeoutError,
)
from api.services.ai_orchestration_service import AIOrchestrationService

pytestmark = pytest.mark.asyncio(loop_scope="session")


class _FakeProvider(LLMProvider):
    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks
        self._exc: Exception | None = None

    @property
    def provider_name(self) -> str:
        return "fake"

    async def analyze(self, prompt, context=""):
        for c in self._chunks:
            if self._exc is not None:
                raise self._exc
            yield c


class _FailingProvider(LLMProvider):
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    @property
    def provider_name(self) -> str:
        return "fake"

    async def analyze(self, prompt, context=""):
        if False:  # pragma: no cover
            yield ""
        raise self._exc


class TestStep1:
    async def test_returns_parsed_nodes(self):
        provider = _FakeProvider(['{"nodes": [', '{"proposed_id": "abc", "name": "X"}', "]}"])
        svc = AIOrchestrationService()
        out = await svc.run_step1(provider=provider, items_summary=[])
        assert "nodes" in out
        assert out["nodes"][0]["name"] == "X"

    async def test_missing_key_raises_provider_error(self):
        provider = _FakeProvider(['{"foo": []}'])
        svc = AIOrchestrationService()
        with pytest.raises(ImportAIProviderError) as exc:
            await svc.run_step1(provider=provider, items_summary=[])
        assert exc.value.details.get("missing_key") == "nodes"

    async def test_non_json_raises_provider_error(self):
        provider = _FakeProvider(["not json at all"])
        svc = AIOrchestrationService()
        with pytest.raises(ImportAIProviderError):
            await svc.run_step1(provider=provider, items_summary=[])


class TestStep2:
    async def test_returns_3_keys(self):
        provider = _FakeProvider(['{"dimensions": [], "competitors": [], "issues": []}'])
        svc = AIOrchestrationService()
        out = await svc.run_step2(provider=provider, proposed_nodes=[], items_summary=[])
        assert "dimensions" in out
        assert "competitors" in out
        assert "issues" in out

    async def test_missing_competitors_key_raises(self):
        provider = _FakeProvider(['{"dimensions": [], "issues": []}'])
        svc = AIOrchestrationService()
        with pytest.raises(ImportAIProviderError):
            await svc.run_step2(provider=provider, proposed_nodes=[], items_summary=[])


class TestProviderErrorMapping:
    async def test_rate_limited_maps_to_quota_exceeded(self):
        provider = _FailingProvider(ProviderError("claude", "rate_limited"))
        svc = AIOrchestrationService()
        with pytest.raises(ImportQuotaExceededError):
            await svc.run_step1(provider=provider, items_summary=[])

    async def test_provider_timeout_maps_to_ai_provider_error(self):
        provider = _FailingProvider(ProviderTimeoutError("claude", 30.0))
        svc = AIOrchestrationService()
        with pytest.raises(ImportAIProviderError) as exc:
            await svc.run_step1(provider=provider, items_summary=[])
        assert "timeout" in str(exc.value.message).lower() or "timeout" in str(exc.value.details)

    async def test_provider_5xx_maps_to_ai_provider_error(self):
        provider = _FailingProvider(ProviderError("claude", "http_503"))
        svc = AIOrchestrationService()
        with pytest.raises(ImportAIProviderError):
            await svc.run_step1(provider=provider, items_summary=[])


class TestConsolidateStep3:
    def test_dedup_dimensions_by_node_and_key(self):
        out = AIOrchestrationService.consolidate_step3(
            {
                "nodes": [{"proposed_id": "n1", "name": "a"}],
                "dimensions": [
                    {
                        "proposed_id": "d1",
                        "target_proposed_node_id": "n1",
                        "dimension_type_key": "k1",
                        "content": {"v": 1},
                    },
                    {
                        "proposed_id": "d2",
                        "target_proposed_node_id": "n1",
                        "dimension_type_key": "k1",  # 同 (node, key) 重复
                        "content": {"v": 2},
                    },
                    {
                        "proposed_id": "d3",
                        "target_proposed_node_id": "n1",
                        "dimension_type_key": "k2",
                        "content": {"v": 3},
                    },
                ],
                "competitors": [],
                "issues": [],
            }
        )
        assert len(out["dimensions"]) == 2
        # 保留首条
        assert out["dimensions"][0]["content"]["v"] == 1

    def test_skipped_nodes_filter_dimensions_and_issues(self):
        out = AIOrchestrationService.consolidate_step3(
            {
                "nodes": [
                    {"proposed_id": "n1", "name": "a", "skipped": True},
                    {"proposed_id": "n2", "name": "b"},
                ],
                "dimensions": [
                    {
                        "proposed_id": "d1",
                        "target_proposed_node_id": "n1",  # n1 skipped
                        "dimension_type_key": "k",
                        "content": {},
                    },
                    {
                        "proposed_id": "d2",
                        "target_proposed_node_id": "n2",
                        "dimension_type_key": "k",
                        "content": {},
                    },
                ],
                "competitors": [],
                "issues": [
                    {
                        "proposed_id": "i1",
                        "target_proposed_node_id": "n1",  # n1 skipped
                        "title": "x",
                        "category": "bug",
                        "description": "",
                    },
                    {
                        "proposed_id": "i2",
                        "target_proposed_node_id": "n2",
                        "title": "y",
                        "category": "bug",
                        "description": "",
                    },
                ],
            }
        )
        # nodes：去 skipped
        assert len(out["nodes"]) == 1
        assert out["nodes"][0]["proposed_id"] == "n2"
        # dimensions: only n2
        assert len(out["dimensions"]) == 1
        assert out["dimensions"][0]["target_proposed_node_id"] == "n2"
        # issues: only n2
        assert len(out["issues"]) == 1

    def test_competitors_dedup_by_display_name(self):
        out = AIOrchestrationService.consolidate_step3(
            {
                "nodes": [],
                "dimensions": [],
                "competitors": [
                    {"proposed_id": "c1", "display_name": "AppX"},
                    {"proposed_id": "c2", "display_name": "appx  "},  # 大小写 / 空格
                    {"proposed_id": "c3", "display_name": "AppY"},
                ],
                "issues": [],
            }
        )
        assert len(out["competitors"]) == 2

    def test_skip_proposed_ids_top_level(self):
        out = AIOrchestrationService.consolidate_step3(
            {
                "nodes": [{"proposed_id": "n1", "name": "a"}],
                "dimensions": [
                    {
                        "proposed_id": "d1",
                        "target_proposed_node_id": "n1",
                        "dimension_type_key": "k",
                        "content": {},
                    }
                ],
                "competitors": [],
                "issues": [],
                "skip_proposed_ids": ["n1"],
            }
        )
        # n1 在 skip_proposed_ids 内 → dimensions 应被过滤
        assert len(out["dimensions"]) == 0


class TestBuildProvider:
    def test_missing_ai_provider_raises_provider_error(self):
        class _Proj:
            ai_provider = None
            ai_api_key_enc = None
            ai_model = None

        with pytest.raises(ImportAIProviderError):
            AIOrchestrationService.build_provider_from_project(_Proj())

    def test_mock_provider_does_not_need_api_key(self):
        class _Proj:
            ai_provider = "mock"
            ai_api_key_enc = None
            ai_model = None

        provider = AIOrchestrationService.build_provider_from_project(_Proj())
        assert provider.provider_name == "mock"
