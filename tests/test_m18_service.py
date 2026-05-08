"""M18 EmbeddingService + SearchService 单元测试（30+）。

使用 AsyncMock + MagicMock 替换 DAO / provider / db 依赖。
不需要真实 DB。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from api.errors.exceptions import (
    EmbeddingDeleteFailedError,
    EmbeddingProviderFailedError,
    EmbeddingTargetNotFoundError,
    SilentFailure,
)
from api.schemas.embedding_schema import EmbedSinglePayload
from api.schemas.search_schema import EmbeddingTargetType, SearchResponse
from api.services.embedding import EmbeddingBackfillService, EmbeddingService
from api.services.embedding_provider import MockEmbeddingProvider
from api.services.search import SearchService, _rrf_merge

# ─── helpers ────────────────────────────────────────────────────────────────


def _mock_db():
    """返回 AsyncMock db session。"""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


def _make_payload(**kwargs):
    defaults = dict(
        user_id=uuid4(),
        project_id=uuid4(),
        target_type=EmbeddingTargetType.NODE,
        target_id=uuid4(),
        provider="mock",
        model_name="mock-default",
        model_version="v1",
        enqueued_by="incremental",
    )
    defaults.update(kwargs)
    return EmbedSinglePayload(**defaults)


# ─── EmbeddingService.enqueue ────────────────────────────────────────────────


async def test_enqueue_creates_task_and_sets_debounce():
    mock_task_dao = AsyncMock()
    mock_task_dao.create = AsyncMock(return_value=MagicMock())
    provider = MockEmbeddingProvider()

    svc = EmbeddingService(
        embedding_task_dao=mock_task_dao,
        provider=provider,
    )
    db = _mock_db()
    project_id = uuid4()
    target_id = uuid4()

    await svc.enqueue(db, project_id, "node", target_id, enqueued_by="incremental")
    mock_task_dao.create.assert_called_once()
    call_kwargs = mock_task_dao.create.call_args.kwargs
    assert call_kwargs["project_id"] == project_id
    assert call_kwargs["target_type"] == "node"
    assert call_kwargs["target_id"] == target_id
    assert call_kwargs["enqueued_by"] == "incremental"


async def test_enqueue_debounce_skips_duplicate():
    """同 key 60s 内第二次 enqueue 应跳过（debounce）。"""
    import time

    from api.services.embedding import _DEBOUNCE_CACHE, _debounce_key

    mock_task_dao = AsyncMock()
    mock_task_dao.create = AsyncMock(return_value=MagicMock())
    provider = MockEmbeddingProvider()
    svc = EmbeddingService(embedding_task_dao=mock_task_dao, provider=provider)
    db = _mock_db()
    pid = uuid4()
    tid = uuid4()

    # 手动预设 debounce cache
    key = _debounce_key(pid, "node", tid)
    _DEBOUNCE_CACHE[key] = time.monotonic()

    await svc.enqueue(db, pid, "node", tid)
    # 应该不调 create（已 debounce）
    mock_task_dao.create.assert_not_called()

    # 清理
    _DEBOUNCE_CACHE.pop(key, None)


# ─── EmbeddingService.enqueue_delete ─────────────────────────────────────────


async def test_enqueue_delete_calls_dao():
    mock_embedding_dao = AsyncMock()
    mock_embedding_dao.delete_by_target = AsyncMock(return_value=1)
    svc = EmbeddingService(embedding_dao=mock_embedding_dao)
    db = _mock_db()
    pid = uuid4()
    tid = uuid4()

    await svc.enqueue_delete(db, pid, "node", tid)
    mock_embedding_dao.delete_by_target.assert_called_once()


async def test_enqueue_delete_raises_silent_failure_on_dao_error():
    mock_embedding_dao = AsyncMock()
    mock_embedding_dao.delete_by_target = AsyncMock(side_effect=RuntimeError("DB down"))
    svc = EmbeddingService(embedding_dao=mock_embedding_dao)
    db = _mock_db()

    with pytest.raises(EmbeddingDeleteFailedError):
        await svc.enqueue_delete(db, uuid4(), "node", uuid4())


async def test_enqueue_delete_error_is_silent_failure():
    """EmbeddingDeleteFailedError 是 SilentFailure — 验证类型层次。"""
    from api.errors.exceptions import EmbeddingDeleteFailedError

    mock_embedding_dao = AsyncMock()
    mock_embedding_dao.delete_by_target = AsyncMock(side_effect=RuntimeError("err"))
    svc = EmbeddingService(embedding_dao=mock_embedding_dao)
    db = _mock_db()

    # 验证抛出的是 SilentFailure 子类（不是 Exception 子类）
    caught_as_silent_failure = False
    try:
        await svc.enqueue_delete(db, uuid4(), "node", uuid4())
    except SilentFailure:
        caught_as_silent_failure = True
    assert caught_as_silent_failure
    # SilentFailure 不是 Exception 子类
    assert not issubclass(EmbeddingDeleteFailedError, Exception)


# ─── EmbeddingService.embed_query ────────────────────────────────────────────


async def test_embed_query_returns_tuple():
    provider = MockEmbeddingProvider(dim=1536)
    svc = EmbeddingService(provider=provider)
    db = _mock_db()

    result = await svc.embed_query(db, "test query")
    vec, dim, prov_name, model_name, model_version = result
    assert len(vec) == 1536
    assert dim == 1536
    assert prov_name == "mock"
    assert model_name == "mock-default"


async def test_embed_query_cache_hit_returns_same_result():
    """同 query 第二次调用应命中内存 cache。"""

    provider = MockEmbeddingProvider(dim=512)
    svc = EmbeddingService(provider=provider)
    db = _mock_db()

    result1 = await svc.embed_query(db, "cached query abc")
    result2 = await svc.embed_query(db, "cached query abc")
    assert result1 == result2


async def test_embed_query_provider_error_raises_app_error():
    """provider.embed_single 失败 → EmbeddingProviderFailedError。"""
    from api.services.embedding_provider import (
        EmbeddingProviderError as ProviderError,
    )

    mock_provider = AsyncMock(spec=MockEmbeddingProvider)
    mock_provider.provider_name = "mock"
    mock_provider.model_name = "mock-default"
    mock_provider.dim = 1536
    mock_provider.embed_single = AsyncMock(side_effect=ProviderError("mock", "rate_limit"))

    svc = EmbeddingService(provider=mock_provider)
    db = _mock_db()

    with pytest.raises(EmbeddingProviderFailedError):
        await svc.embed_query(db, "fail query")


# ─── EmbeddingService.get_or_compute_embedding ───────────────────────────────


async def test_get_or_compute_skip_when_content_hash_matches():
    """content_hash 命中 → 不调 provider，直接返回已有 embedding。"""
    existing = MagicMock()
    existing.content_hash = "existing_hash"

    mock_embedding_dao = AsyncMock()
    mock_embedding_dao.find_by_target = AsyncMock(return_value=existing)

    provider = MockEmbeddingProvider()
    svc = EmbeddingService(embedding_dao=mock_embedding_dao, provider=provider)
    db = _mock_db()

    result = await svc.get_or_compute_embedding(
        db,
        project_id=uuid4(),
        target_type="node",
        target_id=uuid4(),
        provider="mock",
        model_name="mock-default",
        model_version="v1",
        content_hash="existing_hash",
        source_text="some text",
    )
    assert result is existing
    mock_embedding_dao.find_by_target.assert_called_once()


async def test_get_or_compute_calls_provider_when_no_existing():
    """没有已有 embedding → 调 provider.embed_single → upsert。"""
    mock_embedding_dao = AsyncMock()
    mock_embedding_dao.find_by_target = AsyncMock(return_value=None)
    new_embedding = MagicMock()
    mock_embedding_dao.upsert_embedding = AsyncMock(return_value=new_embedding)

    provider = MockEmbeddingProvider(dim=1536)
    svc = EmbeddingService(embedding_dao=mock_embedding_dao, provider=provider)
    db = _mock_db()

    result = await svc.get_or_compute_embedding(
        db,
        project_id=uuid4(),
        target_type="node",
        target_id=uuid4(),
        provider="mock",
        model_name="mock-default",
        model_version="v1",
        content_hash="new_hash",
        source_text="some text",
    )
    assert result is new_embedding
    mock_embedding_dao.upsert_embedding.assert_called_once()


# ─── EmbeddingService.batch_backfill ─────────────────────────────────────────


async def test_batch_backfill_returns_count():
    mock_task_dao = AsyncMock()
    mock_task_dao.create = AsyncMock(return_value=MagicMock())
    provider = MockEmbeddingProvider()
    svc = EmbeddingService(embedding_task_dao=mock_task_dao, provider=provider)
    db = _mock_db()

    ids = [uuid4() for _ in range(5)]
    count = await svc.batch_backfill(
        db,
        project_id=uuid4(),
        target_ids=ids,
        target_type="node",
        provider="mock",
        model_name="mock-default",
        model_version="v1",
    )
    assert count == 5


async def test_batch_backfill_empty_list():
    svc = EmbeddingService(provider=MockEmbeddingProvider())
    db = _mock_db()
    count = await svc.batch_backfill(
        db,
        project_id=uuid4(),
        target_ids=[],
        target_type="node",
        provider="mock",
        model_name="mock-default",
        model_version="v1",
    )
    assert count == 0


# ─── EmbeddingService.check_payload_consistency ──────────────────────────────


async def test_check_payload_consistency_target_not_found_raises():
    """EmbeddingTask 表无对应行 → EmbeddingTargetNotFoundError。"""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    svc = EmbeddingService()
    payload = _make_payload()

    with pytest.raises(EmbeddingTargetNotFoundError):
        await svc.check_payload_consistency(db, payload)


async def test_check_payload_consistency_passes_when_task_found():
    """EmbeddingTask 存在 → 不抛。"""
    mock_task = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_task)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    svc = EmbeddingService()
    payload = _make_payload()

    # 不抛即通过
    await svc.check_payload_consistency(db, payload)


# ─── EmbeddingBackfillService.detect_and_resume_pending_backfill ─────────────


async def test_detect_and_resume_no_stale_returns_zero():
    mock_task_dao = AsyncMock()
    mock_task_dao.find_pending_for_recovery = AsyncMock(return_value=[])
    svc = EmbeddingBackfillService(task_dao=mock_task_dao)
    db = _mock_db()
    arq_pool = AsyncMock()

    result = await svc.detect_and_resume_pending_backfill(db, arq_pool)
    assert result == 0


async def test_detect_and_resume_enqueues_stale_tasks():
    """有残留 task → re-enqueue。"""
    stale = MagicMock()
    stale.id = uuid4()
    stale.project_id = uuid4()
    stale.target_type = "node"
    stale.target_id = uuid4()
    stale.provider = "mock"
    stale.model_name = "mock-default"
    stale.model_version = "v1"

    mock_task_dao = AsyncMock()
    mock_task_dao.find_pending_for_recovery = AsyncMock(return_value=[stale])

    svc = EmbeddingBackfillService(task_dao=mock_task_dao)
    db = _mock_db()
    arq_pool = AsyncMock()
    arq_pool.enqueue_job = AsyncMock()

    result = await svc.detect_and_resume_pending_backfill(db, arq_pool)
    assert result == 1
    arq_pool.enqueue_job.assert_called_once()
    call_kwargs = arq_pool.enqueue_job.call_args
    assert call_kwargs[0][0] == "embed_single"
    # _job_id should be backfill_recovery:{task.id}
    assert f"backfill_recovery:{stale.id}" in call_kwargs[1].get("_job_id", "")


async def test_detect_and_resume_handles_enqueue_error():
    """enqueue 失败 → warn + skip，不抛（续处理下一条）。"""
    stale = MagicMock()
    stale.id = uuid4()
    stale.project_id = uuid4()
    stale.target_type = "node"
    stale.target_id = uuid4()
    stale.provider = "mock"
    stale.model_name = "mock-default"
    stale.model_version = "v1"

    mock_task_dao = AsyncMock()
    mock_task_dao.find_pending_for_recovery = AsyncMock(return_value=[stale])

    svc = EmbeddingBackfillService(task_dao=mock_task_dao)
    db = _mock_db()
    arq_pool = AsyncMock()
    arq_pool.enqueue_job = AsyncMock(side_effect=RuntimeError("redis down"))

    result = await svc.detect_and_resume_pending_backfill(db, arq_pool)
    # 抛了错但 service 内部 catch + warn，返回 resumed=0
    assert result == 0


# ─── SearchService ────────────────────────────────────────────────────────────


async def test_search_service_keyword_only_mode():
    """SEARCH_MODE=keyword_only → keyword path only，search_mode 返回 keyword_only。"""
    import api.services.search as search_mod

    svc = SearchService()
    db = _mock_db()

    # 通过 patch 模块级 _SEARCH_MODE 变量来控制搜索模式
    with patch.object(search_mod, "_SEARCH_MODE", "keyword_only"):
        resp = await svc.hybrid_search(
            db=db,
            query="test",
            project_id=uuid4(),
            user_id=uuid4(),
        )
    assert isinstance(resp, SearchResponse)
    # keyword_only 模式 + 无真实结果 = keyword_only
    assert resp.search_mode == "keyword_only"


async def test_search_service_semantic_fallback_on_pgvector_unavailable():
    """pgvector 不可用 → search_mode 降级为 keyword_only。"""
    mock_embedding_svc = AsyncMock()
    mock_embedding_svc.embed_query = AsyncMock(
        return_value=([0.1] * 1536, 1536, "mock", "mock-default", "v1")
    )

    svc = SearchService(embedding_service=mock_embedding_svc)
    db = _mock_db()

    # vector_search 抛 NotImplementedError（pgvector 未装）
    import api.services.search as sm

    with (
        patch("api.dao.embedding_dao.EmbeddingDAO.vector_search", side_effect=NotImplementedError),
        patch.object(svc, "_embedding_service", mock_embedding_svc),
        patch.object(sm, "_SEARCH_MODE", "hybrid"),
    ):
        resp = await svc.hybrid_search(
            db=db,
            query="test",
            project_id=uuid4(),
            user_id=uuid4(),
        )
    assert resp.search_mode == "keyword_only"


async def test_search_service_returns_search_response():
    svc = SearchService()
    db = _mock_db()

    with patch("api.services.search._SEARCH_MODE", "keyword_only"):
        resp = await svc.hybrid_search(
            db=db,
            query="test query",
            project_id=uuid4(),
            user_id=uuid4(),
        )
    assert isinstance(resp, SearchResponse)
    assert isinstance(resp.results, list)
    assert isinstance(resp.total, int)


# ─── RRF 融合 ────────────────────────────────────────────────────────────────


def test_rrf_merge_empty_both():
    result = _rrf_merge([], [])
    assert result == []


def test_rrf_merge_keyword_only():
    from api.schemas.search_schema import SearchResultItem

    items = [
        SearchResultItem(
            target_type=EmbeddingTargetType.NODE,
            target_id=uuid4(),
            title=f"Item {i}",
            snippet="",
            score=1.0 - i * 0.1,
            matched_by=["keyword"],
            breadcrumb=[],
        )
        for i in range(3)
    ]
    result = _rrf_merge(items, [])
    assert len(result) == 3


def test_rrf_merge_deduplicates_and_merges_matched_by():
    """同一 target_id 出现在 keyword + semantic 两路 → merged_by 合并。"""
    from api.schemas.search_schema import SearchResultItem

    tid = uuid4()
    keyword_item = SearchResultItem(
        target_type=EmbeddingTargetType.NODE,
        target_id=tid,
        title="Shared",
        snippet="",
        score=0.9,
        matched_by=["keyword"],
        breadcrumb=[],
    )
    semantic_item = SearchResultItem(
        target_type=EmbeddingTargetType.NODE,
        target_id=tid,
        title="Shared",
        snippet="",
        score=0.8,
        matched_by=["semantic"],
        breadcrumb=[],
    )
    result = _rrf_merge([keyword_item], [semantic_item])
    assert len(result) == 1
    assert set(result[0].matched_by) == {"keyword", "semantic"}


def test_rrf_merge_respects_limit():
    from api.schemas.search_schema import SearchResultItem

    items = [
        SearchResultItem(
            target_type=EmbeddingTargetType.NODE,
            target_id=uuid4(),
            title=f"Item {i}",
            snippet="",
            score=1.0,
            matched_by=["keyword"],
            breadcrumb=[],
        )
        for i in range(10)
    ]
    result = _rrf_merge(items, [], k=60, limit=5)
    assert len(result) == 5
