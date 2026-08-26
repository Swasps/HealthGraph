from redis.asyncio import Redis

from app.core.config import get_settings

settings = get_settings()

# A single connection pool shared process-wide (the redis-py client is
# safe for concurrent use); this is analogous to the SQLAlchemy engine's
# pool and avoids opening a new TCP connection per request.
redis_client: Redis = Redis.from_url(
    settings.redis_url, decode_responses=True, max_connections=50
)


async def get_redis() -> Redis:
    return redis_client
