"""M13 AI 需求分析 router — design §7 + §8 + §12A 流式 SSE 子模板。

3 endpoints：
  - POST /api/projects/{pid}/nodes/{nid}/analyze/requirement  (editor / SSE 流式)
  - POST /api/projects/{pid}/nodes/{nid}/analyze/save         (editor / 写 M04)
  - GET  /api/projects/{pid}/nodes/{nid}/analyze/affected-nodes (viewer / 读 M04)

权限（design §8 R8-1 三层）：viewer 读 affected-nodes / editor 发起分析 + 保存；
viewer 写 2 端点 403（M07 立 / M08+M11+M12 应用 / M13 主动复制）。

SSE 协议（design §12A 7 字段）：
  - 端点路径：POST .../analyze/requirement
  - event 枚举：chunk / complete / error
  - data payload schema：SSEChunkEvent / SSECompleteEvent / SSEErrorEvent
  - 鉴权：ADR-004 P1 Bearer JWT（连接级 auth；无 chunk 级鉴权）
  - 超时：asyncio.timeout(300) 包 async for chunk
  - 取消：Request.is_disconnected() 检测 → provider.aclose() 释放底层流
  - 断线重连：不支持（用户重新发起）

事务边界：
  - analyze/requirement：纯流式不写 DB 不开事务
  - analyze/save：router 末 await db.commit()；M04 service 在同事务内代写 activity_log
  - analyze/affected-nodes：纯读
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.check_project_access import ProjectAccess, check_project_access
from api.core.db import get_db
from api.errors.exceptions import (
    AnalysisNodeNotFoundError,
    AnalysisProviderError,
    AnalysisProviderNotConfiguredError,
    AnalysisQuotaExceededError,
    AnalysisTimeoutError,
    ProjectNotFoundError,
)
from api.schemas.analyze_schema import (
    AffectedNodesResponse,
    RequirementAnalysisRequest,
    SaveAnalysisRequest,
    SaveAnalysisResponse,
    SSEChunkEvent,
    SSECompleteEvent,
    SSEErrorEvent,
)
from api.services.analyze_service import AnalyzeService

logger = logging.getLogger(__name__)

# design §12 字段⑤ 服务器硬超时（5min；ADR-001 TASK_TIMEOUTS["need_analysis"]=300s）
_STREAM_TIMEOUT_SECONDS = 300.0

analyze_router = APIRouter(
    prefix="/api/projects/{project_id}/nodes/{node_id}/analyze",
    tags=["analyze"],
)


def _sse_format(event: str, data_model) -> bytes:
    """SSE 行格式化（design §7 传输格式样例）：
    event: <name>
    data: <json>
    <空行>
    """
    payload = data_model.model_dump_json()
    return f"event: {event}\ndata: {payload}\n\n".encode()


# ─────────────── POST /analyze/requirement (editor / SSE 流式) ───────────────


@analyze_router.post("/requirement", status_code=status.HTTP_200_OK)
async def stream_requirement_analysis(
    request: Request,
    payload: RequirementAnalysisRequest,
    node_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """SSE 流式需求分析（design §12A）。

    - 鉴权：ADR-004 P1（连接级；check_project_access editor 拦 viewer 写 403）
    - 超时：asyncio.timeout(300) 包整个 async for chunk 循环
    - 取消：Request.is_disconnected() 每 yield 后检查；断开时 break + service finally
      会自动 await stream.aclose() 释放底层流（R1-C P1-01 立修）
    - 异常：在 SSE 流内 yield event:error 给前端；不抛 HTTP 错（流已 200 OK）
    """
    svc = AnalyzeService()

    async def generator() -> AsyncIterator[bytes]:
        full_chunks: list[str] = []
        t_start = time.monotonic()
        try:
            async with asyncio.timeout(_STREAM_TIMEOUT_SECONDS):
                async for chunk in svc.analyze_stream(
                    db,
                    project_id=access.project.id,
                    node_id=node_id,
                    user_id=access.user.id,
                    requirement_text=payload.requirement_text,
                    level=payload.analysis_level,
                ):
                    if await request.is_disconnected():
                        # design §12 字段⑥：客户端断开 → 服务器停 + service finally aclose
                        # 不发任何 SSE event（连接已断）
                        return
                    full_chunks.append(chunk)
                    yield _sse_format(
                        "chunk",
                        SSEChunkEvent(text=chunk, level=payload.analysis_level),
                    )
            # 流式自然完成 → complete 事件含 metadata 给前端做 save payload
            # R2 P2-4 立修：design §7 line 437 字面 metadata 应含 analysis_time_ms
            elapsed_ms = int((time.monotonic() - t_start) * 1000)
            yield _sse_format(
                "complete",
                SSECompleteEvent(
                    full_result="".join(full_chunks),
                    metadata={
                        # M02 Project 暂未实装 ai_model 字段（M02 sprint 时只加了
                        # ai_provider + ai_api_key_enc）；用 getattr 兼容直到 M02
                        # baseline-patch 加列。punt 到 M14+/sprint 后续。
                        "ai_provider": access.project.ai_provider or "",
                        "ai_model": getattr(access.project, "ai_model", None) or "",
                        "analysis_level": payload.analysis_level.value,
                        "analysis_time_ms": elapsed_ms,
                    },
                ),
            )
        except TimeoutError:
            # asyncio.timeout 触发（含 Python 3.11+ 内置 TimeoutError）
            yield _sse_format(
                "error",
                SSEErrorEvent(error="分析超时，请重试", error_code="analysis_timeout"),
            )
        except AnalysisTimeoutError:
            yield _sse_format(
                "error",
                SSEErrorEvent(error="分析超时，请重试", error_code="analysis_timeout"),
            )
        except AnalysisQuotaExceededError:
            yield _sse_format(
                "error",
                SSEErrorEvent(error="AI 配额已耗尽", error_code="analysis_quota_exceeded"),
            )
        except AnalysisProviderError:
            yield _sse_format(
                "error",
                SSEErrorEvent(
                    error="AI 服务调用失败，请稍后重试",
                    error_code="analysis_provider_error",
                ),
            )
        except AnalysisProviderNotConfiguredError:
            yield _sse_format(
                "error",
                SSEErrorEvent(
                    error="项目未配置 AI provider，请到项目设置页配置",
                    error_code="analysis_provider_not_configured",
                ),
            )
        except (AnalysisNodeNotFoundError, ProjectNotFoundError):
            # R2 P1-1 立修：generator 内 race（NodeService.breadcrumb / get_for_user 中途
            # 抛 NodeNotFound/ProjectNotFound）应映射 analysis_node_not_found 而非兜底
            # provider_error。design §13 line 723 字面：M03 get_by_id None → AnalysisNodeNotFoundError
            yield _sse_format(
                "error",
                SSEErrorEvent(
                    error="目标节点不存在或已被删除",
                    error_code="analysis_node_not_found",
                ),
            )
        except Exception as e:
            # R2 P1-1 立修延伸：兜底 except 留给真未知异常（不再吃 NodeNotFound/ProjectNotFound）
            logger.exception("analyze_stream unexpected error: %s", e)
            yield _sse_format(
                "error",
                SSEErrorEvent(error="分析失败，请重试", error_code="analysis_provider_error"),
            )

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            # 防中间代理缓冲（保证流式实时推送）
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ─────────────── POST /analyze/save (editor / 写 M04) ───────────────


@analyze_router.post(
    "/save",
    response_model=SaveAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_analysis(
    payload: SaveAnalysisRequest,
    node_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="editor")),
    db: AsyncSession = Depends(get_db),
) -> SaveAnalysisResponse:
    """保存分析结果到 M04 dimension_records（design §10 Q6 ack A 仅 save 写 1 条）。"""
    svc = AnalyzeService()
    rec = await svc.save_analysis(
        db,
        project_id=access.project.id,
        node_id=node_id,
        user_id=access.user.id,
        analysis_result=payload.analysis_result,
        requirement_text=payload.requirement_text,
        level=payload.analysis_level,
        ai_provider=payload.ai_provider,
        ai_model=payload.ai_model,
        analysis_time_ms=payload.analysis_time_ms,
        affected_node_ids=payload.affected_node_ids,
    )
    await db.commit()
    return SaveAnalysisResponse(
        dimension_record_id=rec.id,
        analysis_saved_at=rec.created_at,
    )


# ─────────────── GET /analyze/affected-nodes (viewer / 读 M04) ───────────────


@analyze_router.get("/affected-nodes", response_model=AffectedNodesResponse)
async def get_affected_nodes(
    node_id: UUID,
    access: ProjectAccess = Depends(check_project_access(role="viewer")),
    db: AsyncSession = Depends(get_db),
) -> AffectedNodesResponse:
    """读 (project, node) 上最新一条 requirement_analysis 的 affected_node_ids。

    无历史 → analysis_record_id=None / affected_node_ids=[] / saved_at=None
    （design line 739）。
    """
    svc = AnalyzeService()
    res = await svc.get_affected_nodes(
        db,
        project_id=access.project.id,
        node_id=node_id,
        user_id=access.user.id,
    )
    return AffectedNodesResponse(
        node_id=res.node_id,
        affected_node_ids=res.affected_node_ids,
        analysis_record_id=res.analysis_record_id,
        analysis_saved_at=res.analysis_saved_at,
    )


__all__ = ["analyze_router"]
