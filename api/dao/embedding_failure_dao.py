"""M18 EmbeddingFailureDAO (sync) — design/02-modules/M18-semantic-search/00-design.md §9.

R-X3 精神：DAO 接受外部 session，不自 commit / 不自 begin。
事务由 Service 层控制（worker 调 record_failure 在 worker 事务内）。

EmbeddingFailure 是 R10-2 例外表（与 auth_audit_log 类）：
- 高频系统级事件（embedding 计算失败），不进 M15 activity_log
- 写自有 embedding_failures 表
- 保留策略：90 天后 delete_old cron 清理

关于模型字段对齐：
- EmbeddingFailure 无 failure_count 字段（每次失败插入独立行）
- retry_count 字段由 worker 设定（表示已重试次数）
- content_hash 不在 failure 表（该字段在 embeddings 表，worker 层比对）

尊重红线：
- DAO 不调 service 层
- DAO 不写 activity_log（service 层职责）
- IntegrityError 不在 DAO 层处理
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.embedding import EmbeddingFailure


class EmbeddingFailureDAO:
    """M18 embedding_failures 表 DAO（R10-2 例外表 / 监控源）。

    每次 embedding 计算失败插入一行（无 failure_count 聚合字段，聚合在 count_failures_* 查询层）。
    """

    # ─────────── 写（caller 事务内）───────────

    async def record_failure(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        target_type: str,
        target_id: UUID,
        provider: str,
        model_name: str,
        model_version: str,
        error_code: str,
        error_message: str,
        retry_count: int = 0,
    ) -> EmbeddingFailure:
        """记录一次 embedding 计算失败（插入新行）。

        每次失败插独立行；失败累计通过 count_failures_* 查询层聚合（无 failure_count 字段）。
        project_id 必填：强 tenant 归属（R10-2 例外表同遵 project_id 冗余）。
        """
        failure = EmbeddingFailure(
            project_id=project_id,
            target_type=target_type,
            target_id=target_id,
            provider=provider,
            model_name=model_name,
            model_version=model_version,
            error_code=error_code,
            error_message=error_message,
            retry_count=retry_count,
        )
        db.add(failure)
        await db.flush()
        await db.refresh(failure)
        return failure

    # ─────────── 读 ───────────

    async def find_by_target(
        self,
        db: AsyncSession,
        project_id: UUID,
        target_type: str,
        target_id: UUID,
    ) -> list[EmbeddingFailure]:
        """查指定 target 的全部失败记录（project + target 过滤）。

        强 tenant 过滤：project_id 必填（design §9）。
        """
        result = await db.execute(
            select(EmbeddingFailure)
            .where(
                EmbeddingFailure.project_id == project_id,
                EmbeddingFailure.target_type == target_type,
                EmbeddingFailure.target_id == target_id,
            )
            .order_by(EmbeddingFailure.failed_at.desc())
        )
        return list(result.scalars().all())

    async def count_failures_in_window(
        self,
        db: AsyncSession,
        hours: int,
    ) -> int:
        """monitor cron 全局阈值告警用：hours 内全局失败数。

        全局查询（无 project_id 过滤）——design §9 Failure 监控扫描字面：
        `count_in_window(window_minutes, project_id=None)`。
        对应 env: EMBEDDING_FAILURE_THRESHOLD_ABS（500）触发告警。
        """
        threshold = datetime.now(UTC) - timedelta(hours=hours)
        result = await db.execute(
            select(func.count())
            .where(EmbeddingFailure.failed_at >= threshold)
            .select_from(EmbeddingFailure)
        )
        return result.scalar_one() or 0

    async def count_failures_by_project_in_window(
        self,
        db: AsyncSession,
        project_id: UUID,
        hours: int,
    ) -> int:
        """PER_PROJECT 维度阈值告警用：hours 内指定 project 失败数。

        对应 env: EMBEDDING_FAILURE_THRESHOLD_PER_PROJECT（100）触发告警。
        project_id 必填：强 tenant 过滤。
        """
        threshold = datetime.now(UTC) - timedelta(hours=hours)
        result = await db.execute(
            select(func.count())
            .where(
                EmbeddingFailure.project_id == project_id,
                EmbeddingFailure.failed_at >= threshold,
            )
            .select_from(EmbeddingFailure)
        )
        return result.scalar_one() or 0

    async def delete_old(
        self,
        db: AsyncSession,
        days: int = 90,
    ) -> int:
        """90 天清理 cron 用：物理删除 failed_at < NOW() - days 的旧失败记录。

        保留策略（design §3 line 391）：90 天后删除——仅用于近期失败率监控。
        返回删除行数。
        """
        from sqlalchemy import delete as sa_delete

        threshold = datetime.now(UTC) - timedelta(days=days)
        result = await db.execute(
            sa_delete(EmbeddingFailure).where(EmbeddingFailure.failed_at < threshold)
        )
        return result.rowcount or 0


__all__ = ["EmbeddingFailureDAO"]
