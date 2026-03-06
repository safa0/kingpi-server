"""
Async cache protocol and implementations.

Defines a minimal `Cache` protocol for TTL-based key-value caching, with two
implementations:
- `RedisTTLCache`: production cache backed by Redis
- `InMemoryTTLCache`: dict-based cache for tests and local dev

The protocol stores serialized strings — callers handle serialization.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Protocol

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
        except Exception:
            logger.warning("Redis GET failed for key %s, treating as cache miss", key)
            return None

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            await self._redis.set(key, value, ex=ttl_seconds)
        except Exception:
            logger.warning("Redis SET failed for key %s, skipping cache write", key)

    async def delete(self, key: str) -> None:
        try:
            await self._redis.delete(key)
        except Exception:
            logger.warning("Redis DELETE failed for key %s, skipping", key)


class InMemoryTTLCache:
    """Dict-based TTL cache for tests and single-worker local dev.

    Entries expire based on monotonic clock timestamps. No background cleanup;
    expired entries are evicted lazily on `get`. Max size is bounded by LRU-style
    eviction of the oldest entry when full.
    """

    def __init__(self, max_size: int = 1000) -> None:
        self._max_size = max_size
        self._store: dict[str, tuple[str, float]] = {}

    async def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        if len(self._store) >= self._max_size and key not in self._store:
            oldest_key = next(iter(self._store))
            del self._store[oldest_key]
        self._store[key] = (value, time.monotonic() + ttl_seconds)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)
