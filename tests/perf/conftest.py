"""Sprint 2 Task 2.4 简化版 — perf seed fixture（100 projects / 不到 1000 的简化基线）。

cleanup-plan §479-524 完整版（1000 项目 + 10000 dimension + 5000 issue）推下次会话；
本简化版用 100x 规模建立 baseline + 5 个 endpoint smoke benchmark 验证 pytest-benchmark
基础设施 + 闸门 5 §8.1 第 2 项 PARTIAL。
"""

from __future__ import annotations

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# 简化规模（cleanup-plan §492 完整 1000 → 本期 100 / 10x downsize）
PERF_PROJECTS = 100
PERF_NODES_PER_PROJECT = 5
PERF_ISSUES_PER_PROJECT = 10


@pytest_asyncio.fixture(scope="function")
async def perf_seeded_db(db_session: AsyncSession, make_user, make_project_with_member, make_node):
    """在 db_session 内 seed 简化数据（100 project + 500 node + 1000 issue）。

    scope=function 不 session：避免与其他测试 DB 状态串扰；
    perf 测 setup 时间也算 / 反映冷启动；下次会话上 1000 时再考虑 session+truncate。
    """
    user = await make_user()

    from api.models.issue import Issue

    projects = []
    for i in range(PERF_PROJECTS):
        _, proj = await make_project_with_member(owner=user, name_suffix=f"-perf-{i:04d}")
        projects.append(proj)

    nodes_by_project: dict = {}
    for proj in projects:
        nodes = []
        for j in range(PERF_NODES_PER_PROJECT):
            n = await make_node(proj.id, name=f"node-{proj.id}-{j}")
            nodes.append(n)
        nodes_by_project[proj.id] = nodes

    # 直插 issues（绕过 service / 避免 N×activity_log 拖慢 setup）
    for proj in projects:
        for j in range(PERF_ISSUES_PER_PROJECT):
            db_session.add(
                Issue(
                    project_id=proj.id,
                    node_id=nodes_by_project[proj.id][j % PERF_NODES_PER_PROJECT].id,
                    category="bug",
                    status="open",
                    title=f"perf issue {j}",
                    description="seed",
                    created_by=user.id,
                )
            )
    await db_session.flush()

    yield {
        "user": user,
        "projects": projects,
        "nodes_by_project": nodes_by_project,
    }
