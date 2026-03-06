"""Unit tests for Cache protocol implementations."""

import time
from unittest.mock import AsyncMock, patch

import pytest

from kingpi.services.cache import InMemoryTTLCache, RedisTTLCache


# --- InMemoryTTLCache ---


async def test_in_memory_get_miss():
    cache = InMemoryTTLCache()
    assert await cache.get("nonexistent") is None


async def test_in_memory_set_and_get():
    cache = InMemoryTTLCache()
    await cache.set("key1", "value1", ttl_seconds=60)
    assert await cache.get("key1") == "value1"


async def test_in_memory_delete():
    cache = InMemoryTTLCache()
    await cache.set("key1", "value1", ttl_seconds=60)
    await cache.delete("key1")
    assert await cache.get("key1") is None


async def test_in_memory_delete_nonexistent():
    cache = InMemoryTTLCache()
    await cache.delete("nonexistent")  # should not raise


async def test_in_memory_ttl_expiration():
    cache = InMemoryTTLCache()
    with patch("kingpi.services.cache.time") as mock_time:
        mock_time.monotonic.return_value = 100.0
        await cache.set("key1", "value1", ttl_seconds=10)

        mock_time.monotonic.return_value = 109.0
        assert await cache.get("key1") == "value1"

        mock_time.monotonic.return_value = 111.0
        assert await cache.get("key1") is None


async def test_in_memory_max_size_evicts_oldest():
    cache = InMemoryTTLCache(max_size=2)
    await cache.set("a", "1", ttl_seconds=60)
    await cache.set("b", "2", ttl_seconds=60)
    await cache.set("c", "3", ttl_seconds=60)
    assert await cache.get("a") is None
    assert await cache.get("b") == "2"
    assert await cache.get("c") == "3"


async def test_in_memory_overwrite_existing_no_eviction():
    cache = InMemoryTTLCache(max_size=2)
    await cache.set("a", "1", ttl_seconds=60)
    await cache.set("b", "2", ttl_seconds=60)
    await cache.set("a", "updated", ttl_seconds=60)
    assert await cache.get("a") == "updated"
    assert await cache.get("b") == "2"


# --- RedisTTLCache ---


@pytest.fixture
def mock_redis():
    return AsyncMock()


async def test_redis_get_hit(mock_redis):
    mock_redis.get.return_value = b"cached_value"
    cache = RedisTTLCache(mock_redis)
    assert await cache.get("key1") == "cached_value"
    mock_redis.get.assert_awaited_once_with("key1")


async def test_redis_get_miss(mock_redis):
    mock_redis.get.return_value = None
    cache = RedisTTLCache(mock_redis)
    assert await cache.get("key1") is None


async def test_redis_set(mock_redis):
    cache = RedisTTLCache(mock_redis)
    await cache.set("key1", "value1", ttl_seconds=300)
    mock_redis.set.assert_awaited_once_with("key1", "value1", ex=300)


async def test_redis_delete(mock_redis):
    cache = RedisTTLCache(mock_redis)
    await cache.delete("key1")
    mock_redis.delete.assert_awaited_once_with("key1")


async def test_redis_get_connection_error(mock_redis):
    mock_redis.get.side_effect = ConnectionError("Redis down")
    cache = RedisTTLCache(mock_redis)
    assert await cache.get("key1") is None


async def test_redis_set_connection_error(mock_redis):
    mock_redis.set.side_effect = ConnectionError("Redis down")
    cache = RedisTTLCache(mock_redis)
    await cache.set("key1", "value1", ttl_seconds=300)  # should not raise


async def test_redis_delete_connection_error(mock_redis):
    mock_redis.delete.side_effect = ConnectionError("Redis down")
    cache = RedisTTLCache(mock_redis)
    await cache.delete("key1")  # should not raise
