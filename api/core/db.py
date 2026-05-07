from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from api.core.config import settings

engine: AsyncEngine = create_async_engine(settings.database_url, echo=False, future=True)

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

# Test override hook: tests/conftest.py 用 connection-bound savepoint session,
# 通过 ``override_session_factory`` 注入供 FastAPI dependency 使用。
_session_factory: async_sessionmaker[AsyncSession] | None = None


def override_session_factory(factory: async_sessionmaker[AsyncSession] | None) -> None:
    global _session_factory
    _session_factory = factory


async def get_db() -> AsyncIterator[AsyncSession]:
    factory = _session_factory or SessionLocal
    session = factory()
    try:
        yield session
    finally:
        await session.close()
