"""Phase 2.3 子 sprint B — 性能基线 / capability-matrix C7 测试

scope（首版 / SKELETON 大部分）：
- 1000 project seed → P95 < 100ms（GET /projects + GET /projects/{pid}/overview）
- list endpoints / DAO 直接调用基线（不绕 router）

实施策略：
- 当前提供 1 个真跑 baseline（DAO 层 list project / 不依赖 HTTP 中间件 / 验证 DB+ORM 基线）
- 完整 pytest-benchmark + 1000 seed 推进 perf sprint（子 sprint D / 决策选项二时实施）
- pytest-benchmark 依赖留 §8.0 deps 不引入（避免 deps drift），用 stdlib timeit 占位

激活条件：
- pytest-benchmark 装 + 1000 row seed fixture 落到 tests/perf/conftest.py
- CI ci.yml perf-baseline job 接通（当前定义存在 / 实施推上线 sprint）
"""

from __future__ import annotations

import time

import pytest

pytestmark = pytest.mark.asyncio


@pytest.mark.skip(reason="SKELETON / 待 1000 seed fixture + pytest-benchmark 装")
async def test_list_projects_p95_under_100ms(db_session) -> None:
    """1000 project seed → list_for_user P95 < 100ms."""
    # TODO: seed 1000 projects + measure


async def test_baseline_db_roundtrip_smoke(db_session) -> None:
    """smoke baseline：单次 DB roundtrip < 50ms（环境健康度兜底 / 非 perf 断言）."""
    from sqlalchemy import text

    start = time.perf_counter()
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar_one() == 1
    elapsed_ms = (time.perf_counter() - start) * 1000
    # 宽松阈值（CI runner 抖动）：500ms 报警阈，超就是基线异常
    assert elapsed_ms < 500, f"DB roundtrip {elapsed_ms:.1f}ms > 500ms baseline"


async def test_baseline_orm_select_smoke(db_session) -> None:
    """ORM select 基线 / 验证 SQLAlchemy 配置健康."""
    from sqlalchemy import select

    from api.models.user import User

    start = time.perf_counter()
    result = await db_session.execute(select(User).limit(1))
    _ = result.scalars().first()
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 1000, f"ORM select {elapsed_ms:.1f}ms > 1000ms baseline"
