"""M17 AI 导入 arq Queue tasks（design §6 + §12）。

横切归属（design §6 + R-X6 + 04-layer Q7）：业务 owner=M17，但位置在 api/queue/
横切目录下（与 base.py SYSTEM_USER_UUID + TaskPayload 同级）。

6 个任务函数（arq @task）：
1. import_extract        — 解压 zip / git clone / 创建 import_task_items
2. import_ai_step1       — AI 步骤 1：拆分 + 归类
3. import_ai_step2       — AI 步骤 2：提取 + 补全（→ awaiting_review）
4. import_ai_step3       — AI 步骤 3：关联 + 去重 + 差异标注（用户确认后触发）
5. import_batch_insert   — step3 完成后批量入库（R-X1：调 4 个 batch_create_in_transaction）
6. import_cleanup_dead_letter — cron daily 物理删 30 天 failed 任务

事务边界（R-X1 第二实例 / M11 ColdStart 第一实例 docstring 字面对照）：
- worker 自起 SessionLocal（独立请求级 Depends(get_db)）
- 业务路径走 worker session；失败补偿走 compensation_session helper（独立 connection）
- 重试策略：单步 3 次指数退避 1s/4s/16s；用尽 → status=failed + dead_letter=True

P2 worker-side Service re-auth（ADR-002）：
- 每个 task 第一行强制 ImportXxxPayload.model_validate(raw)（extra='forbid' 防漂移）
- 然后调 ImportService.check_task_access(payload.user_id, payload.project_id, payload.task_id)
- 任何越权 → 走失败路径，不透传到下游模块
"""

from __future__ import annotations

import logging
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from api.queue.base import TaskPayload

log = logging.getLogger(__name__)


# ─────────────── Payload 子类（design §12 字面 / 强类型 audit B5 修复）───────────────


class ImportExtractPayload(TaskPayload):
    task_id: UUID
    source_type: Literal["zip", "git_url", "git_bundle"]


class ImportAIStepPayload(TaskPayload):
    task_id: UUID
    step: Literal[1, 2, 3]
    chunk_id: UUID | None = None  # 大 zip 分 chunk 时（M17 sprint 不实装 chunk，预留）


class ConfirmedNodeData(BaseModel):
    """ConfirmedNode 的 dict 表达，用于 Queue payload 序列化（design §12 字面）。"""

    model_config = ConfigDict(extra="forbid")

    proposed_id: UUID
    name: str
    type: str = "leaf"
    parent_proposed_id: UUID | None = None
    skipped: bool = False


class ConfirmedDimensionData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposed_id: UUID
    target_proposed_node_id: UUID
    dimension_type_key: str
    content: dict[str, Any]


class ConfirmedCompetitorData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposed_id: UUID
    display_name: str
    website_url: str | None = None
    description: str | None = None


class ConfirmedIssueData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposed_id: UUID
    target_proposed_node_id: UUID | None = None
    title: str
    category: str
    description: str


class ConfirmedImportData(BaseModel):
    """用户 review 后的最终数据——结构化替代裸 dict（design §12 字面 / audit B5 修复）。"""

    model_config = ConfigDict(extra="forbid")

    nodes: list[ConfirmedNodeData] = []
    dimensions: list[ConfirmedDimensionData] = []
    competitors: list[ConfirmedCompetitorData] = []
    issues: list[ConfirmedIssueData] = []
    skip_proposed_ids: list[UUID] = []


class ImportBatchInsertPayload(TaskPayload):
    task_id: UUID
    confirmed_data: ConfirmedImportData


# ─────────────── arq @task 入口（design §6 字面 / worker 入口 5 步守门）───────────────


async def import_extract(ctx: dict[str, Any], raw: dict[str, Any]) -> None:
    """步骤 0：解压 zip / git clone → 创建 import_task_items → enqueue ai_step1。

    异常映射：
    - ImportInvalidSourceError → service 内 mark failed (extract stage)
    - 任何其他异常 → arq 重试链；用尽 → failed + dead_letter=True
    """
    payload = ImportExtractPayload.model_validate(raw)
    from api.core.db import SessionLocal
    from api.services.import_service import ImportService

    service = ImportService()
    async with SessionLocal() as db:
        await service.run_extract(
            db,
            user_id=payload.user_id,
            project_id=payload.project_id,
            task_id=payload.task_id,
        )


