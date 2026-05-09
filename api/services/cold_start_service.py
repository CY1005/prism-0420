"""M11 冷启动 OrchestratorService（design/02-modules/M11-cold-start/00-design.md §6/§10）。

R-X1 orchestrator 模式：M11 **不直 INSERT 跨模块表**，调 4 个 service.batch_create_in_transaction：
  - M03 NodeService.batch_create_in_transaction
  - M04 DimensionService.batch_create_in_transaction
  - M06 CompetitorService.batch_create_in_transaction
  - M07 IssueService.batch_create_in_transaction

事务边界（design §5 多表事务 + R-X1 失败补偿 commit boundary 隔离 / M17 sprint
子片 0 prep 重构 2026-05-09）：
- 业务路径（task 创建 + batch_create_in_transaction × 4 + 状态扭转）共享 router 注入的
  request-scope db；router 成功 commit / 失败 rollback。
- task 创建后立即 commit（service 内 await db.commit()）—— 把 task 行从批量入库事务里
  解耦出去，让失败补偿能从独立 connection 看到任务。后续状态扭转 / batch INSERT 走
  自动起的新 txn，失败时 rollback 只丢业务写入，不丢任务身份。
- 失败补偿走独立 connection（compensation_session helper）：service 在抛异常前用
  comp_db 写 task=failed + error_report + cold_start_failed 事件，comp_db.commit()
  立即可见。caller（router）catches 后只需 db.rollback() 丢业务事务（task=failed 状态
  已由 comp_db 落盘，无需 router 再次 commit 失败状态——R2 P1-01 punt 关闭）。
- 立规来源：feedback_rx1_orchestrator_design L1 字面 + design/00-architecture/
  06-design-principles.md 清单 6（commit boundary 隔离）+
  api/services/orchestrator_helpers.py 第二实例 docstring 对照表。
- 兼容测试 fixture（join_transaction_mode='create_savepoint'）：tests/conftest.py
  autouse fixture 把 orchestrator_helpers.SessionLocal monkeypatch 成共享 test
  connection 的 sessionmaker（savepoint 模拟独立 commit boundary）。

CSV 模板（G6 决策 / 固定列 / 不支持自定义映射）：
  ``node_path,node_type,dimension_key,dimension_content,competitor_name,
    competitor_url,issue_title,issue_category,issue_description``
  仅 node_path 必填；其他字段空表示该行不生成相应 entity。

R10-1：4 个 batch_create_in_transaction 各自写 N 条 activity_log；
       orchestrator 完成时再写 1 条聚合事件（cold_start.completed / failed）。
"""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.core.logging import log
from api.dao.cold_start_dao import ColdStartDAO
from api.errors.exceptions import (
    ColdStartBatchInsertFailedError,
    ColdStartCsvInvalidError,
    ColdStartFileTooLargeError,
    ColdStartRowValidationFailedError,
    ColdStartTaskNotFoundError,
)
from api.models.cold_start_task import ColdStartStatus, ColdStartTask
from api.models.issue import ISSUE_CATEGORIES
from api.services.activity_log_service import write_event
from api.services.competitor_service import CompetitorService
from api.services.dimension_service import DimensionService
from api.services.issue_service import IssueService
from api.services.node_service import NodeService
from api.services.orchestrator_helpers import compensation_session

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10MB（design §1 G6）
MAX_ROWS = 1000  # design §1 G6 同步阈值

REQUIRED_COLUMNS = {
    "node_path",
}
OPTIONAL_COLUMNS = {
    "node_type",
    "dimension_key",
    "dimension_content",
    "competitor_name",
    "competitor_url",
    "issue_title",
    "issue_category",
    "issue_description",
}


