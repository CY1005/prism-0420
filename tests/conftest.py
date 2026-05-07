"""B9 fixtures：每个 test 独立 NESTED savepoint，结束后回滚到干净状态。

- engine 走 prism_test 库（与 dev 库 prism 隔离）
- session 启动时跑 alembic upgrade head（走生产路径，防 migration 漂移）
- 每个 db_session 用 connection-level transaction + nested savepoint，session.commit() 只 commit 到 savepoint
"""

from __future__ import annotations

import asyncio
import os

# 测试环境降低 bcrypt 成本，必须在 api.auth.password 被首次 import 前设置
os.environ.setdefault("BCRYPT_ROUNDS_OVERRIDE", "4")

from collections.abc import AsyncIterator  # noqa: E402

import pytest_asyncio  # noqa: E402
from alembic import command  # noqa: E402
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


# ─────────────── M01 fixtures ────────────────


@pytest_asyncio.fixture(loop_scope="session")
async def auth_app(db_session):
    """复用 test db_session 的 FastAPI app（覆盖 get_db dependency）。

    跳过 lifespan（不跑 bootstrap），bootstrap 测试在专属 fixture 里手动触发。
    """
    from api.core.db import get_db
    from api.main import app

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield app
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture(loop_scope="session")
async def auth_client(auth_app):
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=auth_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture(loop_scope="session")
async def make_user(db_session):
    """工厂 fixture：插一个 user 行（默认 active / role=user）。"""
    from api.auth.password import hash_password
    from api.models.user import User

    created: list[User] = []

    async def _make(
        *,
        email: str | None = None,
        password: str = "Password123!",
        name: str = "Test User",
        role: str = "user",
        status_: str = "active",
        password_hash: str | None = None,
    ) -> User:
        from uuid import uuid4

        if email is None:
            email = f"u{uuid4().hex[:8]}@example.com"
        user = User(
            email=email,
            name=name,
            role=role,
            status=status_,
            password_hash=password_hash if password_hash is not None else hash_password(password),
            failed_login_count=0,
            version=1,
        )
        db_session.add(user)
        await db_session.flush()
        created.append(user)
        return user

    yield _make


@pytest_asyncio.fixture(loop_scope="session")
async def isolated_db(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """独立连接 + 顶层事务的 session（不走 savepoint）。

    专给"必须验证 commit/rollback 真实路径"的测试用（如 C9 事务原子性）。
    退出时手工清理 users / refresh_tokens / auth_audit_log（M01 测试创建的所有数据）。
    """
    from sqlalchemy import text as _text

    async with engine.connect() as conn:
        factory = async_sessionmaker(bind=conn, expire_on_commit=False, class_=AsyncSession)
        session = factory()
        try:
            yield session
        finally:
            await session.close()
            # 清掉本测试创建的行（按 FK 顺序）
            for table in (
                "auth_audit_log",
                "refresh_tokens",
                "password_reset_tokens",
                "invite_codes",
                "auth_identities",
                "email_change_requests",
                "users",
            ):
                await conn.execute(_text(f"DELETE FROM {table}"))
            await conn.commit()


@pytest_asyncio.fixture(loop_scope="session")
async def isolated_app(isolated_db):
    """复用 isolated_db 的 FastAPI app（覆盖 get_db）。"""
    from api.core.db import get_db
    from api.main import app

    async def _override_get_db():
        yield isolated_db

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield app
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture(loop_scope="session")
async def isolated_client(isolated_app):
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=isolated_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        yield client
