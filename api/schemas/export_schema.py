"""M19 导出 Pydantic schema（design/02-modules/M19-import-export/00-design.md §7）。

两入口共享 ExportIncludeOptions：
- 入口 A：MultiNodeExportRequest（POST /api/projects/{pid}/exports / node_ids min 1 / max 20）
- 入口 B：SingleNodeExportRequest（POST /api/projects/{pid}/nodes/{nid}/export / 仅 include）

响应：200 OK + Content-Type=text/markdown + Content-Disposition: attachment
（Markdown bytes，非 JSON）。
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExportIncludeOptions(BaseModel):
    """include 章节开关（design §7）。"""

    model_config = ConfigDict(extra="forbid")

    dimensions: bool = True
    versions: bool = True
    competitors: bool = False
    issues: bool = True


class MultiNodeExportRequest(BaseModel):
    """入口 A：多 node 选择导出（design §7 / node_ids 1-20）。

    Pydantic schema 层校验 node_ids 长度上限（422 由 FastAPI ValidationException 处理）；
    Service 层 ExportService.generate_markdown 不再重复校验长度（双重防御 N/A — 上限是
    硬约束 / Service 层只做 cross-project 校验）。
    """

    model_config = ConfigDict(extra="forbid")

    node_ids: list[UUID] = Field(..., min_length=1, max_length=20)
    include: ExportIncludeOptions = Field(default_factory=ExportIncludeOptions)


class SingleNodeExportRequest(BaseModel):
    """入口 B：单 node 导出（design §7 / 等价 MultiNodeExportRequest(node_ids=[node_id])）。"""

    model_config = ConfigDict(extra="forbid")

    include: ExportIncludeOptions = Field(default_factory=ExportIncludeOptions)
