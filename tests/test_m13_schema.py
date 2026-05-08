"""M13 子片 3 — Pydantic schema 单元测试（轻量；schema 子片 ≥80% simplify SKIP）。

覆盖：
  - AnalysisLevel StrEnum 三档值
  - RequirementAnalysisRequest 边界（min_length=1 / max_length=5000）+ 默认 L2
  - SaveAnalysisRequest 必填字段约束 + analysis_time_ms ≥0
  - SaveAnalysisResponse / AffectedNodesResponse 字段缺省
  - SSE event 3 类强类型 + source Literal["ai"] 默认
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from api.schemas.analyze_schema import (
    AffectedNodesResponse,
    AnalysisLevel,
    RequirementAnalysisRequest,
    SaveAnalysisRequest,
    SaveAnalysisResponse,
    SSEChunkEvent,
    SSECompleteEvent,
    SSEErrorEvent,
)


def test_analysis_level_values():
    assert AnalysisLevel.L1.value == "L1"
    assert AnalysisLevel.L2.value == "L2"
    assert AnalysisLevel.L3.value == "L3"
    assert {x.value for x in AnalysisLevel} == {"L1", "L2", "L3"}


def test_requirement_request_defaults_l2():
    req = RequirementAnalysisRequest(requirement_text="a")
    assert req.analysis_level == AnalysisLevel.L2


def test_requirement_request_accepts_full_5000_chars():
    req = RequirementAnalysisRequest(requirement_text="x" * 5000, analysis_level=AnalysisLevel.L1)
    assert len(req.requirement_text) == 5000


def test_requirement_request_rejects_empty_text():
    with pytest.raises(ValidationError):
        RequirementAnalysisRequest(requirement_text="")


def test_requirement_request_rejects_overlong_text():
    with pytest.raises(ValidationError):
        RequirementAnalysisRequest(requirement_text="x" * 5001)


def test_save_request_required_fields_and_defaults():
    req = SaveAnalysisRequest(
        analysis_result="r",
        analysis_level=AnalysisLevel.L2,
        ai_provider="claude",
        ai_model="claude-sonnet-4-5",
        analysis_time_ms=100,
        requirement_text="t",
    )
    assert req.affected_node_ids == []  # 默认空列表
    assert req.ai_provider == "claude"


def test_save_request_rejects_negative_time_ms():
    with pytest.raises(ValidationError):
        SaveAnalysisRequest(
            analysis_result="r",
            analysis_level=AnalysisLevel.L1,
            ai_provider="m",
            ai_model="m",
            analysis_time_ms=-1,
            requirement_text="t",
        )


def test_save_response_serializes_iso_via_datetime():
    rid = uuid4()
    saved_at = datetime.now(tz=UTC)
    resp = SaveAnalysisResponse(dimension_record_id=rid, analysis_saved_at=saved_at)
    assert resp.message == "分析结果已保存"
    # pydantic v2 默认 datetime → ISO 8601 字符串
    dumped = resp.model_dump(mode="json")
    assert "T" in dumped["analysis_saved_at"]


def test_affected_nodes_response_empty_history_form():
    nid = uuid4()
    resp = AffectedNodesResponse(node_id=nid, affected_node_ids=[])
    assert resp.analysis_record_id is None
    assert resp.analysis_saved_at is None


def test_sse_chunk_event_default_source_ai():
    ev = SSEChunkEvent(text="hi", level=AnalysisLevel.L1)
    assert ev.source == "ai"


def test_sse_chunk_event_rejects_other_source():
    with pytest.raises(ValidationError):
        SSEChunkEvent(text="hi", level=AnalysisLevel.L1, source="user")  # type: ignore[arg-type]


def test_sse_complete_event_metadata_dict():
    ev = SSECompleteEvent(
        full_result="ok",
        metadata={
            "ai_provider": "claude",
            "ai_model": "m",
            "analysis_level": "L2",
            "analysis_time_ms": 1234,
        },
    )
    assert ev.metadata["ai_model"] == "m"


def test_sse_error_event_string_fields():
    ev = SSEErrorEvent(error="provider timeout", error_code="analysis_timeout")
    assert ev.error_code == "analysis_timeout"
