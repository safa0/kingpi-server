"""
Async cache protocol and Redis implementation.

Defines a minimal `Cache` protocol for TTL-based key-value caching and a
`RedisTTLCache` production implementation backed by Redis.

The protocol stores serialized strings — callers handle serialization.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from redis import RedisError

logger = logging.getLogger(__name__)


class Cache(Protocol):
    """Structural interface for async TTL caches."""

    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ttl_seconds: int) -> None: ...
    async def delete(self, key: str) -> None: ...


class RedisTTLCache:
    """Redis-backed TTL cache with graceful degradation.

    On connection failure, `get` returns None (cache miss) and `set`/`delete`
    become no-ops. The system degrades to uncached calls rather than failing.
    """

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    async def get(self, key: str) -> str | None:
        try:
            value = await self._redis.get(key)
            return value.decode() if isinstance(value, bytes) else value
        except (RedisError, OSError):
            logger.warning("Redis GET failed for key %s, treating as cache miss", key)
            return None

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            await self._redis.set(key, value, ex=ttl_seconds)
        except (RedisError, OSError):
            logger.warning("Redis SET failed for key %s, skipping cache write", key)

    async def delete(self, key: str) -> None:
        try:
            await self._redis.delete(key)
        except (RedisError, OSError):
            logger.warning("Redis DELETE failed for key %s, skipping", key)
