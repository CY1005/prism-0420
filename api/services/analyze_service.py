"""M13 AnalyzeService — 需求分析编排层 (design §6 R3-5 纯读聚合 + 写 M04)。

职责：
  1. 流式分析（``analyze_stream``）：聚合 prompt context（M02 project + M03 node/subtree
     + M07 issues）→ AES 解密 ai_api_key_enc → ProviderRegistry.get → provider.analyze
     yield chunk；caller (Router) 包 SSE event 序列化。
  2. 保存分析（``save_analysis``）：调 ``M04.DimensionService.create_dimension_record``
     单条写入（design §10 Q6 ack A 仅 save 写 1 条 activity_log，由 M04 代写）；
     M13 自身不直写任何表。
  3. 影响节点读（``get_affected_nodes``）：拿 (project_id, node_id) 上 dimension_type_key
     ='requirement_analysis' 的最新 dimension_record + 解析 metadata.affected_node_ids
     回 caller。

异常 wrap (design §13 R13-2)：
  - NodeNotFoundError → AnalysisNodeNotFoundError 404
  - Project.ai_provider 为 None / "" → AnalysisProviderNotConfiguredError 422
  - CryptoDecryptError → AnalysisProviderNotConfiguredError 422（key 损坏 = 配置问题）
  - ProviderConfigError(reason='missing_api_key' | 'unknown_provider') →
    AnalysisProviderNotConfiguredError 422
  - ProviderTimeoutError → AnalysisTimeoutError 504
  - ProviderError(reason='rate_limited') → AnalysisQuotaExceededError 429
  - 其他 ProviderError → AnalysisProviderError 503
  - M04 create_dimension_record 失败 → AnalysisSaveFailedError 500（不直接 raise M04
    DimensionWriteError）

事务边界：
  - analyze_stream：纯读 + 调外部 LLM API；不开事务，不写 DB
  - save_analysis：caller (Router) 控制 db.commit；本 service 接受外部 session，
    DimensionService.create_dimension_record 也是接受外部 session 不自开事务（R-X3）
  - get_affected_nodes：纯读

dimension_type_key 常量 ``REQUIREMENT_ANALYSIS_KEY``：design line 175-177 字面，
首次 save_analysis 调用时 M04 自动 upsert dimension_types 行（accepted 同期补丁 #1）。
"""

from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.crypto import CryptoDecryptError, decrypt
from api.errors.exceptions import (
    AnalysisNodeNotFoundError,
    AnalysisProviderError,
    AnalysisProviderNotConfiguredError,
    AnalysisQuotaExceededError,
    AnalysisSaveFailedError,
    AnalysisTimeoutError,
    ConflictError,
    DimensionDuplicateError,
    DimensionNotFoundError,
    NodeNotFoundError,
)
from api.models.dimension_record import DimensionRecord
from api.models.node import Node
from api.schemas.analyze_schema import AnalysisLevel
from api.services.ai import (
    LLMProvider,
    ProviderConfigError,
    ProviderError,
    ProviderTimeoutError,
    get_provider,
)
from api.services.analyze_prompts import IssueBrief, NodeBrief, build_prompt
from api.services.dimension_service import DimensionService
from api.services.issue_service import IssueService
from api.services.node_service import NodeService
from api.services.project_service import ProjectService

REQUIREMENT_ANALYSIS_KEY = "requirement_analysis"

# 子树最大深度（design §2 ≤2 层；本 service 内联过滤 list_tree 实现，避免新增上游接口）
_SUBTREE_MAX_DEPTH = 2


@dataclass(frozen=True)
class AffectedNodesResult:
    """get_affected_nodes 返回结构（子片 3 Pydantic 化）。"""

    node_id: UUID
    affected_node_ids: list[UUID]
    analysis_record_id: UUID | None
    # R1-C P1-03 立修：与 AffectedNodesResponse.analysis_saved_at 类型一致 (datetime)；
    # router 序列化交给 Pydantic/FastAPI（避免 service 层提前 isoformat 导致漂移）
    analysis_saved_at: datetime | None


