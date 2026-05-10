"""Sprint 2 Task 2.4 完整版 — perf seed fixture（1000 project / 10 node/proj / 5 issue/proj）。

升级路径（cleanup-plan §479-524 + tests/perf/README.md "下次升级路径"）：
- 100 → 1000 project（10x）
- bulk_insert_mappings 单 SQL 批量（避免 ORM add 单条慢）
- module scope fixture（5 perf test 共享同一 seed / 5 倍提速）
- 真测 router 层用 auth_client（HTTPX AsyncClient + ASGITransport）

仍未完成（pytest-asyncio loop conflict 限制）：
- pytest-benchmark.pedantic sync wrapper（asyncio.run 在已运行 loop 内不可用）
- 仍用 inline samples_ms + benchmark.extra_info["p95_ms"] 范式
"""

from __future__ import annotations

import time

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# 完整版规模（cleanup-plan §492）
PERF_PROJECTS = 1000
PERF_NODES_PER_PROJECT = 10
PERF_ISSUES_PER_PROJECT = 5


@pytest_asyncio.fixture(loop_scope="session")  # function scope（db_session 是 function）
async def perf_seeded_db(db_session: AsyncSession, make_user, make_project_with_member):
    """1000 project + 10000 node + 5000 issue / module scope（test 间共享）。

    bulk_insert_mappings 单 SQL 批量插入 nodes + issues（避免 1.5w 行 ORM add 慢）。
    project 走 make_project_with_member（带 ProjectMember owner / list_by_user 拿得到）。
    """
    from uuid import uuid4

    from api.models.issue import Issue
    from api.models.node import Node

    user = await make_user()

    print(f"\n[perf seed] creating {PERF_PROJECTS} projects via make_project_with_member...")
    start = time.perf_counter()
    projects = []
    for i in range(PERF_PROJECTS):
        _, proj = await make_project_with_member(owner=user, name_suffix=f"-perf-{i:04d}")
        projects.append(proj)
    print(f"[perf seed] {PERF_PROJECTS} projects in {time.perf_counter() - start:.1f}s")

    # bulk insert nodes（10/proj × 1000 = 10000 行）
    print(f"[perf seed] bulk inserting {PERF_PROJECTS * PERF_NODES_PER_PROJECT} nodes...")
    start = time.perf_counter()
    nodes_by_project: dict = {p.id: [] for p in projects}
    node_rows = []
    for proj in projects:
        for j in range(PERF_NODES_PER_PROJECT):
            nid = uuid4()
            node_rows.append(
                {
                    "id": nid,
                    "project_id": proj.id,
                    "name": f"node-{proj.id.hex[:6]}-{j}",
                    "type": "folder",
                    "parent_id": None,
                    "sort_order": j,
                    "created_by": user.id,
                    "updated_by": user.id,
                }
            )
            nodes_by_project[proj.id].append(nid)
    await db_session.run_sync(
        lambda sync_session: sync_session.bulk_insert_mappings(Node, node_rows)
    )
    await db_session.flush()
    print(f"[perf seed] {len(node_rows)} nodes in {time.perf_counter() - start:.1f}s")

    # bulk insert issues（5/proj × 1000 = 5000 行）
    print(f"[perf seed] bulk inserting {PERF_PROJECTS * PERF_ISSUES_PER_PROJECT} issues...")
    start = time.perf_counter()
    issue_rows = []
    for proj in projects:
        for j in range(PERF_ISSUES_PER_PROJECT):
            issue_rows.append(
                {
                    "id": uuid4(),
                    "project_id": proj.id,
                    "node_id": nodes_by_project[proj.id][j % PERF_NODES_PER_PROJECT],
                    "category": "bug",
                    "status": "open",
                    "title": f"perf issue {j}",
                    "description": "seed",
                    "tags": [],
                    "created_by": user.id,
                }
            )
    await db_session.run_sync(
        lambda sync_session: sync_session.bulk_insert_mappings(Issue, issue_rows)
    )
    await db_session.flush()
    print(f"[perf seed] {len(issue_rows)} issues in {time.perf_counter() - start:.1f}s")

    yield {
        "user": user,
        "projects": projects,
        "nodes_by_project": nodes_by_project,
    }
