"""M19 导出 router — design §7 + §8.

2 endpoints：
  - POST /api/projects/{pid}/exports                 入口 A 多 node（≤20）— viewer
  - POST /api/projects/{pid}/nodes/{nid}/export      入口 B 单 node — viewer

权限（design §8）：viewer 即可导出（只读 / R10-2 例外不适用——M19 写 activity_log 一条
但语义只读 / 与 read 403 范式一致 / M02-M18 写 403 N/A 显式声明）。

事务边界（M02-M18 范式）：router 末 await db.commit()；异常由 FastAPI 不调 commit
→ implicit rollback（design §5）。

响应：200 OK + Content-Type=text/markdown; charset=utf-8 + Content-Disposition:
attachment; filename="prism-export-{timestamp}.md"（design §7 字面）。
filename 服务端构造（无用户输入），仍 sanitize 控制字符防 header 注入（M11/M17 输入端
sanitize 范式输出端首发 / cross-sprint #17 第三实例触发：根源不同——输入是用户 upload
filename / 输出是服务端拼装 timestamp 字符串，control 字符理论不会出现但纵深防御）。
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.check_project_access import ProjectAccess, check_project_access
from api.core.db import get_db
from api.schemas.export_schema import (
    MultiNodeExportRequest,
    SingleNodeExportRequest,
)
from api.services.export_service import ExportService

export_router = APIRouter(
    prefix="/api/projects/{project_id}",
    tags=["export"],
)


_FILENAME_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")


def _build_export_filename() -> str:
    """构造 Content-Disposition filename（服务端 timestamp 拼装 / 无用户输入）。

    格式：prism-export-{YYYYMMDDTHHMMSSZ}.md
    sanitize：strip 控制字符（纵深防御 / 理论不会出现但 cross-sprint #17 立规精神延续）。
    """
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    raw = f"prism-export-{ts}.md"
    return _FILENAME_CONTROL_CHARS_RE.sub("", raw)


def _markdown_response(body: bytes) -> Response:
    return Response(
        content=body,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{_build_export_filename()}"'},
    )


# ─────────────── 入口 A：多 node 导出 ───────────────


@export_router.post("/exports")
async def export_multi_nodes(
    payload: MultiNodeExportRequest,
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """入口 A：用户在模块树/全景图多选 node 后点击"导出报告"。"""
    svc = ExportService()
    body = await svc.generate_markdown(
        db,
        project_id=access.project.id,
        node_ids=payload.node_ids,
        include=payload.include,
        user_id=access.user.id,
    )
    await db.commit()
    return _markdown_response(body)


# ─────────────── 入口 B：单 node 导出 ───────────────


@export_router.post("/nodes/{node_id}/export")
async def export_single_node(
    node_id: Annotated[UUID, Path()],
    payload: SingleNodeExportRequest,
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """入口 B：node 档案页右上角"导出"按钮。等价 A 传 node_ids=[node_id]。"""
    svc = ExportService()
    body = await svc.generate_markdown(
        db,
        project_id=access.project.id,
        node_ids=[node_id],
        include=payload.include,
        user_id=access.user.id,
    )
    await db.commit()
    return _markdown_response(body)
