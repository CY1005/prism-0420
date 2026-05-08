"""M16 AI 快照 prompt 模板（design §6 Prompt Template 层）。

输入：AISnapshotContext (内存聚合) + dimension_keys（M04 当前 PDC 启用维度 key 清单）
输出：(system_context, user_prompt) 二元组传 LLMProvider.analyze()

模板要求 AI 严格按 dimension_keys 输出 JSON dict {summary: str, dimensions: [{key, name, content}]}。
service 解析时校验 dimensions[*].key ∈ dimension_keys 子集；缺失 key 视为 dimension content={}（而非 raise）。
"""

from __future__ import annotations

import json

from api.schemas.ai_snapshot_schema import AISnapshotContext

_SUMMARY_DIMENSION_KEY = "snapshot_summary"


def build_prompt(*, ctx: AISnapshotContext) -> tuple[str, str]:
    """构建 (system_context, user_prompt) 二元组。

    严格 JSON 输出格式：
        {
            "summary": "<一句话快照>",
            "dimensions": [
                {"key": "<dimension_type_key>", "name": "<中文展示名>", "content": {...}},
                ...
            ]
        }
    """
    system = (
        "你是一个产品 mentor，根据节点的版本演进史和当前各维度内容，输出该节点的"
        "「AI 快照」——一句话概括 + 每个维度的结构化总结。\n"
        "严格按下方 JSON schema 输出，禁止额外字段或 markdown 包裹：\n"
        '{"summary": "<一句话快照>", "dimensions": '
        '[{"key": "<dimension_type_key>", "name": "<中文名>", "content": {...}}, ...]}'
    )

    versions_block = "\n".join(
        f"- v{i + 1} ({v.version_label} @ {v.created_at.isoformat()}): "
        f"{(v.description or '')[:200]}"
        for i, v in enumerate(ctx.versions)
    )

    dims_block = "\n".join(
        f"- {d.dimension_type_key}: {json.dumps(d.content, ensure_ascii=False)[:300]}"
        for d in ctx.current_dimensions
    )

    keys_block = ", ".join(ctx.dimension_keys)

    user = (
        f"# 节点：{ctx.node_name}\n\n"
        f"## 版本演进史（共 {len(ctx.versions)} 条）\n{versions_block}\n\n"
        f"## 当前维度内容（{len(ctx.current_dimensions)} 条）\n{dims_block}\n\n"
        f"## 输出要求\n"
        f"- summary：一句话快照（≤ 80 字）\n"
        f"- dimensions：按以下 key 顺序输出（每个 key 一条）：{keys_block}\n"
        f"- content 字段为 JSON 对象（结构与当前维度内容形态相似 / AI 自决细节）"
    )
    return system, user


__all__ = ["build_prompt"]
