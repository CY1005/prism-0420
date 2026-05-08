"""SearchService（M18 接管 M09）— design §6 line 575 / §7 line 625。

# horizontal: 否（M18 搜索专属）
# owner: M18
# 位置: api/services/（service 层）
# 范畴: hybrid_search / check_project_access / RRF 融合
"""

from __future__ import annotations

import logging
import os
import random
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.errors.exceptions import (
    EmbeddingProviderFailedError,
    EmbeddingProviderTimeoutError,
    PgvectorUnavailableError,
)
from api.schemas.search_schema import (
    EmbeddingTargetType,
    SearchResponse,
    SearchResultItem,
)

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

# ─── env 配置（design §6 line 591-606）──────────────────────────────────────

_SEARCH_MODE = os.getenv("SEARCH_MODE", "hybrid")
"""hybrid / keyword_only / semantic_only（B5 kill switch）。"""

_SEARCH_EVAL_SAMPLE_RATE = float(os.getenv("SEARCH_EVAL_SAMPLE_RATE", "0.01"))
"""search 路由 1% 采样写 search_evaluation_log（M13 离线评估）。"""

# RRF k 默认值（从 ProjectSettings 读；此处作 fallback）
_RRF_K_DEFAULT: int = 60


class SearchService:
    """M18 SearchService（接管 M09 search）。

    hybrid_search 入口读 env SEARCH_MODE：
    - hybrid：keyword path + semantic path → RRF 融合
    - keyword_only：仅 keyword path（pgvector 不可用降级）
    - semantic_only：仅 semantic path
    """

    def __init__(
        self,
        embedding_service: object | None = None,
    ) -> None:
        # 延迟 import 避免循环依赖
        if embedding_service is not None:
            self._embedding_service = embedding_service
        else:
            from api.services.embedding import EmbeddingService

            self._embedding_service = EmbeddingService()

    # ─── check_project_access（L3 Service 层权限防御）───────────────────────

    async def check_project_access(
        self,
        db: AsyncSession,
        user_id: UUID,
        project_id: UUID,
        role: str = "viewer",
    ) -> None:
        """调 M02 ProjectService 校验 project 访问权（design §8 L3）。

        TODO 子片 4+ 真接 ProjectService.check_access；当前占位（M02 ProjectService 已实装但
        本子片不依赖其签名——search 路由 router 层先行鉴权，此处 service 层二次防御）。
        """
        # TODO 接 ProjectService.check_member_role(db, user_id, project_id, role)
        # 占位：不抛则通过
        pass

    # ─── hybrid_search（主入口）─────────────────────────────────────────────

    async def hybrid_search(
        self,
        db: AsyncSession,
        query: str,
        project_id: UUID,
        user_id: UUID,
        target_types: list[EmbeddingTargetType] | None = None,
        limit: int = 20,
        rrf_k: int = _RRF_K_DEFAULT,
    ) -> SearchResponse:
        """混合搜索主入口（design §6 SearchService.hybrid_search）。

        SEARCH_MODE 三档（hybrid / keyword_only / semantic_only）。
        1% 采样写 search_evaluation_log（design §10 M13 离线评估）。
        error wrap：上游 ErrorCode 透传（audit M2 决策 / R13-2 豁免）+ metadata['from_module']。
        """
        mode = _SEARCH_MODE.lower()

        keyword_results: list[SearchResultItem] = []
        semantic_results: list[SearchResultItem] = []
        query_embedding_cached = False
        # actual_search_mode 初始值按 mode 决定
        actual_search_mode: str = "hybrid" if mode == "hybrid" else "keyword_only"

        # ─── keyword path ────────────────────────────────────────────
        if mode in ("hybrid", "keyword_only"):
            try:
                keyword_results = await self._keyword_search(
                    db, query, project_id, target_types, limit
                )
            except Exception as exc:  # noqa: BLE001
                # R13-2 豁免：透传上游 ErrorCode + 加 from_module 标记（audit M2）
                if hasattr(exc, "metadata"):
                    exc.metadata["from_module"] = "M09"  # type: ignore[attr-defined]
                log.warning("keyword_search failed: %s", exc)
                if mode == "keyword_only":
                    raise

        # ─── semantic path ───────────────────────────────────────────
        if mode in ("hybrid", "semantic_only"):
            try:
                query_vec, dim, provider, model_name, model_version = (
                    await self._embedding_service.embed_query(db, query)  # type: ignore[attr-defined]
                )
                query_embedding_cached = False  # TODO 子片 4+ 接 Redis 后真判断

                from api.dao.embedding_dao import EmbeddingDAO

                embedding_dao = EmbeddingDAO()
                # pgvector 占位：NotImplementedError → 降级 keyword_only（AC4）
                try:
                    raw_vec_results = await embedding_dao.vector_search(
                        db,
                        project_id=project_id,
                        query_vec=query_vec,
                        dim=dim,
                        provider=provider,
                        model_name=model_name,
                        model_version=model_version,
                        target_types=[t.value for t in target_types] if target_types else None,
                        limit=limit,
                    )
                    semantic_results = [
                        SearchResultItem(
                            target_type=EmbeddingTargetType(row.target_type),
                            target_id=row.target_id,
                            title=f"{row.target_type}:{row.target_id}",
                            snippet="",
                            score=1.0 - score,
                            matched_by=["semantic"],
                            breadcrumb=[],
                        )
                        for row, score in raw_vec_results
                    ]
                except NotImplementedError:
                    # pgvector 不可用 → 降级 keyword_only（PRD AC4）
                    log.info("pgvector unavailable, falling back to keyword_only")
                    raise PgvectorUnavailableError("pgvector extension not yet installed") from None

            except PgvectorUnavailableError:
                # 降级 keyword_only（AC4）— 不抛 HTTP 错误
                actual_search_mode = "keyword_only"
            except (EmbeddingProviderFailedError, EmbeddingProviderTimeoutError):
                # provider 失败 → 降级 keyword_only（不中断用户搜索）
                actual_search_mode = "keyword_only"
                log.warning("embed_query failed, fallback to keyword_only")
            except Exception as exc:  # noqa: BLE001
                actual_search_mode = "keyword_only"
                log.warning("semantic search failed: %s", exc)

        # ─── RRF 融合（hybrid 模式）──────────────────────────────────
        if mode == "hybrid" and actual_search_mode == "hybrid":
            merged = _rrf_merge(keyword_results, semantic_results, k=rrf_k, limit=limit)
        elif keyword_results:
            merged = keyword_results[:limit]
        else:
            merged = semantic_results[:limit]

        total = len(merged)

        # ─── 1% 采样写 search_evaluation_log（design §10 M13）───────
        if random.random() < _SEARCH_EVAL_SAMPLE_RATE:
            await self._write_eval_log(
                db,
                project_id=project_id,
                user_id=user_id,
                query=query,
                keyword_results=keyword_results,
                semantic_results=semantic_results,
                merged_results=merged,
                rrf_k=rrf_k,
            )

        return SearchResponse(
            results=merged,
            total=total,
            search_mode=actual_search_mode,  # type: ignore[arg-type]
            query_embedding_cached=query_embedding_cached,
        )

    # ─── keyword path（M09 已 superseded by M18 / 占位 + TODO）─────────────

    async def _keyword_search(
        self,
        db: AsyncSession,
        query: str,
        project_id: UUID,
        target_types: list[EmbeddingTargetType] | None,
        limit: int,
    ) -> list[SearchResultItem]:
        """调上游 M09 search_by_keyword（占位 / TODO：M09 已 superseded by M18）。

        实际项目可能无 M09；当前返回空列表让测试可跑。
        TODO 子片 4+ 接真实 M09/全文搜索路径。
        """
        # TODO 子片 4+：接 M09 search_by_keyword(db, query, project_id, target_types, limit)
        return []

    # ─── search_evaluation_log 1% 写入（design §10 M13）─────────────────────

    async def _write_eval_log(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        user_id: UUID,
        query: str,
        keyword_results: list[SearchResultItem],
        semantic_results: list[SearchResultItem],
        merged_results: list[SearchResultItem],
        rrf_k: int,
    ) -> None:
        """1% 采样写 search_evaluation_log（不写 M15 activity_log / R10-2 例外）。"""
        try:
            from api.models.embedding import SearchEvaluationLog

            def _items_to_dicts(items: list[SearchResultItem]) -> list[dict]:
                return [
                    {
                        "target_type": i.target_type.value,
                        "target_id": str(i.target_id),
                        "score": i.score,
                    }
                    for i in items[:5]
                ]

            log_entry = SearchEvaluationLog(
                project_id=project_id,
                user_id=user_id,
                query=query,
                keyword_top5=_items_to_dicts(keyword_results),
                semantic_top5=_items_to_dicts(semantic_results),
                hybrid_top5=_items_to_dicts(merged_results),
                rrf_k=rrf_k,
                similarity_threshold=0.0,
            )
            db.add(log_entry)
            await db.flush()
        except Exception as exc:  # noqa: BLE001
            # search_evaluation_log 写入失败不影响主路径
            log.debug("search_evaluation_log write failed (non-blocking): %s", exc)


