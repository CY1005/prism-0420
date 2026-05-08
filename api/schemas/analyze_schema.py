"""M13 需求分析 Pydantic schema (design §7 + SSE event schema)。

子片 2 已落 AnalysisLevel 枚举；本子片 3 补：
  - Request：RequirementAnalysisRequest / SaveAnalysisRequest
  - Response：SaveAnalysisResponse / AffectedNodesResponse
  - SSE event：SSEChunkEvent / SSECompleteEvent / SSEErrorEvent（R7-1 强类型，Router 层负责序列化）

design 真相源：design/02-modules/M13-requirement-analysis/00-design.md §7 + §12A 字段③。
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AnalysisLevel(StrEnum):
    """分析深度（design §1 AC1 + §7）。"""

    L1 = "L1"  # 快速影响面判断（~30s）
    L2 = "L2"  # 标准完整性 + 风险（~1-2min）
    L3 = "L3"  # 深度（含改进建议详述、~2-3min）


# ─── Request ───


class RequirementAnalysisRequest(BaseModel):
    """POST /api/projects/{pid}/nodes/{nid}/analyze/requirement 请求体。

    design §7：requirement_text 1-5000 字符；analysis_level 可选默认 L2。
    """

    requirement_text: str = Field(..., min_length=1, max_length=5000)
    analysis_level: AnalysisLevel = AnalysisLevel.L2


class SaveAnalysisRequest(BaseModel):
    """POST /api/projects/{pid}/nodes/{nid}/analyze/save 请求体。

    design §7：保存时回传 ai_provider/ai_model/analysis_time_ms 留痕（审计可回溯）。
    """

    analysis_result: str = Field(..., min_length=1)
    analysis_level: AnalysisLevel
    affected_node_ids: list[UUID] = Field(default_factory=list)
    ai_provider: str = Field(..., min_length=1, max_length=50)
    ai_model: str = Field(..., min_length=1, max_length=100)
    analysis_time_ms: int = Field(..., ge=0)
    requirement_text: str = Field(..., min_length=1, max_length=5000)


# ─── Response ───


class SaveAnalysisResponse(BaseModel):
    """POST /api/projects/{pid}/nodes/{nid}/analyze/save 响应。"""

    dimension_record_id: UUID
    analysis_saved_at: datetime  # 由 router 序列化为 ISO 8601
    message: str = "分析结果已保存"


class AffectedNodesResponse(BaseModel):
    """GET /api/projects/{pid}/nodes/{nid}/analyze/affected-nodes 响应。

    无历史分析 → analysis_record_id=None / affected_node_ids=[]（design line 739）。
    """

    node_id: UUID
    affected_node_ids: list[UUID]
    analysis_record_id: UUID | None = None
    analysis_saved_at: datetime | None = None


# ─── SSE Event Schema (§12A 子模板核心) ───


class SSEChunkEvent(BaseModel):
    """event: chunk ——一段增量分析文本（design §7 字段③）。"""

    text: str
    level: AnalysisLevel
    source: Literal["ai"] = "ai"  # 未来扩展 "template" / "system" 区分


class SSECompleteEvent(BaseModel):
    """event: complete ——流式结束，含元数据给前端做 save payload。"""

    full_result: str
    metadata: dict[str, Any]
    # metadata 形态约定（design §7）：
    #   {ai_provider, ai_model, analysis_level, analysis_time_ms, matched_template_id?}


class SSEErrorEvent(BaseModel):
    """event: error ——流式失败（provider / 超时 / 其他）。"""

    error: str  # 面向用户的错误描述
    error_code: str  # 业务错误码（§13 ErrorCode value 字符串）
