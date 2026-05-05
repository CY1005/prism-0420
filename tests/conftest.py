"""B9 fixtures：每个 test 独立 NESTED savepoint，结束后回滚到干净状态。

- engine 走 prism_test 库（与 dev 库 prism 隔离）
- session 启动时跑 alembic upgrade head（走生产路径，防 migration 漂移）
- 每个 db_session 用 connection-level transaction + nested savepoint，session.commit() 只 commit 到 savepoint
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator

import pytest_asyncio
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from api.core.config import settings

_TEST_DB = "prism_test"


def _admin_url() -> str:
    """连 postgres 默认库，用于 CREATE / DROP DATABASE（不能在事务内执行）。"""
    return settings.database_url.rsplit("/", 1)[0] + "/postgres"


def _test_url() -> str:
    return settings.database_url.rsplit("/", 1)[0] + f"/{_TEST_DB}"


def _sync_test_url() -> str:
    """alembic env.py 用 async engine，但 set_main_option 需要 URL 字符串；保持 +asyncpg。"""
    return _test_url()


async def _ensure_test_db_exists() -> None:
    admin = create_async_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :n"),
                {"n": _TEST_DB},
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{_TEST_DB}"'))
    finally:
        await admin.dispose()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    await _ensure_test_db_exists()

    os.environ["DATABASE_URL"] = _sync_test_url()

    def _run_alembic_upgrade() -> None:
        cfg = AlembicConfig("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", _sync_test_url())
        command.upgrade(cfg, "head")

    await asyncio.to_thread(_run_alembic_upgrade)

    eng = create_async_engine(_test_url(), future=True)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def db_connection(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    async with engine.connect() as conn:
        await conn.begin()
        yield conn
        await conn.rollback()


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(db_connection: AsyncConnection) -> AsyncIterator[AsyncSession]:
    """ADR-001 单 ORM：测试 session 与生产 AsyncSession 同源。

    每次 session.commit() 实际只 commit 到 savepoint；teardown 时连接级
    transaction rollback 把所有 savepoint 一并丢弃。SQLAlchemy 2.0 的
    `join_transaction_mode='create_savepoint'` 自动处理嵌套。
    """
    factory = async_sessionmaker(
        bind=db_connection,
        expire_on_commit=False,
        class_=AsyncSession,
        join_transaction_mode="create_savepoint",
    )
    session = factory()

    @event.listens_for(session.sync_session, "after_transaction_end")
    def _restart_savepoint(sync_session, transaction):
        if transaction.nested and not transaction._parent.nested:
            sync_session.begin_nested()

    try:
        yield session
    finally:
        await session.close()
