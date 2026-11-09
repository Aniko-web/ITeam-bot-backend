import json
import logging
from typing import Optional, Any
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

class InMemoryFallbackCache:
    """Zero-crash fallback in-memory cache when Redis server is offline locally."""
    def __init__(self):
        self._store: dict[str, str] = {}
        self._sets: dict[str, set] = {}

    async def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        self._store[key] = value
        return True

    async def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                count += 1
            if k in self._sets:
                del self._sets[k]
                count += 1
        return count

    async def sadd(self, key: str, *members: str) -> int:
        if key not in self._sets:
            self._sets[key] = set()
        prev_len = len(self._sets[key])
        self._sets[key].update(members)
        return len(self._sets[key]) - prev_len

    async def smembers(self, key: str) -> set:
        return self._sets.get(key, set())

    async def scard(self, key: str) -> int:
        return len(self._sets.get(key, set()))


class RedisManager:
    def __init__(self):
        self.client: Optional[aioredis.Redis] = None
        self.fallback = InMemoryFallbackCache()
        self.is_connected = False

    async def init(self):
        try:
            self.client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=2.0
            )
            await self.client.ping()
            self.is_connected = True
            logger.info("Connected to Redis successfully.")
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}). Using robust In-Memory fallback cache.")
            self.is_connected = False
            self.client = None

    async def close(self):
        if self.client and self.is_connected:
            await self.client.close()

    async def get(self, key: str) -> Optional[str]:
        if self.is_connected and self.client:
            return await self.client.get(key)
        return await self.fallback.get(key)

    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        val_str = json.dumps(value) if not isinstance(value, (str, int, float)) else str(value)
        if self.is_connected and self.client:
            return await self.client.set(key, val_str, ex=ex)
        return await self.fallback.set(key, val_str, ex=ex)

    async def delete(self, *keys: str) -> int:
        if self.is_connected and self.client:
            return await self.client.delete(*keys)
        return await self.fallback.delete(*keys)

    async def sadd(self, key: str, *members: str) -> int:
        if self.is_connected and self.client:
            return await self.client.sadd(key, *members)
        return await self.fallback.sadd(key, *members)

    async def smembers(self, key: str) -> set:
        if self.is_connected and self.client:
            return await self.client.smembers(key)
        return await self.fallback.smembers(key)

    async def scard(self, key: str) -> int:
        if self.is_connected and self.client:
            return await self.client.scard(key)
        return await self.fallback.scard(key)

redis_manager = RedisManager()

async def get_redis():
    return redis_manager

