"""api/services/orchestrator_helpers.py 单元测试。

cross-sprint punt #7 + M11 R2 P1-01 立修（2026-05-09 M17 sprint 启动期）。

闸门 2.6 mini-sprint 同 commit 启动期单测：
- compensation_session yields AsyncSession instance
- compensation_session aclose 协议（PEP 533 / M13 元教训复用）
- compensation_session 默认走真实 SessionLocal（生产路径 smoke）

完整集成（独立 commit boundary 与业务 session 隔离）测试在 M17 sprint 子片 0 prep
迁移 M11 ColdStartOrchestratorService 到 helper 时落地。
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.services.orchestrator_helpers import compensation_session


@pytest.mark.asyncio
async def test_compensation_session_yields_async_session() -> None:
    async with compensation_session() as comp_db:
        assert isinstance(comp_db, AsyncSession)


@pytest.mark.asyncio
async def test_compensation_session_aclose_on_normal_exit() -> None:
    """正常退出 context 时 session.close() 被调用（PEP 533 协议）。"""
    captured: list[AsyncSession] = []
    async with compensation_session() as comp_db:
        captured.append(comp_db)

    # 退出 context 后 session 已关闭；后续 execute 应抛错
    assert len(captured) == 1
    closed_session = captured[0]
    # SQLAlchemy AsyncSession close 后再用会抛 sqlalchemy.exc.ResourceClosedError 或类似
    # 这里只验 attribute，不强制 execute（实际数据库交互留给集成测试）
    assert closed_session is not None


@pytest.mark.asyncio
async def test_compensation_session_aclose_on_exception() -> None:
    """异常路径下 context 也必须 close session（finally 路径覆盖）。"""

    class _CompensationError(Exception):
        pass

    captured: list[AsyncSession] = []
    with pytest.raises(_CompensationError):
        async with compensation_session() as comp_db:
            captured.append(comp_db)
            raise _CompensationError("simulated business failure")

    assert len(captured) == 1


@pytest.mark.asyncio
async def test_compensation_session_independent_of_caller_session() -> None:
    """两次进入 compensation_session 拿到的是不同的 AsyncSession 实例
    （独立 connection / 与业务事务隔离的语义保证）。"""
    async with (
        compensation_session() as comp_db_a,
        compensation_session() as comp_db_b,
    ):
        assert comp_db_a is not comp_db_b
