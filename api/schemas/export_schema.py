"""M19 导出 Pydantic schema（design/02-modules/M19-import-export/00-design.md §7）。

两入口共享 ExportIncludeOptions：
- 入口 A：MultiNodeExportRequest（POST /api/projects/{pid}/exports / node_ids min 1 / max 20）
- 入口 B：SingleNodeExportRequest（POST /api/projects/{pid}/nodes/{nid}/export / 仅 include）

响应：200 OK + Content-Type=text/markdown + Content-Disposition: attachment
（Markdown bytes，非 JSON）。

R1 立修（2026-05-09）：
- R1-A P1-2：node_ids 超上限走业务码 ExportNodeLimitExceededError（422 + code=
  export_node_limit_exceeded），不再依赖 Pydantic 通用 validation_error 丢失业务码
  （M15 ActivityStreamFilter model_validator 范式延续）
- R1-C P1-2：include 全 False 走业务码（提前 422 防 Service 层走完 4 DAO 才发现空 I/O 浪费）
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from api.errors.exceptions import (
    ExportNodeLimitExceededError,
)
from api.errors.exceptions import (
    ValidationError as AppValidationError,
)


class ExportIncludeOptions(BaseModel):
    """include 章节开关（design §7）。

    R1-C P1-2 立修：至少一个章节为 True（防 Service 层 4 DAO 查完才抛 422）。
    """

    model_config = ConfigDict(extra="forbid")

    dimensions: bool = True
    versions: bool = True
    competitors: bool = False
    issues: bool = True

    @model_validator(mode="after")
    def at_least_one_section(self) -> ExportIncludeOptions:
        if not (self.dimensions or self.versions or self.competitors or self.issues):
            raise AppValidationError(
                "At least one include section must be enabled",
                hint="dimensions/versions/competitors/issues — set at least one to true",
            )
        return self


class MultiNodeExportRequest(BaseModel):
    """入口 A：多 node 选择导出（design §7 / node_ids 1-20）。

    R1-A P1-2 立修：max_length 校验改走 model_validator 抛业务码 ExportNodeLimitExceededError
    （422 + code=export_node_limit_exceeded 不丢失业务语义 / M15 ActivityStreamFilter 范式）。
    保留 Pydantic min_length=1（空列表通用 422 即可，无业务语义需求）。
    """

    model_config = ConfigDict(extra="forbid")

    node_ids: list[UUID] = Field(..., min_length=1)
    include: ExportIncludeOptions = Field(default_factory=ExportIncludeOptions)

    @model_validator(mode="after")
    def check_node_count(self) -> MultiNodeExportRequest:
        if len(self.node_ids) > 20:
            raise ExportNodeLimitExceededError(
                provided=len(self.node_ids),
                max_allowed=20,
            )
        return self


class SingleNodeExportRequest(BaseModel):
    """入口 B：单 node 导出（design §7 / 等价 MultiNodeExportRequest(node_ids=[node_id])）。"""

    model_config = ConfigDict(extra="forbid")

    include: ExportIncludeOptions = Field(default_factory=ExportIncludeOptions)