async def import_ai_step1(ctx: dict[str, Any], raw: dict[str, Any]) -> None:
    """步骤 1：AI 拆分 + 归类（→ ai_step2）。"""
    payload = ImportAIStepPayload.model_validate(raw)
    if payload.step != 1:
        raise ValueError(f"import_ai_step1 expects step=1, got step={payload.step}")
    from api.core.db import SessionLocal
    from api.services.import_service import ImportService

    service = ImportService()
    async with SessionLocal() as db:
        await service.run_ai_step(
            db,
            user_id=payload.user_id,
            project_id=payload.project_id,
            task_id=payload.task_id,
            step=1,
        )


async def import_ai_step2(ctx: dict[str, Any], raw: dict[str, Any]) -> None:
    """步骤 2：AI 提取 + 补全（→ awaiting_review；推 review_ready 事件）。"""
    payload = ImportAIStepPayload.model_validate(raw)
    if payload.step != 2:
        raise ValueError(f"import_ai_step2 expects step=2, got step={payload.step}")
    from api.core.db import SessionLocal
    from api.services.import_service import ImportService

    service = ImportService()
    async with SessionLocal() as db:
        await service.run_ai_step(
            db,
            user_id=payload.user_id,
            project_id=payload.project_id,
            task_id=payload.task_id,
            step=2,
        )


async def import_ai_step3(ctx: dict[str, Any], raw: dict[str, Any]) -> None:
    """步骤 3：AI 关联 + 去重 + 差异标注（用户 confirm 后触发 → importing）。"""
    payload = ImportAIStepPayload.model_validate(raw)
    if payload.step != 3:
        raise ValueError(f"import_ai_step3 expects step=3, got step={payload.step}")
    from api.core.db import SessionLocal
    from api.services.import_service import ImportService

    service = ImportService()
    async with SessionLocal() as db:
        await service.run_ai_step(
            db,
            user_id=payload.user_id,
            project_id=payload.project_id,
            task_id=payload.task_id,
            step=3,
        )


async def import_batch_insert(ctx: dict[str, Any], raw: dict[str, Any]) -> None:
    """步骤 4：批量入库（R-X1 调 M03/M04/M06/M07 batch_create_in_transaction）。"""
    payload = ImportBatchInsertPayload.model_validate(raw)
    from api.core.db import SessionLocal
    from api.services.import_service import ImportService

    service = ImportService()
    async with SessionLocal() as db:
        await service.run_batch_insert(
            db,
            user_id=payload.user_id,
            project_id=payload.project_id,
            task_id=payload.task_id,
            confirmed=payload.confirmed_data,
        )


async def import_cleanup_dead_letter(ctx: dict[str, Any], raw: dict[str, Any]) -> int:
    """cron daily：物理删 status=failed 且 created_at < NOW - 30d 的死信任务。

    payload.user_id 必须 = SYSTEM_USER_UUID（ADR-002 §1.1）；不写 activity_log
    （housekeeping 而非业务事件 / design §12 字面）。
    """
    payload = TaskPayload.model_validate(raw)
    from api.core.db import SessionLocal
    from api.services.import_service import ImportService

    service = ImportService()
    async with SessionLocal() as db:
        count = await service.cleanup_dead_letter(db, system_user_id=payload.user_id)
        await db.commit()
        return count


__all__ = [
    "ConfirmedCompetitorData",
    "ConfirmedDimensionData",
    "ConfirmedImportData",
    "ConfirmedIssueData",
    "ConfirmedNodeData",
    "ImportAIStepPayload",
    "ImportBatchInsertPayload",
    "ImportExtractPayload",
    "import_ai_step1",
    "import_ai_step2",
    "import_ai_step3",
    "import_batch_insert",
    "import_cleanup_dead_letter",
    "import_extract",
]
