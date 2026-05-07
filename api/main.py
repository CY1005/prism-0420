from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from api.core.config import settings
from api.core.db import SessionLocal, engine
from api.core.logging import configure_logging, log
from api.core.redis import get_redis
from api.errors import register_exception_handlers
from api.routers import auth as auth_router
from api.services.auth_service import get_auth_service

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("app.startup", version="0.1.0")
    if settings.bootstrap_admin_email and settings.bootstrap_admin_password:
        try:
            async with SessionLocal() as db:
                created = await get_auth_service().bootstrap_admin_if_empty(
                    db,
                    email=settings.bootstrap_admin_email,
                    password=settings.bootstrap_admin_password,
                    name=settings.bootstrap_admin_name,
                )
            if created is not None:
                log.info("app.bootstrap_admin_created", email=created.email)
        except Exception as exc:  # noqa: BLE001
            log.warning("app.bootstrap_admin_failed", error=str(exc))
    else:
        log.info("app.bootstrap_admin_skipped", reason="env not set")
    yield
    log.info("app.shutdown")


app = FastAPI(title="prism-0420", version="0.1.0", lifespan=lifespan)
register_exception_handlers(app)
app.include_router(auth_router.router)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/readyz")
async def readyz() -> dict[str, object]:
    pg_ok = False
    redis_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        pg_ok = True
    except Exception:
        pg_ok = False

    redis = get_redis()
    try:
        redis_ok = bool(await redis.ping())
    except Exception:
        redis_ok = False
    finally:
        await redis.aclose()

    return {"pg": pg_ok, "redis": redis_ok, "ok": pg_ok and redis_ok}
