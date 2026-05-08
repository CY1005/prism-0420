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
async def make_project(db_session, make_user):
    """工厂 fixture：建 (user, project) 对。R1-B C1 修：消除 test_m03_*.py 三处重复。

    返回 async callable: `user, proj = await make_project(name_suffix="-A")`。
    """
    from uuid import uuid4

    from api.models.project import Project

    async def _make(
        *,
        name_suffix: str = "",
        owner: object | None = None,
    ):
        user = owner if owner is not None else await make_user()
        proj = Project(name=f"P-{uuid4().hex[:6]}{name_suffix}", owner_id=user.id)
        db_session.add(proj)
        await db_session.flush()
        return user, proj

    yield _make


@pytest_asyncio.fixture(loop_scope="session")
async def make_node(db_session):
    """工厂 fixture：建一个 node（默认 folder，path 与 depth 一致）。

    M04 sprint 加：M03 R1-B C1 规则延伸——禁止跨模块 test helper 内联重复。
    test_m03_dao.py 原内联 `_make_node` 迁移到本 fixture，M04+ 复用。
    """
    from uuid import uuid4

    from api.models.node import Node

    async def _make(project_id, *, parent=None, name: str = "n", **extra) -> Node:
        if parent is None:
            depth = 0
            prefix = "/"
        else:
            depth = parent.depth + 1
            prefix = parent.path
        nid = uuid4()
        node = Node(
            id=nid,
            project_id=project_id,
            parent_id=parent.id if parent else None,
            name=name,
            depth=depth,
            path=f"{prefix}{nid}/",
            **extra,
        )
        db_session.add(node)
        await db_session.flush()
        return node

    yield _make


@pytest_asyncio.fixture(loop_scope="session")
async def make_version(db_session):
    """工厂 fixture：建一条 version_records 行（M05）。

    R1-B P1-01 立修（M05 sprint，2026-05-08）：从 test_m05_dao.py 内联 _make_version
    迁入 conftest，保持"跨测试 helper 必须迁入 conftest"规则（M04 R1-B C1 同款）。

    用法：
      rec = await make_version(user=user, project=proj, node=node, label="v1")
      cur = await make_version(..., label="v2", is_current=True)
    """
    from api.models.version_record import VersionRecord

    async def _make(
        *,
        user,
        project,
        node,
        label: str,
        is_current: bool = False,
        summary: str = "s",
        details: str | None = None,
        change_type: str = "added",
        release_mode: str = "release",
        snapshot_data: dict | None = None,
    ):
        rec = VersionRecord(
            node_id=node.id,
            project_id=project.id,
            version_label=label,
            summary=summary,
            details=details,
            change_type=change_type,
            release_mode=release_mode,
            is_current=is_current,
            snapshot_data=snapshot_data,
            created_by=user.id,
        )
        db_session.add(rec)
        await db_session.flush()
        return rec

    yield _make


@pytest_asyncio.fixture(loop_scope="session")
async def make_dim_record(db_session):
    """工厂 fixture：建一条 dimension_records 行（M04 维度内容；M10 sprint 抽出）。

    R1-B P1-01 立修（M10 sprint，2026-05-08）：从 test_m10_dao.py + test_m10_service.py
    内联 _make_dim_record 迁入 conftest，规则六连延续：M04 R1-B B1.1 (_seed_dim_type) +
    M05 R1-B P1-01 (_make_version) + M06 R1-B P1-01 (_make_competitor) + M07 R1-B P1-01
    (_make_issue) + M08 R1-B P1-01 (_make_relation) + M10 R1-B P1-01 (_make_dim_record)。
    """
    from api.models.dimension_record import DimensionRecord

    async def _make(*, user, project, node, dim_type_id, content: dict | None = None):
        rec = DimensionRecord(
            node_id=node.id,
            project_id=project.id,
            dimension_type_id=dim_type_id,
            content=content or {"description": "x"},
            created_by=user.id,
            updated_by=user.id,
        )
        db_session.add(rec)
        await db_session.flush()
        return rec

    yield _make


@pytest_asyncio.fixture(loop_scope="session")
async def make_module_relation(db_session):
    """工厂 fixture：建一条 module_relations 行（M08）。

    R1-B P1-01 立修（M08 sprint，2026-05-08）：从 test_m08_dao.py 内联 _make_relation
    迁入 conftest，规则五连延续：M04 R1-B B1.1 + M05 R1-B P1-01 + M06 R1-B P1-01 +
    M07 R1-B P1-01 + M08 R1-B P1-01。
    """
    from api.models.module_relation import ModuleRelation

    async def _make(
        *,
        user,
        project,
        source_node,
        target_node,
        relation_type: str = "depends_on",
        notes: str | None = None,
    ):
        r = ModuleRelation(
            project_id=project.id,
            source_node_id=source_node.id,
            target_node_id=target_node.id,
            relation_type=relation_type,
            notes=notes,
            created_by=user.id,
        )
        db_session.add(r)
        await db_session.flush()
        return r

    yield _make


