"""Thin wrapper around the Redis client.

Deliberately just get/set/delete on raw strings — callers own their own
serialization (see `PatientRecord` in `app.services.patient_service`) so
this stays a generic caching primitive rather than knowing about any one
domain object's shape.
"""

from redis.asyncio import Redis


class CacheService:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def get(self, key: str) -> str | None:
        return await self.redis.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        await self.redis.set(key, value, ex=ttl_seconds)

    async def delete(self, *keys: str) -> None:
        if keys:
            await self.redis.delete(*keys)

    async def delete_pattern(self, pattern: str) -> None:
        """SCAN rather than KEYS, so invalidating a wide pattern (e.g.
        every cached page tied to a patient) doesn't block Redis's single
        event loop while it walks a large keyspace."""
        async for key in self.redis.scan_iter(match=pattern, count=100):
            await self.redis.delete(key)
