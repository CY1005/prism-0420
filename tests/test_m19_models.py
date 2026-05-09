"""M19 导入/导出 — model/enum 同步守护测试（子片 1）。

M19 是只读聚合模块（design §3 字面：无主表 / 复用上游模型）。本测试仅守护
M15 NEW 元教训"横切表 owner enum 4 处同步责任"——M19 sprint 新增 ActionType
"exported"。M03 已落 TargetType "node" → 不在本测试范围。

四处同步对账（M15 立 / M16 R14 ci-lint 守护 / M19 复用范式）：
1. api/models/activity_log.py:_ACTION_TYPES tuple
2. api/schemas/activity_stream_schema.py:ActionType StrEnum
3. CHECK constraint（基于 _ACTION_TYPES 自动构造，间接守护）
4. Alembic m19_export.py ALTER CHECK constraint（schema-level 守护）
"""

from __future__ import annotations


def test_action_type_enum_includes_m19_export():
    """M19 sprint 新增 "exported" action_type 必入 _ACTION_TYPES tuple。"""
    from api.models.activity_log import _ACTION_TYPES

    assert "exported" in _ACTION_TYPES


def test_schema_action_type_strenum_includes_export():
    """M19 sprint 新增 "exported" 必入 schema StrEnum。"""
    from api.schemas.activity_stream_schema import ActionType

    assert ActionType.exported.value == "exported"


def test_target_type_node_already_present():
    """M19 design §10 字面：target_type=node（M03 已 baseline-patch 落 / 不需 M19 新增）。"""
    from api.models.activity_log import _TARGET_TYPES
    from api.schemas.activity_stream_schema import TargetType

    assert "node" in _TARGET_TYPES
    assert TargetType.node.value == "node"


def test_action_type_full_sync_after_m19():
    """4 处同步对账：M19 sprint 完成后 schema StrEnum 与 model._ACTION_TYPES 全集仍一致。"""
    from api.models.activity_log import _ACTION_TYPES
    from api.schemas.activity_stream_schema import ActionType

    assert set(_ACTION_TYPES) == {a.value for a in ActionType}
