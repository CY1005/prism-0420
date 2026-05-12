"""M18 Pydantic schema 校验测试（10+）。

范围：
- EmbeddingTargetType StrEnum 枚举
- SearchRequest min/max length + target_types + limit 校验
- SearchResultItem / SearchResponse 结构
- EmbedSinglePayload TaskPayload 继承 + 字段校验
- Admin schema（BackfillRequest / BackfillResponse 等）
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from api.schemas.embedding_schema import (
    BackfillRequest,
    EmbedSinglePayload,
    ModelUpgradeRequest,
)
from api.schemas.search_schema import (
    _EMBEDDING_TARGET_TYPES,
    EmbeddingTargetType,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)

# ─── EmbeddingTargetType ────────────────────────────────────────────────────


def test_embedding_target_type_values():
    assert EmbeddingTargetType.NODE == "node"
    assert EmbeddingTargetType.DIMENSION_RECORD == "dimension_record"
    assert EmbeddingTargetType.COMPETITOR == "competitor"
    assert EmbeddingTargetType.ISSUE == "issue"


def test_embedding_target_type_is_str_enum():
    assert isinstance(EmbeddingTargetType.NODE, str)
    assert EmbeddingTargetType.NODE == "node"


def test_embedding_target_type_tuple_alignment():
    """StrEnum + tuple 三重防护对齐。"""
    assert set(_EMBEDDING_TARGET_TYPES) == {t.value for t in EmbeddingTargetType}


# ─── SearchRequest ──────────────────────────────────────────────────────────


def test_search_request_valid_minimal():
    req = SearchRequest(query="hello")
    assert req.query == "hello"
    assert req.target_types is None
    assert req.limit == 20


def test_search_request_max_length_200():
    long_query = "a" * 200
    req = SearchRequest(query=long_query)
    assert len(req.query) == 200


def test_search_request_query_201_chars_passes_schema():
    """query 201 字符 → Pydantic 不拦（边界全在 router 层 / B-P2-M18 fix）。

    design §7 line 663：query 越界 / limit 越界全部由 router 手动 check 抛 400 INVALID_QUERY_LENGTH。
    Pydantic schema 不再做边界校验（保持错误路径单一）。
    """
    req = SearchRequest(query="a" * 201)
    assert len(req.query) == 201


def test_search_request_empty_query_passes_schema():
    """空 query → Pydantic 不拦（边界全在 router 层 / B-P2-M18 fix）。"""
    req = SearchRequest(query="")
    assert req.query == ""


def test_search_request_limit_range_passes_schema():
    """limit 越界 → Pydantic 不拦（边界全在 router 层 / B-P2-M18 fix）。"""
    req = SearchRequest(query="test", limit=100)
    assert req.limit == 100
    # 边界越界 Pydantic 不再拦（router 抛 400）
    req_low = SearchRequest(query="test", limit=0)
    assert req_low.limit == 0
    req_high = SearchRequest(query="test", limit=101)
    assert req_high.limit == 101


def test_search_request_target_types_list():
    req = SearchRequest(query="test", target_types=[EmbeddingTargetType.NODE])
    assert req.target_types == [EmbeddingTargetType.NODE]


def test_search_request_target_types_none_means_all():
    req = SearchRequest(query="test", target_types=None)
    assert req.target_types is None


# ─── SearchResultItem ────────────────────────────────────────────────────────


def test_search_result_item_valid():
    item = SearchResultItem(
        target_type=EmbeddingTargetType.NODE,
        target_id=uuid4(),
        title="Test Node",
        snippet="keyword match here",
        score=0.85,
        matched_by=["keyword", "semantic"],
        breadcrumb=["root", "parent", "Test Node"],
    )
    assert item.target_type == EmbeddingTargetType.NODE
    assert item.score == 0.85
    assert "keyword" in item.matched_by


def test_search_result_item_matched_by_literal():
    with pytest.raises(ValidationError):
        SearchResultItem(
            target_type=EmbeddingTargetType.NODE,
            target_id=uuid4(),
            title="T",
            snippet="s",
            score=0.5,
            matched_by=["invalid_channel"],  # 不在 Literal
            breadcrumb=[],
        )


# ─── SearchResponse ──────────────────────────────────────────────────────────


def test_search_response_valid():
    resp = SearchResponse(
        results=[],
        total=0,
        search_mode="hybrid",
        query_embedding_cached=False,
    )
    assert resp.total == 0
    assert resp.search_mode == "hybrid"


def test_search_response_search_mode_literal():
    with pytest.raises(ValidationError):
        SearchResponse(
            results=[],
            total=0,
            search_mode="semantic_only",  # 不在 Literal["hybrid", "keyword_only"]
            query_embedding_cached=False,
        )


# ─── EmbedSinglePayload（TaskPayload 继承）──────────────────────────────────


def test_embed_single_payload_valid():
    payload = EmbedSinglePayload(
        user_id=uuid4(),
        project_id=uuid4(),
        target_type=EmbeddingTargetType.NODE,
        target_id=uuid4(),
        provider="openai",
        model_name="text-embedding-3-small",
        model_version="v1",
        enqueued_by="incremental",
    )
    assert payload.provider == "openai"
    assert payload.enqueued_by == "incremental"


def test_embed_single_payload_inherits_task_payload():
    from api.queue.base import TaskPayload

    assert issubclass(EmbedSinglePayload, TaskPayload)


def test_embed_single_payload_has_user_id_and_project_id():
    uid = uuid4()
    pid = uuid4()
    payload = EmbedSinglePayload(
        user_id=uid,
        project_id=pid,
        target_type=EmbeddingTargetType.ISSUE,
        target_id=uuid4(),
        provider="mock",
        model_name="mock-default",
        model_version="v1",
        enqueued_by="backfill",
    )
    assert payload.user_id == uid
    assert payload.project_id == pid


def test_embed_single_payload_enqueued_by_literal():
    with pytest.raises(ValidationError):
        EmbedSinglePayload(
            user_id=uuid4(),
            project_id=uuid4(),
            target_type=EmbeddingTargetType.NODE,
            target_id=uuid4(),
            provider="mock",
            model_name="mock-default",
            model_version="v1",
            enqueued_by="manual",  # 不在 Literal
        )


def test_embed_single_payload_no_source_text_field():
    """source_text 不放 payload（design §12D line 954 字面）——extra='forbid'。"""
    with pytest.raises(ValidationError):
        EmbedSinglePayload(
            user_id=uuid4(),
            project_id=uuid4(),
            target_type=EmbeddingTargetType.NODE,
            target_id=uuid4(),
            provider="mock",
            model_name="mock-default",
            model_version="v1",
            enqueued_by="incremental",
            source_text="should not be here",  # extra field → forbid
        )


def test_embed_single_payload_target_type_enum():
    """target_type 是强类型枚举（非裸 str）。"""
    payload = EmbedSinglePayload(
        user_id=uuid4(),
        project_id=uuid4(),
        target_type="node",  # str 会被自动转枚举
        target_id=uuid4(),
        provider="mock",
        model_name="mock-default",
        model_version="v1",
        enqueued_by="model_upgrade",
    )
    assert payload.target_type == EmbeddingTargetType.NODE


# ─── Admin schemas ───────────────────────────────────────────────────────────


def test_backfill_request_valid():
    """BackfillRequest 继承 BaseModel（非 TaskPayload）— user_id 不再是字段（R1 fix #1 / ADR-002）。"""
    req = BackfillRequest(
        project_id=uuid4(),
    )
    assert req.provider is None
    assert req.model_name is None


def test_backfill_request_rejects_user_id():
    """BackfillRequest extra='forbid'：传 user_id 应 ValidationError（HTTP body 不应含 user_id）。"""
    with pytest.raises(ValidationError):
        BackfillRequest(
            user_id=uuid4(),  # 已删字段 / extra='forbid' 应拒绝
            project_id=uuid4(),
        )


def test_model_upgrade_request_valid():
    """ModelUpgradeRequest 继承 BaseModel（非 TaskPayload）— user_id 不再是字段（R1 fix #1）。"""
    req = ModelUpgradeRequest(
        project_id=uuid4(),
        new_provider="openai",
        new_model_name="text-embedding-3-large",
        new_model_version="v2",
    )
    assert req.new_provider == "openai"
    assert req.new_model_version == "v2"


def test_model_upgrade_request_rejects_user_id():
    """ModelUpgradeRequest extra='forbid'：传 user_id 应 ValidationError。"""
    with pytest.raises(ValidationError):
        ModelUpgradeRequest(
            user_id=uuid4(),  # 已删字段 / extra='forbid' 应拒绝
            project_id=uuid4(),
            new_provider="openai",
            new_model_name="m",
            new_model_version="v1",
        )