@pytest_asyncio.fixture(loop_scope="session")
async def make_issue(db_session):
    """工厂 fixture：建一条 issues 行（M07）。

    R1-B P1-01 立修（M07 sprint，2026-05-08）：从 test_m07_dao.py 内联 _make_issue
    迁入 conftest，规则四连延续：M04 R1-B B1.1（_seed_dim_type）+ M05 R1-B P1-01
    （_make_version）+ M06 R1-B P1-01（_make_competitor/_ref）+ M07 R1-B P1-01。
    """
    from api.models.issue import Issue

    async def _make(
        *,
        user,
        project,
        node=None,
        category: str = "bug",
        status: str = "open",
        title: str = "t",
        description: str = "d",
        tags: list[str] | None = None,
    ):
        i = Issue(
            project_id=project.id,
            node_id=node.id if node else None,
            category=category,
            status=status,
            title=title,
            description=description,
            tags=tags if tags is not None else [],
            created_by=user.id,
        )
        db_session.add(i)
        await db_session.flush()
        return i

    yield _make


@pytest_asyncio.fixture(loop_scope="session")
async def make_competitor(db_session):
    """工厂 fixture：建一条 competitors 行（M06）。

    R1-B P1-01 / R1-C P1-02 立修（M06 sprint，2026-05-08）：
    test_m06_dao.py 内联 `_make_competitor` 迁入 conftest，规则延续
    M04 R1-B B1.1（_seed_dim_type）+ M05 R1-B P1-01（_make_version）。

    用法：
      c = await make_competitor(project=proj, user=user, name="Notion")
      c = await make_competitor(project=proj, user=user, website_url="...", description="...")
    """
    from api.models.competitor import Competitor

    async def _make(
        *,
        project,
        user,
        name: str = "Notion",
        website_url: str | None = None,
        description: str | None = None,
    ):
        c = Competitor(
            project_id=project.id,
            display_name=name,
            website_url=website_url,
            description=description,
            created_by=user.id,
        )
        db_session.add(c)
        await db_session.flush()
        return c

    yield _make


@pytest_asyncio.fixture(loop_scope="session")
async def make_competitor_ref(db_session):
    """工厂 fixture：建一条 competitor_refs 行（M06）。

    R1-B P1-01 / R1-C P1-02 立修（M06 sprint，2026-05-08）：
    test_m06_dao.py 内联 `_make_ref` 迁入 conftest。
    """
    from api.models.competitor import CompetitorRef

    async def _make(*, project, node, competitor, user):
        ref = CompetitorRef(
            node_id=node.id,
            competitor_id=competitor.id,
            project_id=project.id,
            created_by=user.id,
        )
        db_session.add(ref)
        await db_session.flush()
        return ref

    yield _make


@pytest_asyncio.fixture(loop_scope="session")
async def make_dim_type(db_session):
    """工厂 fixture：建 dimension_types 行（可选同时建 ProjectDimensionConfig）。

    M05 sprint 抽出（M04 punt R1-B B1.1，2026-05-07）：消除 4 处 _seed_dim_type
    内联重复（test_m04_models / test_m04_service / test_m04_dao / test_m04_routers）。

    用法：
      type_id = await make_dim_type(key="t1")  # 仅建 type
      type_id = await make_dim_type(key="g1", project_id=pid)  # 建 type + PDC enabled
      type_id = await make_dim_type(key="off", project_id=pid, enabled=False)  # PDC disabled
    """
    from api.models.project import DimensionType, ProjectDimensionConfig

    async def _make(
        *,
        key: str = "t",
        name: str | None = None,
        project_id=None,
        enabled: bool = True,
        sort_order: int = 0,
        icon: str | None = None,
    ) -> int:
        dt_kwargs: dict = {"key": key, "name": name if name is not None else f"DT-{key}"}
        if icon is not None:
            dt_kwargs["icon"] = icon
        dt = DimensionType(**dt_kwargs)
        db_session.add(dt)
        await db_session.flush()
        if project_id is not None:
            db_session.add(
                ProjectDimensionConfig(
                    project_id=project_id,
                    dimension_type_id=dt.id,
                    enabled=enabled,
                    sort_order=sort_order,
                )
            )
            await db_session.flush()
        return dt.id

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


@pytest_asyncio.fixture(loop_scope="session")
async def make_cold_start_task(db_session):
    """工厂 fixture：建一条 cold_start_tasks 行（M11+）。

    M11 sprint R1-B 立修（2026-05-08）：内联 _make_task 在 test_m11_dao.py 多次
    使用 → 迁 conftest（M04-M10 七连规则延续，下个 R-X1 模块可复用）。

    用法：t = await make_cold_start_task(project_id=p.id, user_id=u.id, status="pending")
    """
    from uuid import uuid4

    from api.models.cold_start_task import ColdStartStatus, ColdStartTask

    async def _make(
        *,
        project_id,
        user_id,
        status: str = ColdStartStatus.PENDING.value,
        source_filename: str = "x.csv",
        source_hash: str | None = None,
    ) -> ColdStartTask:
        task = ColdStartTask(
            project_id=project_id,
            user_id=user_id,
            source_hash=source_hash or uuid4().hex,
            source_filename=source_filename,
            status=status,
        )
        db_session.add(task)
        await db_session.flush()
        return task

    yield _make
