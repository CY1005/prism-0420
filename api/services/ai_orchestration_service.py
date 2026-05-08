"""M17 AI 编排 service — 3 步 AI 流水线（design §6 + §12）。

3 步合并（Q2 选 C 字面）：
- step 1：拆分 + 归类（结构识别 / 输出 proposed_nodes）
- step 2：提取 + 补全（输出 proposed_dimensions / proposed_competitors / proposed_issues）
- step 3：关联 + 去重 + 差异标注（用户 confirm 后跑 / 仅整理 confirmed_data 不再调 LLM）

M17 sprint 范围：
- step 1 + step 2 真调 LLM（走 api.services.ai 既有 provider/registry，与 M13/M16 同源）
- step 3 不调 LLM（confirmed_data 由用户 review 后落地，service 层做 schema 校验 + 去重）
- LLM 输出 parse 失败 → ImportAIProviderError（service 层 wrap）

design §13 错误映射：
- ProviderConfigError → ImportAIProviderError 503（reason=missing_api_key/...）
- ProviderTimeoutError → ImportAIProviderError 503（reason=timeout）
- ProviderError → ImportAIProviderError 503（瞬时网络/5xx）
- ImportQuotaExceededError 单独抛（rate_limited）

prompt 风格延续 M13 analyze_prompts + M16 ai_snapshot_prompts（system_context + user_prompt）；
M17 sprint scaffold：prompt 字面在本文件内（后续 sprint 可抽 import_prompts.py 与 M13/M16 对齐）。
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from api.errors.exceptions import (
    ImportAIProviderError,
    ImportQuotaExceededError,
)
from api.services.ai.provider import (
    LLMProvider,
    ProviderConfigError,
    ProviderError,
    ProviderTimeoutError,
)
from api.services.ai.registry import get_provider

log = logging.getLogger(__name__)

_AI_TIMEOUT_SECONDS = 600  # 10min（与 design §12 retry 策略一致——单步上限）


# ─────────────── prompt 模板（M17 sprint 内联；后续可抽到 import_prompts.py）───────────────


_STEP1_SYSTEM = (
    "You are a knowledge-base structuring assistant. Given a list of file paths and "
    "their first lines, propose a hierarchical node tree (folder/leaf) that captures "
    'the implicit structure. Output strict JSON: {"nodes": [{"proposed_id": uuid, '
    '"name": str, "type": "folder"|"leaf", "parent_proposed_id": uuid|null, '
    '"confidence": 0..1}]}.'
)

_STEP2_SYSTEM = (
    "You are a content extraction assistant. Given proposed nodes and source content, "
    "extract dimension records (per node), competitors (project-level), and issues. "
    'Output strict JSON: {"dimensions": [...], "competitors": [...], "issues": [...]}.'
)


# ─────────────── service ───────────────


class AIOrchestrationService:
    """M17 AI 编排 — 把 import_task_items + AI provider 串起来。

    与 ImportService 区分：
    - ImportService：状态机扭转 / DAO / 跨模块 batch_insert orchestration
    - AIOrchestrationService：纯 LLM 调用 + JSON parse + 错误 wrap（无 DB 写入）
    """

    def __init__(self) -> None:
        pass

    async def run_step1(
        self,
        *,
        provider: LLMProvider,
        items_summary: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """步骤 1：传 items 摘要给 LLM → proposed_nodes。

        Args:
            provider: 已构建的 LLMProvider 实例（与 M13/M16 共享 registry.get_provider）
            items_summary: [{file_path, file_size, head_chars}] 形式

        Returns: {"proposed_nodes": [...]}（JSON parse 后的 review_data 子结构）
        """
        user_prompt = json.dumps(
            {"items": items_summary, "task": "structure_only"}, ensure_ascii=False
        )
        text = await self._collect(provider, _STEP1_SYSTEM, user_prompt)
        return self._parse_json(text, expected_key="nodes")

    async def run_step2(
        self,
        *,
        provider: LLMProvider,
        proposed_nodes: list[dict[str, Any]],
        items_summary: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """步骤 2：传 step1 结果 + 完整内容给 LLM → proposed_dimensions/competitors/issues。"""
        user_prompt = json.dumps(
            {"nodes": proposed_nodes, "items": items_summary, "task": "extract_and_fill"},
            ensure_ascii=False,
        )
        text = await self._collect(provider, _STEP2_SYSTEM, user_prompt)
        parsed = self._parse_json(text, expected_keys=("dimensions", "competitors", "issues"))
        return parsed

    @staticmethod
    def consolidate_step3(
        confirmed: dict[str, Any],
    ) -> dict[str, Any]:
        """步骤 3：不调 LLM——confirmed_data 内做去重 + 关联检查。

        M17 sprint 范围：
        - skipped=True 的 nodes 从下游 dimensions/issues 引用中剔除
        - 同 (target_proposed_node_id, dimension_type_key) 二元组 dedupe（保留首条）
        - issues 去重以 (target_proposed_node_id, title) 二元组
        - 不引入 LLM 调用（避免 token 浪费 + 业务上 confirmed_data 已是用户最终决策）
        """
        nodes = confirmed.get("nodes", [])
        skipped_ids = {n["proposed_id"] for n in nodes if n.get("skipped")}
        skipped_ids.update(confirmed.get("skip_proposed_ids", []))
        # R1-C P1-04 立修：提前构造 skipped_str set，避免每条 dim/issue 重建 O(k) 集合
        skipped_str = {str(s) for s in skipped_ids}

        # dimensions 去重 + 跳过 skipped 节点
        seen_dim: set[tuple[str, str]] = set()
        dims_out: list[dict[str, Any]] = []
        for d in confirmed.get("dimensions", []):
            tn = str(d["target_proposed_node_id"])
            if tn in skipped_str:
                continue
            k = (tn, d["dimension_type_key"])
            if k in seen_dim:
                continue
            seen_dim.add(k)
            dims_out.append(d)

        # issues 去重 + 跳过 skipped 节点
        seen_issue: set[tuple[str, str]] = set()
        issues_out: list[dict[str, Any]] = []
        for i in confirmed.get("issues", []):
            tn = str(i.get("target_proposed_node_id") or "")
            if tn and tn in skipped_str:
                continue
            k = (tn, i["title"])
            if k in seen_issue:
                continue
            seen_issue.add(k)
            issues_out.append(i)

        # competitors 项目级去重（display_name）
        seen_comp: set[str] = set()
        comps_out: list[dict[str, Any]] = []
        for c in confirmed.get("competitors", []):
            n = c["display_name"].strip().lower()
            if n in seen_comp:
                continue
            seen_comp.add(n)
            comps_out.append(c)

        return {
            "nodes": [n for n in nodes if not n.get("skipped")],
            "dimensions": dims_out,
            "competitors": comps_out,
            "issues": issues_out,
        }

    # ─────────────── 内部 helpers ───────────────

    @staticmethod
    async def _collect(provider: LLMProvider, system: str, prompt: str) -> str:
        """流式 collect → 完整 text；超时 / provider 异常 wrap 为 ImportAIProviderError。

        与 M13/M16 同款（aclose 协议保证；rate_limited 单独抛 ImportQuotaExceededError）。
        """
        stream = provider.analyze(prompt, context=system)
        parts: list[str] = []
        try:
            async with asyncio.timeout(_AI_TIMEOUT_SECONDS):
                async for chunk in stream:
                    parts.append(chunk)
        except TimeoutError as e:
            raise ImportAIProviderError(reason="timeout") from e
        except ProviderTimeoutError as e:
            raise ImportAIProviderError(reason=f"timeout_{e.timeout_seconds}s") from e
        except ProviderError as e:
            if e.reason == "rate_limited":
                raise ImportQuotaExceededError(provider=e.provider) from e
            raise ImportAIProviderError(provider=e.provider, reason=e.reason) from e
        finally:
            await stream.aclose()
        return "".join(parts).strip()

    @staticmethod
    def _parse_json(
        text: str,
        *,
        expected_key: str | None = None,
        expected_keys: tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as e:
            raise ImportAIProviderError(reason="parse_failed", snippet=text[:200]) from e
        if not isinstance(obj, dict):
            raise ImportAIProviderError(reason="parse_failed", snippet=text[:200])
        if expected_key is not None and expected_key not in obj:
            raise ImportAIProviderError(
                reason="parse_failed",
                missing_key=expected_key,
                snippet=text[:200],
            )
        if expected_keys is not None:
            for k in expected_keys:
                if k not in obj:
                    raise ImportAIProviderError(
                        reason="parse_failed",
                        missing_key=k,
                        snippet=text[:200],
                    )
        return obj

    @staticmethod
    def build_provider_from_project(project: Any) -> LLMProvider:
        """与 M13/M16 同款（拆字段 + AES 解密 + Registry 工厂）。

        M17 sprint：复用既有 api.services.ai.registry（mock + claude）；后续 sprint
        顺手抄 prism 补 kimi/codex/deepseek（registry.py 子片 1 范围 docstring 字面）。
        """
        from api.auth.crypto import CryptoDecryptError, decrypt

        ai_provider_name = getattr(project, "ai_provider", None)
        if not ai_provider_name:
            raise ImportAIProviderError(reason="provider_unset")
        api_key: str | None = None
        enc = getattr(project, "ai_api_key_enc", None)
        if enc:
            try:
                api_key = decrypt(enc)
            except CryptoDecryptError as e:
                raise ImportAIProviderError(reason="api_key_decrypt_failed") from e
        model = getattr(project, "ai_model", None)
        try:
            return get_provider(ai_provider_name, api_key=api_key, model=model)
        except ProviderConfigError as e:
            raise ImportAIProviderError(provider=e.provider, reason=e.reason) from e


__all__ = ["AIOrchestrationService"]
