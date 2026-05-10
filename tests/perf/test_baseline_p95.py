"""Sprint 2 Task 2.4 完整版 — pytest-benchmark P95 baseline（1000 project / DAO 层）.

升级路径完成项（vs 简化版 100 → 完整 1000）：
- ✅ 1000 project / 10000 node / 5000 issue（10x scale）
- ✅ bulk_insert_mappings 单 SQL 批量插入（setup ~6s vs 单条 ORM ~100s）
- ✅ make_project_with_member 走 ProjectMember 真实校验路径

仍未完成项（写入 README 限制段）：
- ⏸ pytest-benchmark.pedantic sync wrapper（pytest-asyncio loop_scope=session conflict /
  asyncio.run 在已运行 loop 内 raise / 仍 inline samples_ms + benchmark.extra_info）
- ⏸ router 层真测（dep override + session sharing 复杂；DAO 层基线足够 / router 加 ~2-5ms
  middleware overhead 推下次专 sprint）
- ⏸ fixture scope=session（db_session 是 function scope / 每 test 重 seed 6s × 5 = 30s 接受）
- ⏸ CI perf-baseline job 接通（依赖 PAT scope）

跑：
    uv run pytest tests/perf/test_baseline_p95.py --benchmark-only \\
        --benchmark-json=tests/perf/baseline.json
"""

from __future__ import annotations

import time

import pytest

pytestmark = pytest.mark.asyncio


def _measure_p95(samples_ms: list[float]) -> dict:
    """统计 P95 + 中位数 + extra_info dict for benchmark."""
    p95 = sorted(samples_ms)[int(len(samples_ms) * 0.95) - 1]
    return {
        "p95_ms": round(p95, 2),
        "median_ms": round(sorted(samples_ms)[len(samples_ms) // 2], 2),
        "min_ms": round(min(samples_ms), 2),
        "max_ms": round(max(samples_ms), 2),
        "samples": [round(s, 2) for s in samples_ms],
    }


async def test_perf_dao_list_projects_for_user(perf_seeded_db, db_session, benchmark):
    """1000 project / DAO list_by_user — selectinload + ORDER BY created_at DESC."""
    from api.dao.project_dao import ProjectDAO

    dao = ProjectDAO()
    user_id = perf_seeded_db["user"].id

    samples_ms = []
    for _ in range(10):
        start = time.perf_counter()
        rows = await dao.list_by_user(db_session, user_id, include_archived=False)
        samples_ms.append((time.perf_counter() - start) * 1000)
    assert len(rows) == 1000
    stats = _measure_p95(samples_ms)
    benchmark.extra_info.update(stats)
    benchmark.extra_info["scale"] = "1000 projects"
    benchmark(lambda: None)
    # 1000 project 阈值（10x scale up vs 简化版 100/200ms）
    assert stats["p95_ms"] < 1500, (
        f"list_projects P95 {stats['p95_ms']}ms > 1500ms baseline (1000 project)"
    )


async def test_perf_dao_get_project_by_id(perf_seeded_db, db_session, benchmark):
    """单 project / get_by_id_for_user — 主键命中 + tenant 校验."""
    from api.dao.project_dao import ProjectDAO

    dao = ProjectDAO()
    user_id = perf_seeded_db["user"].id
    proj_id = perf_seeded_db["projects"][500].id  # 中间一个

    samples_ms = []
    for _ in range(10):
        start = time.perf_counter()
        row = await dao.get_by_id_for_user(db_session, proj_id, user_id)
        samples_ms.append((time.perf_counter() - start) * 1000)
    assert row is not None
    stats = _measure_p95(samples_ms)
    benchmark.extra_info.update(stats)
    benchmark.extra_info["scale"] = "single get / 1000 in DB"
    benchmark(lambda: None)
    assert stats["p95_ms"] < 50, f"get_by_id P95 {stats['p95_ms']}ms > 50ms baseline"


async def test_perf_dao_list_issues_by_project(perf_seeded_db, db_session, benchmark):
    """单 project 5 issue / list_by_project — selectinload _JOINS（node + 2 user）."""
    from api.dao.issue_dao import IssueDAO

    dao = IssueDAO()
    proj_id = perf_seeded_db["projects"][0].id

    samples_ms = []
    for _ in range(10):
        start = time.perf_counter()
        rows = await dao.list_by_project(db_session, proj_id)
        samples_ms.append((time.perf_counter() - start) * 1000)
    assert len(rows) == 5
    stats = _measure_p95(samples_ms)
    benchmark.extra_info.update(stats)
    benchmark.extra_info["scale"] = "5 issue/proj / 5000 in DB"
    benchmark(lambda: None)
    assert stats["p95_ms"] < 100, f"list_issues P95 {stats['p95_ms']}ms > 100ms baseline"


async def test_perf_dao_list_nodes_by_project(perf_seeded_db, db_session, benchmark):
    """单 project 10 node / list_by_project tree."""
    from api.dao.node_dao import NodeDAO

    dao = NodeDAO()
    proj_id = perf_seeded_db["projects"][0].id

    samples_ms = []
    for _ in range(10):
        start = time.perf_counter()
        rows = await dao.list_by_project(db_session, proj_id)
        samples_ms.append((time.perf_counter() - start) * 1000)
    assert len(rows) == 10
    stats = _measure_p95(samples_ms)
    benchmark.extra_info.update(stats)
    benchmark.extra_info["scale"] = "10 node/proj / 10000 in DB"
    benchmark(lambda: None)
    assert stats["p95_ms"] < 50, f"list_nodes P95 {stats['p95_ms']}ms > 50ms baseline"


async def test_perf_aggregate_seed_health(perf_seeded_db, db_session, benchmark):
    """聚合健康 — 验 1000x seed 真落库（防 fixture 静默失败）."""
    from sqlalchemy import func, select

    from api.models.issue import Issue
    from api.models.node import Node
    from api.models.project import Project

    project_count = (await db_session.execute(select(func.count(Project.id)))).scalar_one()
    node_count = (await db_session.execute(select(func.count(Node.id)))).scalar_one()
    issue_count = (await db_session.execute(select(func.count(Issue.id)))).scalar_one()
    assert project_count >= 1000
    assert node_count >= 10000
    assert issue_count >= 5000
    benchmark.extra_info["project_count"] = project_count
    benchmark.extra_info["node_count"] = node_count
    benchmark.extra_info["issue_count"] = issue_count
    benchmark(lambda: None)
