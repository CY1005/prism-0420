"""M15 子片 3 — Pydantic schema 单元测试（design §7）。

覆盖：
- ActivityStreamFilter from_dt > to_dt → ValidationError
- ActionType / TargetType enum 值与 model._ACTION_TYPES / _TARGET_TYPES 一致
- ActivityLogItem from_attributes 行为（含 metadata 字段映射）
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from api.errors.codes import ErrorCode
from api.errors.exceptions import ActivityStreamInvalidFilterError
from api.models.activity_log import _ACTION_TYPES, _TARGET_TYPES
from api.schemas.activity_stream_schema import (
    ActionType,
    ActivityLogItem,
    ActivityStreamFilter,
    TargetType,
)


def test_filter_from_dt_after_to_dt_raises_business_error():
    """R1 P1-1：raise 业务 code ActivityStreamInvalidFilterError（非裸 ValueError）。"""
    now = datetime.now(UTC)
    with pytest.raises(ActivityStreamInvalidFilterError) as ei:
        ActivityStreamFilter(from_dt=now, to_dt=now - timedelta(days=1))
    err = ei.value
    assert err.code == ErrorCode.ACTIVITY_STREAM_INVALID_FILTER
    assert err.http_status == 422
    assert "from_dt" in err.details and "to_dt" in err.details


def test_filter_equal_from_to_dt_ok():
    now = datetime.now(UTC)
    f = ActivityStreamFilter(from_dt=now, to_dt=now)
    assert f.from_dt == f.to_dt


def test_filter_default_page_and_size():
    f = ActivityStreamFilter()
    assert f.page == 1
    assert f.page_size == 50


def test_filter_page_size_max_200():
    with pytest.raises(ValidationError):
        ActivityStreamFilter(page_size=500)


def test_action_type_enum_matches_model_action_types():
    """schema ActionType Enum 全集 = model _ACTION_TYPES 字面（R10-2 owner 同步）。"""
    schema_values = {v.value for v in ActionType}
    model_values = set(_ACTION_TYPES)
    assert schema_values == model_values, (
        f"diff: schema-only={schema_values - model_values}, "
        f"model-only={model_values - schema_values}"
    )


def test_target_type_enum_matches_model_target_types():
    schema_values = {v.value for v in TargetType}
    model_values = set(_TARGET_TYPES)
    assert schema_values == model_values, (
        f"diff: schema-only={schema_values - model_values}, "
        f"model-only={model_values - schema_values}"
    )


def test_activity_log_item_from_dict():
    """ActivityLogItem 从 dict 构建（service 层 _to_item 用法）。"""
    data = {
        "id": uuid4(),
        "user_id": uuid4(),
        "user_name": "alice",
        "action_type": "node_created",
        "target_type": "node",
        "target_id": "00000000-0000-0000-0000-000000000001",
        "summary": "x",
        "metadata": {"k": "v"},
        "created_at": datetime.now(UTC),
    }
    item = ActivityLogItem.model_validate(data)
    assert item.action_type == ActionType.node_created
    assert item.metadata == {"k": "v"}


def test_activity_log_item_metadata_optional():
    item = ActivityLogItem.model_validate(
        {
            "id": uuid4(),
            "user_id": uuid4(),
            "user_name": "x",
            "action_type": "news_created",
            "target_type": "industry_news",
            "target_id": "00000000-0000-0000-0000-000000000002",
            "summary": "y",
            "metadata": None,
            "created_at": datetime.now(UTC),
        }
    )
    assert item.metadata is None
