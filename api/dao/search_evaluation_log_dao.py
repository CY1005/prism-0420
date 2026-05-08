"""M18 SearchEvaluationLogDAO (sync) — design/02-modules/M18-semantic-search/00-design.md §10.

R-X3 精神：DAO 接受外部 session，不自 commit / 不自 begin。
事务由 Service 层（SearchService 1% 采样路径）控制。

⚠️ 不强 tenant 过滤——design §10 line 825 R10-2 例外：
  search_evaluation_log 是 1% 采样诊断数据（系统行为 / 非用户业务 CRUD），
  find_by_project 按 project_id 查即可（诊断用途，无跨租户安全边界），
  不强制"跨 project 返 None"的 tenant 过滤语义。

保留策略：1 年保留（评估目的），delete_old cron 清理。

尊重红线：
- DAO 不调 service 层
- DAO 不写 activity_log（search 操作不写 M15 activity_log，见 §10 字面）
- IntegrityError 不在 DAO 层处理
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.embedding import SearchEvaluationLog


class SearchEvaluationLogDAO:
    """M18 search_evaluation_log 表 DAO（1% 采样诊断 / R10-2 例外 / 不强 tenant 过滤）。

    design §10 R10-2 例外推论：系统行为 = search 路由 1% 采样写入，非用户业务 CRUD；
    三条件全满足（仅服务 M18 诊断 / 高频 / 系统级）→ 写自有表。
    """

    # ─────────── 写（caller 事务内）───────────

    async def record(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        user_id: UUID,
        query: str,
        keyword_top5: list[dict[str, Any]],
        semantic_top5: list[dict[str, Any]],
        hybrid_top5: list[dict[str, Any]],
        rrf_k: int,
        similarity_threshold: float,
    ) -> SearchEvaluationLog:
        """写入一条 1% 采样的搜索评估日志。

        字段对齐 SearchEvaluationLog 模型（design §3 line 432-462）：
        - query / keyword_top5 / semantic_top5 / hybrid_top5 / rrf_k / similarity_threshold
        - user_clicked_target_type / user_clicked_target_id 由后续点击事件更新（此处不填）
        """
        log = SearchEvaluationLog(
            project_id=project_id,
            user_id=user_id,
            query=query,
            keyword_top5=keyword_top5,
            semantic_top5=semantic_top5,
            hybrid_top5=hybrid_top5,
            rrf_k=rrf_k,
            similarity_threshold=similarity_threshold,
        )
        db.add(log)
        await db.flush()
        await db.refresh(log)
        return log

    # ─────────── 读 ───────────

    async def find_by_project(
        self,
        db: AsyncSession,
        project_id: UUID,
        limit: int = 100,
    ) -> list[SearchEvaluationLog]:
        """按 project 查最近 N 条采样日志（sampled_at desc）。

        ⚠️ 不强 tenant 过滤——诊断查询（design §10 R10-2 例外）。
        """
        result = await db.execute(
            select(SearchEvaluationLog)
            .where(SearchEvaluationLog.project_id == project_id)
            .order_by(SearchEvaluationLog.sampled_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_old(
        self,
        db: AsyncSession,
        days: int = 365,
    ) -> int:
        """cleanup cron 用：物理删除 sampled_at < NOW() - days 的旧采样日志。

        保留策略：1 年保留（评估目的），cron 清理（design §3 line 432 + §10）。
        返回删除行数。
        """
        threshold = datetime.now(UTC) - timedelta(days=days)
        result = await db.execute(
            sa_delete(SearchEvaluationLog).where(SearchEvaluationLog.sampled_at < threshold)
        )
        return result.rowcount or 0


__all__ = ["SearchEvaluationLogDAO"]
