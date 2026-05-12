"""dev/test 用 dimension_types + project_dimension_configs 8 维度 seed 脚本。

Phase 2.3 cleanup B sprint 临时方案——dogfooding 解锁。

为什么不进 alembic migration：
- design §3.Y R3-6-C 明文：业务字典清单走运行期 admin endpoint
  (POST /api/admin/dimension-types，待 admin UI 实装)
- alembic migration 写死会跟 R3-6-C 真路径冲突
- 长期 D-2 sprint：实装 admin endpoint + create_project hook，4-8h（已立 punt pool）

为什么 8 个 key 跟 prism v1 seed.ts 不完全一致：
- prism v1 用 `requirement` / `competitor`，prism-0420 workspace.tsx
  dimensionIconMap 用 `requirement_analysis` / `competitive_ref`。
- 以 prism-0420 workspace 前端 hardcode 为准（前端 dimensionIconMap 是 A sprint
  内部消费点，不改 / 后端按其 key 种）。

使用：
    uv run python scripts/seed_dimension_types.py

幂等：
- dimension_types 用 ON CONFLICT (key) DO NOTHING — 重跑不重复
- project_dimension_configs 用 ON CONFLICT (project_id, dimension_type_id) DO NOTHING
  → 需 schema 加 unique 约束，本期跑 SELECT 后判 INSERT
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from api.core.config import settings

# prism-0420 workspace.tsx dimensionIconMap 8 key 真值
DIMENSION_TYPES_SEED: list[dict[str, str]] = [
    {
        "key": "description",
        "name": "功能描述",
        "icon": "FileText",
        "description": "功能的核心说明",
    },
    {
        "key": "user_scenario",
        "name": "用户场景",
        "icon": "Users",
        "description": "谁在什么场景下使用",
    },
    {
        "key": "tech_impl",
        "name": "技术实现",
        "icon": "Server",
        "description": "平台侧的技术方案",
    },
    {
        "key": "design_decision",
        "name": "设计决策",
        "icon": "GitBranch",
        "description": "关键架构决策及取舍",
    },
    {
        "key": "engineering_exp",
        "name": "工程经验",
        "icon": "Lightbulb",
        "description": "踩坑记录与最佳实践",
    },
    {
        "key": "test_analysis",
        "name": "测试分析",
        "icon": "TestTube",
        "description": "测试策略与问题记录",
    },
    {
        "key": "requirement_analysis",
        "name": "需求分析",
        "icon": "ClipboardList",
        "description": "需求拆解与影响范围",
    },
    {
        "key": "competitive_ref",
        "name": "竞品参考",
        "icon": "Building",
        "description": "竞品功能对标分析",
    },
]


async def seed(db_name: str = "prism") -> None:
    base = settings.database_url.rsplit("/", 1)[0]
    eng = create_async_engine(f"{base}/{db_name}", isolation_level="AUTOCOMMIT")

    async with eng.connect() as conn:
        # 1. INSERT dimension_types（幂等：ON CONFLICT key DO NOTHING）
        inserted_dims = 0
        for d in DIMENSION_TYPES_SEED:
            result = await conn.execute(
                text(
                    "INSERT INTO dimension_types (key, name, icon, description) "
                    "VALUES (:key, :name, :icon, :description) "
                    "ON CONFLICT (key) DO NOTHING RETURNING id"
                ),
                d,
            )
            if result.rowcount > 0:
                inserted_dims += 1
        print(
            f"[{db_name}] dimension_types inserted: {inserted_dims}/{len(DIMENSION_TYPES_SEED)} (rest existed)"
        )

        # 2. 取所有 dimension_types id（8 行无论新插还是已有）
        dim_rows = (
            await conn.execute(
                text("SELECT id, key FROM dimension_types WHERE key = ANY(:keys)"),
                {"keys": [d["key"] for d in DIMENSION_TYPES_SEED]},
            )
        ).all()
        dim_ids = [row[0] for row in dim_rows]
        print(
            f"[{db_name}] dimension_type ids resolved: {len(dim_ids)} ({[r[1] for r in dim_rows]})"
        )

        # 3. 对所有现有 projects INSERT project_dimension_configs（SELECT-then-INSERT 判去重）
        projects = (await conn.execute(text("SELECT id FROM projects"))).all()
        total_inserted_configs = 0
        for (pid,) in projects:
            existing = (
                await conn.execute(
                    text(
                        "SELECT dimension_type_id FROM project_dimension_configs WHERE project_id = :pid"
                    ),
                    {"pid": pid},
                )
            ).all()
            existing_dim_ids = {row[0] for row in existing}
            missing = [(did, idx) for idx, did in enumerate(dim_ids) if did not in existing_dim_ids]
            for did, sort_order in missing:
                await conn.execute(
                    text(
                        "INSERT INTO project_dimension_configs "
                        "(project_id, dimension_type_id, enabled, sort_order) "
                        "VALUES (:pid, :did, true, :sort_order)"
                    ),
                    {"pid": pid, "did": did, "sort_order": sort_order},
                )
                total_inserted_configs += 1
        print(
            f"[{db_name}] project_dimension_configs inserted: {total_inserted_configs} "
            f"(across {len(projects)} project(s))"
        )

    await eng.dispose()


async def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "prism"
    valid_targets = {"prism", "prism_test", "both"}
    if target not in valid_targets:
        print(f"usage: {sys.argv[0]} [prism|prism_test|both]")
        sys.exit(1)
    targets = ["prism", "prism_test"] if target == "both" else [target]
    for t in targets:
        await seed(t)


if __name__ == "__main__":
    asyncio.run(main())
