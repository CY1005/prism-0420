"""M10 Pydantic schemas — design/02-modules/M10-overview/00-design.md §7."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

NodeTypeLiteral = Literal["folder", "file"]


class NodeOverview(BaseModel):
    """单节点完善度信息（嵌套 children 用于树渲染）。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    parent_id: UUID | None
    name: str
    type: NodeTypeLiteral
    depth: int
    sort_order: int
    path: str
    filled_count: int
    completion_rate: float
    children: list["NodeOverview"] = []


NodeOverview.model_rebuild()


class OverviewStats(BaseModel):
    total_nodes: int
    file_nodes: int
    fully_complete_nodes: int
    empty_nodes: int
    avg_completion_rate: float
    enabled_dimension_count: int


class OverviewResponse(BaseModel):
    project_id: UUID
    tree: list[NodeOverview]
    stats: OverviewStats


class OverviewStatsResponse(BaseModel):
    project_id: UUID
    stats: OverviewStats


# NodeCompletionResponse: 走 M04 dimension_router /completion endpoint（避免双注册）；
# M10 service.get_node_completion 保留作内部接口；schema 留作未来 M04 委托可用。
class NodeCompletionResponse(BaseModel):
    node_id: UUID
    filled_count: int
    enabled_count: int
    completion_rate: float