# ─── RRF 融合工具函数────────────────────────────────────────────────────────


def _rrf_merge(
    keyword: list[SearchResultItem],
    semantic: list[SearchResultItem],
    k: int = 60,
    limit: int = 20,
) -> list[SearchResultItem]:
    """Reciprocal Rank Fusion（design §6 SearchService RRF 融合 / rrf_k 从 ProjectSettings 读）。

    RRF(d) = Σ 1 / (k + rank_i(d))
    """
    scores: dict[str, float] = {}
    items_map: dict[str, SearchResultItem] = {}

    for rank, item in enumerate(keyword, start=1):
        key = f"{item.target_type}:{item.target_id}"
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
        items_map[key] = item

    for rank, item in enumerate(semantic, start=1):
        key = f"{item.target_type}:{item.target_id}"
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
        if key not in items_map:
            items_map[key] = item
        else:
            # 合并 matched_by
            existing = items_map[key]
            merged_by = list({*existing.matched_by, *item.matched_by})
            items_map[key] = existing.model_copy(update={"matched_by": merged_by})

    sorted_keys = sorted(scores, key=lambda k: scores[k], reverse=True)
    result = []
    for key in sorted_keys[:limit]:
        item = items_map[key]
        result.append(item.model_copy(update={"score": scores[key]}))
    return result


__all__ = ["SearchService"]
