from fastapi import FastAPI
from sqlalchemy import text

from api.core.db import engine
from api.core.redis import get_redis

app = FastAPI(title="prism-0420", version="0.1.0")


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
