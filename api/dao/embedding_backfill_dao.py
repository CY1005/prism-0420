"""本 DAO 适用 ADR-003 规则 4：embedding/索引专用豁免。

M18 EmbeddingBackfillDAO — design/02-modules/M18-semantic-search/00-design.md §9 规则 4 全文。

规则 4 豁免条件（设计字面 §9 line 706-718）：
  1. 模块定位是"为业务表生成派生索引数据"（embedding / 全文索引 / 物化统计）
  2. 仅 backfill 路径走规则 4（增量单条 / search 关键词路径仍走规则 1）
  3. 批量回填性能要求使规则 1 不可行（5 万条调 5 万次 Service 接口 ≥ 1h）
  4. 仅做只读 SELECT（含 LEFT JOIN），禁止 UPDATE/DELETE

豁免内容：
  - 只读 import M03/M04/M06/M07 model（Node / DimensionRecord / Competitor / Issue）
  - 跑 LEFT JOIN embeddings WHERE project_id = :pid AND embeddings.target_id IS NULL
  - 严禁在本 DAO 中 INSERT/UPDATE/DELETE 上游表

与规则 1（增量 worker 调上游 Service）的区别：
  - 规则 1：EmbeddingService.embed_single → 调 NodeService/IssueService 等 get_for_embedding
  - 规则 4：本 DAO 直接 LEFT JOIN 批量扫差异，不走 Service 层

与规则 2（DB 层聚合计算）的区别：
  - 规则 2：M10 完善度 GROUP BY/aggregate
  - 规则 4：M18 backfill LEFT JOIN 找差异（不重叠）

参考设计示例：design §9 line 730-763（list_pending_node_ids 示例 SQL）。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ADR-003 规则 4 豁免：只读 import 上游 M03/M04/M06/M07 model
# 严禁在本 DAO 中 INSERT/UPDATE/DELETE 这些表
from api.models.competitor import Competitor  # M06
from api.models.dimension_record import DimensionRecord  # M04
from api.models.embedding import Embedding
from api.models.issue import Issue  # M07
from api.models.node import Node  # M03


class EmbeddingBackfillDAO:
    """ADR-003 规则 4 豁免 DAO：只读 import M03/M04/M06/M07 + LEFT JOIN 找 backfill 差异。

    所有方法：
    - ADR-003 规则 4 豁免 / 只读 import + LEFT JOIN / batch backfill 派生数据
    - 强 tenant 过滤：project_id 必填
    - 返回需要 backfill 的 id 列表（service 层逐条 enqueue）
    """

    # ─────────── Node（M03）───────────

    async def list_pending_node_ids(
        self,
        db: AsyncSession,
        project_id: UUID,
        provider: str,
        model_name: str,
        model_version: str,
        batch_size: int = 100,
    ) -> list[UUID]:
        """ADR-003 规则 4 豁免 / 只读 import + LEFT JOIN / batch backfill 派生数据。

        SELECT n.id FROM nodes n
        LEFT JOIN embeddings e ON e.target_type='node' AND e.target_id=n.id
            AND e.provider=:p AND e.model_name=:mn AND e.model_version=:mv
            AND e.project_id=:pid
        WHERE n.project_id=:pid AND e.target_id IS NULL
        LIMIT batch_size

        (design §9 line 730-749 示例字面)
        """
        # ADR-003 规则 4 豁免 / 只读 import + LEFT JOIN / batch backfill 派生数据
        stmt = (
            select(Node.id)
            .outerjoin(
                Embedding,
                (Embedding.target_type == "node")
                & (Embedding.target_id == Node.id)
                & (Embedding.project_id == project_id)
                & (Embedding.provider == provider)
                & (Embedding.model_name == model_name)
                & (Embedding.model_version == model_version),
            )
            .where(
                Node.project_id == project_id,
                Embedding.target_id.is_(None),
            )
            .limit(batch_size)
        )
        result = await db.execute(stmt)
        return [row[0] for row in result.fetchall()]

    # ─────────── DimensionRecord（M04）───────────

    async def list_pending_dimension_record_ids(
        self,
        db: AsyncSession,
        project_id: UUID,
        provider: str,
        model_name: str,
        model_version: str,
        batch_size: int = 100,
    ) -> list[UUID]:
        """ADR-003 规则 4 豁免 / 只读 import + LEFT JOIN / batch backfill 派生数据。

        找出 dimension_records 表有但 embeddings 表无对应行的 id（按 project + provider 三段）。
        """
        # ADR-003 规则 4 豁免 / 只读 import + LEFT JOIN / batch backfill 派生数据
        stmt = (
            select(DimensionRecord.id)
            .outerjoin(
                Embedding,
                (Embedding.target_type == "dimension_record")
                & (Embedding.target_id == DimensionRecord.id)
                & (Embedding.project_id == project_id)
                & (Embedding.provider == provider)
                & (Embedding.model_name == model_name)
                & (Embedding.model_version == model_version),
            )
            .where(
                DimensionRecord.project_id == project_id,
                Embedding.target_id.is_(None),
            )
            .limit(batch_size)
        )
        result = await db.execute(stmt)
        return [row[0] for row in result.fetchall()]

    # ─────────── Competitor（M06）───────────

    async def list_pending_competitor_ids(
        self,
        db: AsyncSession,
        project_id: UUID,
        provider: str,
        model_name: str,
        model_version: str,
        batch_size: int = 100,
    ) -> list[UUID]:
        """ADR-003 规则 4 豁免 / 只读 import + LEFT JOIN / batch backfill 派生数据。

        找出 competitors 表有但 embeddings 表无对应行的 id（按 project + provider 三段）。
        """
        # ADR-003 规则 4 豁免 / 只读 import + LEFT JOIN / batch backfill 派生数据
        stmt = (
            select(Competitor.id)
            .outerjoin(
                Embedding,
                (Embedding.target_type == "competitor")
                & (Embedding.target_id == Competitor.id)
                & (Embedding.project_id == project_id)
                & (Embedding.provider == provider)
                & (Embedding.model_name == model_name)
                & (Embedding.model_version == model_version),
            )
            .where(
                Competitor.project_id == project_id,
                Embedding.target_id.is_(None),
            )
            .limit(batch_size)
        )
        result = await db.execute(stmt)
        return [row[0] for row in result.fetchall()]

    # ─────────── Issue（M07）───────────

    async def list_pending_issue_ids(
        self,
        db: AsyncSession,
        project_id: UUID,
        provider: str,
        model_name: str,
        model_version: str,
        batch_size: int = 100,
    ) -> list[UUID]:
        """ADR-003 规则 4 豁免 / 只读 import + LEFT JOIN / batch backfill 派生数据。

        找出 issues 表有但 embeddings 表无对应行的 id（按 project + provider 三段）。
        """
        # ADR-003 规则 4 豁免 / 只读 import + LEFT JOIN / batch backfill 派生数据
        stmt = (
            select(Issue.id)
            .outerjoin(
                Embedding,
                (Embedding.target_type == "issue")
                & (Embedding.target_id == Issue.id)
                & (Embedding.project_id == project_id)
                & (Embedding.provider == provider)
                & (Embedding.model_name == model_name)
                & (Embedding.model_version == model_version),
            )
            .where(
                Issue.project_id == project_id,
                Embedding.target_id.is_(None),
            )
            .limit(batch_size)
        )
        result = await db.execute(stmt)
        return [row[0] for row in result.fetchall()]


__all__ = ["EmbeddingBackfillDAO"]