class ParsedCsv:
    """CSV 解析中间结果（service 内部使用）。"""

    def __init__(
        self,
        *,
        nodes_data: list[dict[str, Any]],
        dimensions_pending: list[dict[str, Any]],
        competitors_data: list[dict[str, Any]],
        issues_pending: list[dict[str, Any]],
        total_rows: int,
        errors: list[dict[str, Any]],
    ) -> None:
        self.nodes_data = nodes_data
        self.dimensions_pending = dimensions_pending
        self.competitors_data = competitors_data
        self.issues_pending = issues_pending
        self.total_rows = total_rows
        self.errors = errors


def _check_csv_size_or_raise(content_bytes: bytes) -> None:
    """M-CLEANUP（cross-sprint #8 / M11 punt 立修）：CSV 大小校验单一 helper。

    parse_csv（独立调用 helper / 自防御）+ process_csv（orchestrator 预检 / 防 task 行无意义
    创建）双调用都走本 helper。两次检查保留 — DRY 字面 / 行为不变。
    """
    if len(content_bytes) > MAX_FILE_BYTES:
        raise ColdStartFileTooLargeError(max_bytes=MAX_FILE_BYTES, actual_bytes=len(content_bytes))


def parse_csv(content_bytes: bytes) -> ParsedCsv:
    """解析 CSV bytes → 4 类 batch_create 的 raw payload + 行级错误列表。

    抛 ColdStartCsvInvalidError：文件无法解析 / 缺必填列。
    返回 ParsedCsv：errors 非空表示有行级校验失败（不抛，由 caller 决策）。
    """
    _check_csv_size_or_raise(content_bytes)

    try:
        text = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ColdStartCsvInvalidError(reason=f"UTF-8 decode failed: {e}") from e

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ColdStartCsvInvalidError(reason="CSV has no header row")
    cols = set(reader.fieldnames)
    missing = REQUIRED_COLUMNS - cols
    if missing:
        raise ColdStartCsvInvalidError(reason=f"missing required columns: {sorted(missing)}")

    nodes_data: list[dict[str, Any]] = []
    dimensions_pending: list[dict[str, Any]] = []
    competitors_data: list[dict[str, Any]] = []
    issues_pending: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen_paths: dict[str, str] = {}  # node_path → temp_id
    total = 0

    for idx, row in enumerate(reader, start=2):  # row 2 是第一条数据（行 1 是 header）
        total += 1
        if total > MAX_ROWS:
            raise ColdStartCsvInvalidError(reason=f"row count {total} exceeds MAX_ROWS={MAX_ROWS}")

        path = (row.get("node_path") or "").strip()
        if not path:
            errors.append({"row": idx, "field": "node_path", "message": "node_path required"})
            continue
        if not path.startswith("/"):
            errors.append(
                {
                    "row": idx,
                    "field": "node_path",
                    "message": "node_path must start with '/'",
                }
            )
            continue

        # 节点（去重 + 父子拓扑：path 拆分按层级）
        if path not in seen_paths:
            parts = [p for p in path.split("/") if p]
            parent_temp: str | None = None
            cumulative = ""
            for part in parts[:-1]:
                cumulative = f"{cumulative}/{part}"
                if cumulative not in seen_paths:
                    temp = f"t-{len(seen_paths)}"
                    seen_paths[cumulative] = temp
                    nodes_data.append(
                        {
                            "name": part,
                            "type": "folder",
                            "parent_temp_id": parent_temp,
                            "temp_id": temp,
                        }
                    )
                parent_temp = seen_paths[cumulative]
            # 当前 node
            temp = f"t-{len(seen_paths)}"
            seen_paths[path] = temp
            nodes_data.append(
                {
                    "name": parts[-1] if parts else path,
                    "type": (row.get("node_type") or "folder").strip() or "folder",
                    "parent_temp_id": parent_temp,
                    "temp_id": temp,
                }
            )

        node_temp = seen_paths[path]

        # 维度记录（pending：node 真 id 在 batch_create 后才有）
        dim_key = (row.get("dimension_key") or "").strip()
        dim_content = (row.get("dimension_content") or "").strip()
        if dim_key and dim_content:
            dimensions_pending.append(
                {
                    "node_temp_id": node_temp,
                    "dimension_key": dim_key,
                    "content": {"text": dim_content},
                    "row": idx,
                }
            )

        # 竞品（项目级，不挂 node）
        comp_name = (row.get("competitor_name") or "").strip()
        if comp_name:
            competitors_data.append(
                {
                    "display_name": comp_name,
                    "website_url": (row.get("competitor_url") or "").strip() or None,
                }
            )

        # 问题（可挂 node_temp）
        issue_title = (row.get("issue_title") or "").strip()
        if issue_title:
            issue_cat = (row.get("issue_category") or "").strip()
            if issue_cat not in ISSUE_CATEGORIES:
                errors.append(
                    {
                        "row": idx,
                        "field": "issue_category",
                        "message": f"invalid category '{issue_cat}'",
                    }
                )
                continue
            issues_pending.append(
                {
                    "node_temp_id": node_temp,
                    "category": issue_cat,
                    "title": issue_title,
                    "description": (row.get("issue_description") or "").strip() or issue_title,
                    "row": idx,
                }
            )

    return ParsedCsv(
        nodes_data=nodes_data,
        dimensions_pending=dimensions_pending,
        competitors_data=competitors_data,
        issues_pending=issues_pending,
        total_rows=total,
        errors=errors,
    )


