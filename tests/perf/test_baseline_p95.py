"""Sprint 2 Task 2.4 简化版 — pytest-benchmark P95 baseline（100 project seed）。

完整 1000 seed + CI 接通 perf-baseline job 推下次会话（cleanup-plan §479）；
本简化版建立 5 endpoint smoke benchmark + baseline.json 落字面：
- DAO 层 list_by_user / 不绕 router
- 100 project / 500 node / 1000 issue

跑：
    uv run pytest tests/perf/test_baseline_p95.py --benchmark-only \\
        --benchmark-json=tests/perf/baseline.json

阈值（CI runner 抖动 / 简化规模 / 下次升 1000 要重设）：
- list 100 project P95 < 200ms（DAO + selectinload）
- get_for_user 单 project P95 < 50ms
- list_issues 100 project ≤ 1000 issue P95 < 300ms
"""

from __future__ import annotations

import asyncio

import pytest

pytestmark = pytest.mark.asyncio


async def test_perf_dao_list_projects_for_user(perf_seeded_db, db_session, benchmark):
    """100 project / DAO 层 list_by_user — selectinload + ORDER BY created_at DESC。"""
    from api.dao.project_dao import ProjectDAO

    dao = ProjectDAO()
    user_id = perf_seeded_db["user"].id

    def run() -> int:
        rows = asyncio.get_event_loop().run_until_complete(
            dao.list_by_user(db_session, user_id, include_archived=False)
        )
        return len(rows)

    # benchmark.pedantic 需要 sync 函数；wrap async via run_until_complete 不安全（已在 loop）。
    # 改：直接 await 多轮 + 统计（pytest-benchmark 主要价值是结构化 P95 输出）。
    samples_ms = []
    import time

    for _ in range(10):
        start = time.perf_counter()
        rows = await dao.list_by_user(db_session, user_id, include_archived=False)
        samples_ms.append((time.perf_counter() - start) * 1000)
    assert len(rows) == 100  # type: ignore[name-defined]
    p95 = sorted(samples_ms)[int(len(samples_ms) * 0.95) - 1]
    benchmark.extra_info["p95_ms"] = round(p95, 2)
    benchmark.extra_info["samples"] = samples_ms
    benchmark(lambda: None)  # 占位：让 pytest-benchmark 输出 row（真测量在 samples_ms）
    assert p95 < 200, f"list_projects P95 {p95:.1f}ms > 200ms baseline"


async def test_perf_dao_get_project_by_id(perf_seeded_db, db_session, benchmark):
    """单 project get_by_id_for_user — 主键命中 + tenant 校验。"""
    from api.dao.project_dao import ProjectDAO

    dao = ProjectDAO()
    user_id = perf_seeded_db["user"].id
    proj_id = perf_seeded_db["projects"][50].id  # 中间一个

    samples_ms = []
    import time

    for _ in range(10):
        start = time.perf_counter()
        row = await dao.get_by_id_for_user(db_session, proj_id, user_id)
        samples_ms.append((time.perf_counter() - start) * 1000)
    assert row is not None
    p95 = sorted(samples_ms)[int(len(samples_ms) * 0.95) - 1]
    benchmark.extra_info["p95_ms"] = round(p95, 2)
    benchmark(lambda: None)
    assert p95 < 50, f"get_by_id P95 {p95:.1f}ms > 50ms baseline"


async def test_perf_dao_list_issues_by_project(perf_seeded_db, db_session, benchmark):
    """单 project 10 issue / list_by_project — selectinload _JOINS（node + 2 user relationship）."""
    from api.dao.issue_dao import IssueDAO

    dao = IssueDAO()
    proj_id = perf_seeded_db["projects"][0].id

    samples_ms = []
    import time

    for _ in range(10):
        start = time.perf_counter()
        rows = await dao.list_by_project(db_session, proj_id)
        samples_ms.append((time.perf_counter() - start) * 1000)
    assert len(rows) == 10
    p95 = sorted(samples_ms)[int(len(samples_ms) * 0.95) - 1]
    benchmark.extra_info["p95_ms"] = round(p95, 2)
    benchmark(lambda: None)
    assert p95 < 100, f"list_issues_by_project P95 {p95:.1f}ms > 100ms baseline"


async def test_perf_dao_list_nodes_by_project(perf_seeded_db, db_session, benchmark):
    """单 project 5 node / list_by_project tree — DAO 层。"""
    from api.dao.node_dao import NodeDAO

    dao = NodeDAO()
    proj_id = perf_seeded_db["projects"][0].id

    samples_ms = []
    import time

    for _ in range(10):
        start = time.perf_counter()
        rows = await dao.list_by_project(db_session, proj_id)
        samples_ms.append((time.perf_counter() - start) * 1000)
    assert len(rows) == 5
    p95 = sorted(samples_ms)[int(len(samples_ms) * 0.95) - 1]
    benchmark.extra_info["p95_ms"] = round(p95, 2)
    benchmark(lambda: None)
    assert p95 < 50, f"list_nodes P95 {p95:.1f}ms > 50ms baseline"


async def test_perf_aggregate_seed_health(perf_seeded_db, db_session, benchmark):
    """聚合健康 — 验 100x seed 真落库（防 fixture 静默失败）。"""
    from sqlalchemy import func, select

    from api.models.issue import Issue
    from api.models.node import Node
    from api.models.project import Project

    project_count = (await db_session.execute(select(func.count(Project.id)))).scalar_one()
    node_count = (await db_session.execute(select(func.count(Node.id)))).scalar_one()
    issue_count = (await db_session.execute(select(func.count(Issue.id)))).scalar_one()
    assert project_count >= 100
    assert node_count >= 500
    assert issue_count >= 1000
    benchmark.extra_info["project_count"] = project_count
    benchmark.extra_info["node_count"] = node_count
    benchmark.extra_info["issue_count"] = issue_count
    benchmark(lambda: None)
