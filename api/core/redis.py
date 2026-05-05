from redis.asyncio import Redis, from_url

from api.core.config import settings


def get_redis() -> Redis:
    return from_url(settings.redis_url, decode_responses=True)