class ColdStartOrchestratorService:
    """M11 冷启动 orchestrator service。

    R-X1：不直 INSERT 跨模块表；只调 4 个 service.batch_create_in_transaction。
    R-X3：DAO 共享外部 session；caller（router）负责 commit。
    """

    def __init__(
        self,
        dao: ColdStartDAO | None = None,
        node_service: NodeService | None = None,
        dimension_service: DimensionService | None = None,
        competitor_service: CompetitorService | None = None,
        issue_service: IssueService | None = None,
    ) -> None:
        self.dao = dao or ColdStartDAO()
        self.node_service = node_service or NodeService()
        self.dimension_service = dimension_service or DimensionService()
        self.competitor_service = competitor_service or CompetitorService()
        self.issue_service = issue_service or IssueService()

    async def get_by_id(
        self, db: AsyncSession, *, project_id: UUID, task_id: UUID
    ) -> ColdStartTask:
        t = await self.dao.get_by_id(db, task_id, project_id)
        if t is None:
            raise ColdStartTaskNotFoundError(task_id=str(task_id))
        return t

    async def list_by_project(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        user_id: UUID,
        limit: int = 20,
    ) -> list[ColdStartTask]:
        return list(await self.dao.list_by_project(db, project_id, user_id, limit=limit))

    async def process_csv(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        content_bytes: bytes,
        source_filename: str,
    ) -> ColdStartTask:
        """Orchestrator 主入口。状态机 pending → validating → importing → completed/failed。

        异常契约（不 catch-all 静默吞错；M07 R1-C P1-01 范式延续）：
        - ColdStartFileTooLargeError：大小超阈值（解析前）
        - ColdStartCsvInvalidError：CSV 格式 / 缺列（解析失败）
        - ColdStartRowValidationFailedError：行级校验失败（task.error_report 写入）
        - ColdStartBatchInsertFailedError：4 service.batch_create 任一抛异常（savepoint 回滚）
        """
        # ---- 大小检查（解析前 / 走 helper / cross-sprint #8 立修） ----
        _check_csv_size_or_raise(content_bytes)

        source_hash = hashlib.sha256(content_bytes).hexdigest()

        # ---- 创建 task 记录（pending） ----
        task = ColdStartTask(
            project_id=project_id,
            user_id=actor_user_id,
            source_hash=source_hash,
            source_filename=source_filename,
            status=ColdStartStatus.PENDING.value,
        )
        await self.dao.create(db, task)

        # R10-1: 创建事件
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="cold_start_created",
            target_type="cold_start_task",
            target_id=str(task.id),
            summary="创建了冷启动导入任务",
            metadata={
                "source_hash": source_hash,
                "source_filename": source_filename,
            },
        )

        # ★ 任务创建立即 commit（M17 sprint 子片 0 prep 重构 2026-05-09）
        # 让 task 行脱离批量入库事务，失败补偿走独立 connection 时能看到。
        await db.commit()

        # ---- validating：解析 + 行校验 ----
        await self.dao.update(
            db, task.id, project_id, fields={"status": ColdStartStatus.VALIDATING.value}
        )
        try:
            parsed = parse_csv(content_bytes)
        except (ColdStartCsvInvalidError, ColdStartFileTooLargeError) as e:
            await self._mark_failed(
                task,
                project_id,
                actor_user_id,
                stage="parse",
                error_code=e.code.value,
                error_report=[{"row": 0, "field": "_parse", "message": str(e.message)}],
                total_rows=0,
                failed_rows=0,
            )
            raise

        # R1-A P1-03 立修（M11 sprint，2026-05-08）：dimension 字段当前 sprint 未实装
        # 真注入路径（ProjectDimensionConfig.dim_key → dimension_type_id 解析），不可静默
        # 跳过完成 — 否则 R-X1 orchestrator 完整性契约破坏（用户认为成功但数据缺失）。
        # dim 实装后删本段 + service §6 启用 DimensionService.batch_create_in_transaction。
        if parsed.dimensions_pending:
            err_rows = [
                {
                    "row": d["row"],
                    "field": "dimension_key",
                    "message": (
                        "dimension columns not yet supported in current M11 sprint; "
                        "remove dimension_key/dimension_content columns and retry"
                    ),
                }
                for d in parsed.dimensions_pending
            ]
            await self._mark_failed(
                task,
                project_id,
                actor_user_id,
                stage="parse",
                error_code="cold_start_csv_invalid",
                error_report=err_rows,
                total_rows=parsed.total_rows,
                failed_rows=len(err_rows),
            )
            raise ColdStartCsvInvalidError(
                reason="dimension_key/dimension_content not yet implemented",
                dimension_rows=len(parsed.dimensions_pending),
            )

        if parsed.errors:
            await self._mark_failed(
                task,
                project_id,
                actor_user_id,
                stage="validate",
                error_code="cold_start_row_validation_failed",
                error_report=parsed.errors,
                total_rows=parsed.total_rows,
                failed_rows=len(parsed.errors),
            )
            raise ColdStartRowValidationFailedError(
                failed_rows=len(parsed.errors), total_rows=parsed.total_rows
            )

        # ---- importing：4 batch_create 共享 savepoint ----
        await self.dao.update(
            db,
            task.id,
            project_id,
            fields={
                "status": ColdStartStatus.IMPORTING.value,
                "total_rows": parsed.total_rows,
            },
        )

        try:
            created_nodes = await self.node_service.batch_create_in_transaction(
                db,
                project_id=project_id,
                actor_user_id=actor_user_id,
                nodes_data=parsed.nodes_data,
            )
            # temp_id → real id 映射（NodeService 内部已 raise NodeParentNotFoundError 兜底）
            temp_to_real: dict[str, UUID] = {}
            for raw, real in zip(parsed.nodes_data, created_nodes, strict=True):
                if "temp_id" in raw:
                    temp_to_real[raw["temp_id"]] = real.id

            # dimension_records：M11 sprint 不实装；parse 阶段已抛 CsvInvalid 不会到这（见上方立修）。
            # 等 ProjectDimensionConfig.dim_key → dimension_type_id 解析路径建好后 plug-in
            # DimensionService.batch_create_in_transaction（design §6 列出）。

            if parsed.competitors_data:
                await self.competitor_service.batch_create_in_transaction(
                    db,
                    project_id=project_id,
                    actor_user_id=actor_user_id,
                    competitors_data=parsed.competitors_data,
                )

            if parsed.issues_pending:
                issues_data = [
                    {
                        "category": i["category"],
                        "title": i["title"],
                        "description": i["description"],
                        "node_id": temp_to_real.get(i["node_temp_id"]),
                    }
                    for i in parsed.issues_pending
                ]
                await self.issue_service.batch_create_in_transaction(
                    db,
                    project_id=project_id,
                    actor_user_id=actor_user_id,
                    issues_data=issues_data,
                )
        except Exception as e:
            # 业务事务由 router 异常分支 rollback；service 抛之前先把 task=FAILED 通过
            # 独立 connection（compensation_session）落盘，让 outer rollback 仍保留任务
            # 最终状态。
            await self._mark_failed(
                task,
                project_id,
                actor_user_id,
                stage="import",
                error_code="cold_start_batch_insert_failed",
                error_report=[
                    {
                        "row": 0,
                        "field": "_batch",
                        "message": f"{type(e).__name__}: {e!s}",
                    }
                ],
                total_rows=parsed.total_rows,
                failed_rows=parsed.total_rows,
            )
            raise ColdStartBatchInsertFailedError(reason=str(e)) from e

        # ---- completed ----
        completed_at = datetime.now(UTC)
        await self.dao.update(
            db,
            task.id,
            project_id,
            fields={
                "status": ColdStartStatus.COMPLETED.value,
                "success_rows": parsed.total_rows,
                "completed_at": completed_at,
            },
        )
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="cold_start_completed",
            target_type="cold_start_task",
            target_id=str(task.id),
            summary="冷启动导入完成",
            metadata={
                "total_rows": parsed.total_rows,
                "nodes_created": len(parsed.nodes_data),
                "dimensions_created": 0,  # M11 sprint dim 未实装；parse 阶段已拦截
                "competitors_created": len(parsed.competitors_data),
                "issues_created": len(parsed.issues_pending),
            },
        )
        await db.refresh(task)
        return task

    async def _mark_failed(
        self,
        task: ColdStartTask,
        project_id: UUID,
        actor_user_id: UUID,
        *,
        stage: str,
        error_code: str,
        error_report: list[dict[str, Any]],
        total_rows: int,
        failed_rows: int,
    ) -> None:
        """task 元数据落盘 + activity_log 失败事件（R-X1 失败补偿 commit boundary）。

        立规来源（M17 sprint 子片 0 prep 重构 2026-05-09）：feedback_rx1_orchestrator_design L1
        + design/00-architecture/06-design-principles.md 清单 6（commit boundary 隔离）。

        - 走 compensation_session() 独立 connection；与 caller request-scope db 隔离
        - comp_db.commit() 立即可见；caller 可继续 rollback 业务事务而不影响补偿写入
        - write_event 抛异常不遮盖 task 状态落盘（R1-A P1-04 + R1-C P1-01 立修保留）

        前置契约：caller 必须保证 task 行已 commit 到 DB（process_csv 在 dao.create 后立即
        await db.commit()），否则 comp_db 这个独立 connection 看不到任务。
        """
        async with compensation_session() as comp_db:
            await self.dao.update(
                comp_db,
                task.id,
                project_id,
                fields={
                    "status": ColdStartStatus.FAILED.value,
                    "total_rows": total_rows,
                    "failed_rows": failed_rows,
                    "error_report": error_report,
                },
            )
            try:
                await write_event(
                    db=comp_db,
                    actor_user_id=actor_user_id,
                    project_id=project_id,
                    action_type="cold_start_failed",
                    target_type="cold_start_task",
                    target_id=str(task.id),
                    summary="冷启动导入失败",
                    metadata={
                        "stage": stage,
                        "failed_rows": failed_rows,
                        "error_code": error_code,
                    },
                )
            except Exception as log_err:
                # activity_log 失败降级 log；不让它遮盖原始异常 chain
                log.warning(
                    "cold_start._mark_failed.write_event_failed",
                    task_id=str(task.id),
                    error_code=error_code,
                    log_error=str(log_err),
                )
            await comp_db.commit()


__all__ = [
    "ColdStartOrchestratorService",
    "ParsedCsv",
    "parse_csv",
    "MAX_FILE_BYTES",
    "MAX_ROWS",
]
