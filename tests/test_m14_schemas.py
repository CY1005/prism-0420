"""M14 子片 3 — Pydantic schemas 单元测试。

覆盖 design §7：
- NewsCreate / NewsUpdate 字段约束（title 长度 + URL 格式 + tags 默认）
- NewsResponse / NewsListResponse from_attributes 序列化
- NewsNodeLinkCreate / NewsNodeLinkResponse
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from api.schemas.industry_news_schema import (
    NewsCreate,
    NewsListResponse,
    NewsNodeLinkCreate,
    NewsNodeLinkResponse,
    NewsResponse,
    NewsUpdate,
    NodeRef,
)


def test_news_create_minimal():
    c = NewsCreate(title="t")
    assert c.title == "t"
    assert c.tags == []
    assert c.summary is None


def test_news_create_full():
    c = NewsCreate(
        title="AI 监管新规",
        summary="摘要",
        source_url="https://example.com/a",
        published_date=date(2026, 5, 1),
        tags=["AI", "监管"],
    )
    assert str(c.source_url) == "https://example.com/a"
    assert c.tags == ["AI", "监管"]


def test_news_create_title_too_long_raises():
    with pytest.raises(ValidationError):
        NewsCreate(title="x" * 201)


def test_news_create_empty_title_raises():
    with pytest.raises(ValidationError):
        NewsCreate(title="")


def test_news_create_invalid_url_raises():
    with pytest.raises(ValidationError):
        NewsCreate(title="t", source_url="not-a-url")


def test_news_create_tag_too_long_raises():
    """R1-C P1-3 立修：tags 单元素 max_length=50。"""
    with pytest.raises(ValidationError):
        NewsCreate(title="t", tags=["x" * 51])


def test_news_update_tag_too_long_raises():
    with pytest.raises(ValidationError):
        NewsUpdate(tags=["x" * 51])


def test_news_update_partial():
    u = NewsUpdate(title="new")
    assert u.title == "new"
    assert u.summary is None


def test_news_update_title_too_long_raises():
    with pytest.raises(ValidationError):
        NewsUpdate(title="x" * 201)


def test_node_ref_required_fields():
    r = NodeRef(node_id=uuid4(), node_name="x", project_id=uuid4())
    assert r.node_name == "x"


def test_news_response_from_dict():
    now = datetime.now(UTC)
    payload = {
        "id": uuid4(),
        "title": "t",
        "summary": None,
        "source_url": None,
        "published_date": None,
        "source_type": "manual",
        "tags": ["a"],
        "linked_nodes": [],
        "created_by": uuid4(),
        "created_by_name": "alice",
        "created_at": now,
        "updated_at": now,
    }
    r = NewsResponse(**payload)
    assert r.title == "t"
    assert r.source_type == "manual"
    assert r.linked_nodes == []


def test_news_list_response():
    now = datetime.now(UTC)
    item = NewsResponse(
        id=uuid4(),
        title="t",
        summary=None,
        source_url=None,
        published_date=None,
        source_type="manual",
        tags=[],
        linked_nodes=[],
        created_by=uuid4(),
        created_at=now,
        updated_at=now,
    )
    lr = NewsListResponse(items=[item], total=1, page=1, page_size=20)
    assert lr.total == 1
    assert len(lr.items) == 1


def test_news_node_link_create_requires_node_id():
    with pytest.raises(ValidationError):
        NewsNodeLinkCreate()  # type: ignore


def test_news_node_link_response_required_fields():
    payload = {
        "news_id": uuid4(),
        "node_id": uuid4(),
        "node_name": "x",
        "linked_by": uuid4(),
        "linked_at": datetime.now(UTC),
    }
    r = NewsNodeLinkResponse(**payload)
    assert r.node_name == "x"
