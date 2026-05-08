"""M13 需求分析 Pydantic schema。

子片 2（本文件 partial）：仅 AnalysisLevel 枚举（service 层依赖）。
子片 3（待）：补 RequirementAnalysisRequest / SaveAnalysisRequest / SaveAnalysisResponse /
AffectedNodesResponse + 3 SSE event schema（SSEChunkEvent / SSECompleteEvent / SSEErrorEvent）。

design 真相源：design/02-modules/M13-requirement-analysis/00-design.md §7。
"""

from __future__ import annotations

from enum import StrEnum


class AnalysisLevel(StrEnum):
    """分析深度（design §1 AC1 + §7）。"""

    L1 = "L1"  # 快速影响面判断（~30s）
    L2 = "L2"  # 标准完整性 + 风险（~1-2min）
    L3 = "L3"  # 深度（含改进建议详述、~2-3min）