class AnalyzeService:
    """M13 编排服务（无自有 DAO / model）。"""

    def __init__(
        self,
        project_service: ProjectService | None = None,
        node_service: NodeService | None = None,
        issue_service: IssueService | None = None,
        dimension_service: DimensionService | None = None,
    ) -> None:
        self.projects = project_service or ProjectService()
        self.nodes = node_service or NodeService()
        self.issues = issue_service or IssueService()
        self.dimensions = dimension_service or DimensionService()

    # ─── 流式分析 ───

    async def analyze_stream(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        user_id: UUID,
        requirement_text: str,
        level: AnalysisLevel,
    ) -> AsyncIterator[str]:
        """yield LLM 流式 chunk；caller (Router) 包 SSE event 序列化 + is_disconnected 检测。

        异常路径完全 wrap 为 Analysis* 错误（design §13 R13-2）；wrap 在拿 stream 前完成
        （配置错 / 解密错 / 上下文聚合错），stream 内异常在 caller 迭代时浮现并被 wrap。
        """
        # ① 校验 project access + 拿 ai_provider/api_key/model 字段
        project = await self.projects.get_for_user(db, project_id, user_id)
        provider = self._build_provider_from_project(project)

        # ② + ③ 校验 node + 聚合 prompt context（R1-A P1-2 立修：把 _fetch_node_context
        # / _fetch_issue_context 包进同一 try，里面 NodeService.breadcrumb 在 race 下会
        # 抛 NodeNotFoundError——必须 wrap 为 AnalysisNodeNotFoundError 404 不裸泄漏）
        try:
            target = await self.nodes.get_node(db, node_id, project_id)
            breadcrumb_nodes, subtree_nodes = await self._fetch_node_context(
                db, project_id=project_id, target_node=target
            )
            issue_briefs = await self._fetch_issue_context(
                db, project_id=project_id, node_id=node_id
            )
        except NodeNotFoundError as e:
            raise AnalysisNodeNotFoundError(node_id=str(node_id)) from e

        target_brief = NodeBrief(id=target.id, name=target.name, description=target.description)
        breadcrumb_briefs = [
            NodeBrief(id=n.id, name=n.name, description=n.description) for n in breadcrumb_nodes
        ]

        system_context, user_prompt = build_prompt(
            project_name=project.name,
            target_node=target_brief,
            breadcrumb=breadcrumb_briefs,
            subtree=subtree_nodes,
            issues=issue_briefs,
            requirement_text=requirement_text,
            level=level,
        )

        # ④ 调 provider 流式；异常逐项 wrap + R1-C P1-01 立修：finally aclose 释放底层资源
        # （PEP 533；caller 主动 aclose AnalyzeService 返回的 generator 时，把 GeneratorExit
        # 传播到 inner stream 才能让 ClaudeProvider 嵌套 async with httpx 真释放）
        stream = provider.analyze(user_prompt, context=system_context)
        try:
            async for chunk in stream:
                yield chunk
        except ProviderTimeoutError as e:
            raise AnalysisTimeoutError() from e
        except ProviderError as e:
            raise self._wrap_provider_error(e) from e
        finally:
            await stream.aclose()

    # ─── 保存分析 ───

    async def save_analysis(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        user_id: UUID,
        analysis_result: str,
        requirement_text: str,
        level: AnalysisLevel,
        ai_provider: str,
        ai_model: str,
        analysis_time_ms: int,
        affected_node_ids: list[UUID] | None = None,
    ) -> DimensionRecord:
        """单条写入 dimension_records；R-X3 共享外部 db session。

        M13 不直写 activity_log——交给 M04.create_dimension_record 在同事务内代写
        （design §10 Q6 ack A）。
        """
        # 校验 project access（防越权写）
        await self.projects.get_for_user(db, project_id, user_id)

        affected_ids = affected_node_ids or []
        # R1-A P1-1 立修：design §10 line 559 字面要求 metadata 含 requirement_text_hash
        # （SHA256 锚点 — 留审计回溯但不存明文；未来按 hash 反查"这条分析对应什么需求"）
        text_hash = hashlib.sha256(requirement_text.encode("utf-8")).hexdigest()
        content = {
            "requirement_text": requirement_text,
            "analysis_result": analysis_result,
            "analysis_level": level.value,
            "affected_node_ids": [str(x) for x in affected_ids],
        }
        extra_metadata = {
            "ai_provider": ai_provider,
            "ai_model": ai_model,
            "analysis_level": level.value,
            "analysis_time_ms": analysis_time_ms,
            "affected_node_count": len(affected_ids),
            "requirement_text_hash": text_hash,
            "requirement_text_length": len(requirement_text),
        }

        try:
            rec = await self.dimensions.create_dimension_record(
                db,
                project_id=project_id,
                node_id=node_id,
                dimension_type_key=REQUIREMENT_ANALYSIS_KEY,
                content=content,
                user_id=user_id,
                extra_activity_metadata=extra_metadata,
            )
        except (NodeNotFoundError, DimensionNotFoundError) as e:
            # M04 _check_node_belongs_to_project 抛 DimensionNotFoundError(reason=node_not_in_project)；
            # NodeService.get_node 抛 NodeNotFoundError——两者都 → 404 AnalysisNodeNotFoundError
            raise AnalysisNodeNotFoundError(node_id=str(node_id)) from e
        except (ConflictError, DimensionDuplicateError):
            # R1-A P1-5 立修：M04 显式语义错（乐观锁冲突 / 同 node+type 重复）应保留 409，
            # 不吞成 SaveFailed 500（M05 P1-01 元教训延续——区分 race 类错和真正写失败）
            raise
        except Exception as e:
            # 其他真"写失败"（IntegrityError 非约束 / write_event 异常 / 等）→ wrap 500
            # 不吞错——异常对象保留 in __cause__ 供 logging
            raise AnalysisSaveFailedError() from e
        return rec

    # ─── 影响节点读 ───

    async def get_affected_nodes(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        user_id: UUID,
    ) -> AffectedNodesResult:
        """读 (project_id, node_id) 上最新一条 requirement_analysis 记录的 affected_node_ids。

        无历史分析 → analysis_record_id=None / affected_node_ids=[]（design line 739）。
        """
        # project access 校验
        await self.projects.get_for_user(db, project_id, user_id)
        # node 校验（不存在 → 404，与 analyze_stream 一致）
        try:
            await self.nodes.get_node(db, node_id, project_id)
        except NodeNotFoundError as e:
            raise AnalysisNodeNotFoundError(node_id=str(node_id)) from e

        rec = await self.dimensions.get_latest(
            db,
            project_id=project_id,
            node_id=node_id,
            dimension_type_key=REQUIREMENT_ANALYSIS_KEY,
        )
        if rec is None:
            return AffectedNodesResult(
                node_id=node_id,
                affected_node_ids=[],
                analysis_record_id=None,
                analysis_saved_at=None,
            )
        ids_raw = (rec.content or {}).get("affected_node_ids", [])
        affected_ids: list[UUID] = []
        for x in ids_raw:
            try:
                affected_ids.append(UUID(str(x)))
            except (ValueError, AttributeError):
                continue  # 跳过无效 UUID（不应发生，content 是本服务写入；防御）
        return AffectedNodesResult(
            node_id=node_id,
            affected_node_ids=affected_ids,
            analysis_record_id=rec.id,
            analysis_saved_at=rec.created_at,
        )

    # ─── 内部 helpers ───

    def _build_provider_from_project(self, project: Any) -> LLMProvider:
        """拆字段 + AES 解密 + Registry 工厂；异常逐项 wrap 为 Analysis*。"""
        ai_provider_name = getattr(project, "ai_provider", None)
        if not ai_provider_name:
            raise AnalysisProviderNotConfiguredError(reason="ai_provider_unset")

        api_key: str | None = None
        enc = getattr(project, "ai_api_key_enc", None)
        if enc:
            try:
                api_key = decrypt(enc)
            except CryptoDecryptError as e:
                raise AnalysisProviderNotConfiguredError(reason="api_key_decrypt_failed") from e

        model = getattr(project, "ai_model", None)
        try:
            return get_provider(ai_provider_name, api_key=api_key, model=model)
        except ProviderConfigError as e:
            raise AnalysisProviderNotConfiguredError(provider=e.provider, reason=e.reason) from e

    async def _fetch_node_context(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        target_node: Node,
    ) -> tuple[list[Node], list[NodeBrief]]:
        """返回 (breadcrumb_nodes, subtree_briefs) 二元组。

        Subtree 用 list_tree + path startswith 内联过滤实现 ≤2 层（design §2
        要求"node 路径和 2 层子树"；NodeService 暂无 list_subtree 接口，design 字面
        漂移自决：用 list_tree + path 过滤等价实现，避免新增上游接口）。
        """
        breadcrumb = await self.nodes.breadcrumb(db, target_node.id, project_id)
        all_nodes = await self.nodes.list_tree(db, project_id)
        subtree_briefs: list[NodeBrief] = []
        target_path = target_node.path or ""
        for n in all_nodes:
            if n.id == target_node.id:
                continue
            n_path = n.path or ""
            if not n_path.startswith(target_path):
                continue
            # 深度 = (n.path - target.path) 段数
            tail = n_path[len(target_path) :].strip("/")
            if not tail:
                continue
            depth = len([s for s in tail.split("/") if s])
            if depth > _SUBTREE_MAX_DEPTH:
                continue
            subtree_briefs.append(
                NodeBrief(id=n.id, name=n.name, description=n.description, depth=depth - 1)
            )
        # 稳定顺序（path 字典序）
        subtree_briefs.sort(key=lambda b: b.name)
        return list(breadcrumb), subtree_briefs

    async def _fetch_issue_context(
        self, db: AsyncSession, *, project_id: UUID, node_id: UUID
    ) -> list[IssueBrief]:
        """M07 IssueService.list_by_project pass-through（design §6 R-X3 登记）。"""
        issues = await self.issues.list_by_project(db, project_id=project_id, node_id=node_id)
        return [
            IssueBrief(id=i.id, title=i.title, category=i.category, status=i.status) for i in issues
        ]

    @staticmethod
    def _wrap_provider_error(e: ProviderError) -> Exception:
        """Provider* → Analysis* 异常映射（design §13 R13-2）。"""
        if e.reason == "rate_limited":
            return AnalysisQuotaExceededError()
        return AnalysisProviderError()
