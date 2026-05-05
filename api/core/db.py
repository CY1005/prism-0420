from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from api.core.config import settings

engine: AsyncEngine = create_async_engine(settings.database_url, echo=False, future=True)
