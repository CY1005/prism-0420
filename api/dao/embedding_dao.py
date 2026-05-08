"""M18 EmbeddingDAO (sync) — design/02-modules/M18-semantic-search/00-design.md §9.

R-X3 精神：DAO 接受外部 session，不自 commit / 不自 begin。
事务由 Service 层（EmbeddingService / Queue worker）控制。

主查询模式（design §9 三类查询 tenant 处理）：
- 所有方法强制 WHERE project_id = :pid tenant 过滤（M18 自有表，无 ADR-003 规则适用）
- vector_search 占位：pgvector 未安装，子片 3 安装后回写真实 <=> 算子

尊重红线：
- DAO 不调 service 层（违反分层）
- DAO 不写 activity_log（service 层职责）
- IntegrityError 转换不在 DAO 层做（service 层职责 / 清单 6）
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.embedding import Embedding

# ── upsert SQL（PostgreSQL ON CONFLICT DO UPDATE）────────────────────────────
_UPSERT_SQL = text(
    """
    INSERT INTO embeddings (
        project_id, modality, target_type, target_id,
        provider, model_name, model_version,
        dim, embedding_512, embedding_1536, embedding_3072,
        content_hash,
        created_at, updated_at
    ) VALUES (
        :project_id, :modality, :target_type, :target_id,
        :provider, :model_name, :model_version,
        :dim, :embedding_512, :embedding_1536, :embedding_3072,
        :content_hash,
        NOW(), NOW()
    )
    ON CONFLICT (project_id, modality, target_type, target_id, provider, model_name, model_version)
    DO UPDATE SET
        dim             = EXCLUDED.dim,
        embedding_512   = EXCLUDED.embedding_512,
        embedding_1536  = EXCLUDED.embedding_1536,
        embedding_3072  = EXCLUDED.embedding_3072,
        content_hash    = EXCLUDED.content_hash,
        updated_at      = NOW()
    RETURNING *
    """
)


class EmbeddingDAO:
    """M18 embeddings 表 DAO（增量路径 / M18 自有表 / 强 tenant 过滤）。

    设计原则（design §9 line 692-702）：
    - 所有方法第一参 project_id 必填，不允许跨 project 查
    - vector_search 子片 3 占位（pgvector 未安装）
    """

    # ─────────── 读 ───────────

    async def find_by_target(
        self,
        db: AsyncSession,
        project_id: UUID,
        target_type: str,
        target_id: UUID,
        provider: str,
        model_name: str,
        model_version: str,
    ) -> Embedding | None:
        """7 字段 PK 精确查找（worker 内 content_hash 比对兜底用）。

        强 tenant 过滤：project_id 必填第一参（design §9）。
        """
        result = await db.execute(
            select(Embedding).where(
                Embedding.project_id == project_id,
                Embedding.target_type == target_type,
                Embedding.target_id == target_id,
                Embedding.provider == provider,
                Embedding.model_name == model_name,
                Embedding.model_version == model_version,
            )
        )
        return result.scalar_one_or_none()

    async def find_by_project_and_provider(
        self,
        db: AsyncSession,
        project_id: UUID,
        provider: str,
        model_name: str,
        model_version: str,
    ) -> list[Embedding]:
        """project + (provider, model_name, model_version) 三段过滤查全部 embedding 行。

        强 tenant 过滤：project_id 必填（design §9）。
        用于 admin /stats 列举 / sanity check。
        """
        result = await db.execute(
            select(Embedding).where(
                Embedding.project_id == project_id,
                Embedding.provider == provider,
                Embedding.model_name == model_name,
                Embedding.model_version == model_version,
            )
        )
        return list(result.scalars().all())

    async def vector_search(
        self,
        db: AsyncSession,
        project_id: UUID,
        query_vec: list[float],
        dim: int,
        provider: str,
        model_name: str,
        model_version: str,
        target_types: list[str] | None = None,
        limit: int = 10,
    ) -> list[tuple[Embedding, float]]:
        """pgvector cosine 距离向量搜索占位。

        ⚠️ pgvector 未安装：子片 3 安装 pgvector 后回写真实实现。
        真实实现形式（dim 路由 / design §6 SearchService 字面）：
            SELECT *, embedding_<dim> <=> :q AS distance
            FROM embeddings
            WHERE project_id = :pid
              AND provider = :p
              AND model_name = :mn
              AND model_version = :mv
              AND embedding_<dim> IS NOT NULL
              [AND target_type = ANY(:tt)]
            ORDER BY distance ASC
            LIMIT :n

        强 tenant 过滤：project_id 必填（design §9 向量路径 SQL WHERE project_id + model 过滤）。
        """
        # 子片 3 装 pgvector 后回写
        raise NotImplementedError(
            "vector_search 需要 pgvector 扩展；子片 3 安装 pgvector 后回写"
            f"（dim={dim}, provider={provider}, model_name={model_name}）"
        )

    async def delete_by_target(
        self,
        db: AsyncSession,
        project_id: UUID,
        target_type: str,
        target_id: UUID,
    ) -> int:
        """删除指定 target 的全部 (provider, model_name, model_version) embedding 行。

        用于 commit 后异步 enqueue_delete 真删（design §9 删除策略 B1 修复 = C2=A）。
        强 tenant 过滤：project_id 必填。
        返回删除行数。
        """
        result = await db.execute(
            sa_delete(Embedding).where(
                Embedding.project_id == project_id,
                Embedding.target_type == target_type,
                Embedding.target_id == target_id,
            )
        )
        return result.rowcount or 0

    async def count_by_project_and_provider(
        self,
        db: AsyncSession,
        project_id: UUID,
        provider: str,
        model_name: str,
        model_version: str,
    ) -> int:
        """admin /stats endpoint 用：project + provider 三段下 embedding 总数。

        强 tenant 过滤：project_id 必填（design §9）。
        """
        result = await db.execute(
            select(func.count())
            .where(
                Embedding.project_id == project_id,
                Embedding.provider == provider,
                Embedding.model_name == model_name,
                Embedding.model_version == model_version,
            )
            .select_from(Embedding)
        )
        return result.scalar_one() or 0

    # ─────────── 写（caller 事务内）───────────

    async def upsert_embedding(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        modality: str,
        target_type: str,
        target_id: UUID,
        provider: str,
        model_name: str,
        model_version: str,
        dim: int,
        vector: list[float],
        content_hash: str,
    ) -> Embedding:
        """ON CONFLICT DO UPDATE（7 字段 PK / PostgreSQL）。

        dim 路由到 embedding_512 / embedding_1536 / embedding_3072 列（design §3）。
        同 content_hash 幂等兜底——worker 层已在入口比对，DAO 层无重复检查（service 职责）。
        """
        embedding_512: list[float] | None = None
        embedding_1536: list[float] | None = None
        embedding_3072: list[float] | None = None

        if dim == 512:
            embedding_512 = vector
        elif dim == 1536:
            embedding_1536 = vector
        elif dim == 3072:
            embedding_3072 = vector
        else:
            raise ValueError(f"unsupported dim={dim}; allowed: 512, 1536, 3072")

        await db.execute(
            _UPSERT_SQL,
            {
                "project_id": str(project_id),
                "modality": modality,
                "target_type": target_type,
                "target_id": str(target_id),
                "provider": provider,
                "model_name": model_name,
                "model_version": model_version,
                "dim": dim,
                "embedding_512": embedding_512,
                "embedding_1536": embedding_1536,
                "embedding_3072": embedding_3072,
                "content_hash": content_hash,
            },
        )
        # re-fetch ORM object from identity map / DB after upsert
        await db.flush()
        result = await db.execute(
            select(Embedding).where(
                Embedding.project_id == project_id,
                Embedding.modality == modality,
                Embedding.target_type == target_type,
                Embedding.target_id == target_id,
                Embedding.provider == provider,
                Embedding.model_name == model_name,
                Embedding.model_version == model_version,
            )
        )
        obj = result.scalar_one_or_none()
        assert obj is not None, "upsert_embedding: row missing after UPSERT"
        return obj


__all__ = ["EmbeddingDAO"]
