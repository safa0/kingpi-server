"""Unit tests for RedisTTLCache."""

from unittest.mock import AsyncMock

import pytest
from redis import RedisError

from kingpi.services.cache import RedisTTLCache


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


async def test_redis_get_string_response(mock_redis):
    mock_redis.get.return_value = "cached_value"
    cache = RedisTTLCache(mock_redis)
    assert await cache.get("key1") == "cached_value"


async def test_redis_get_connection_error(mock_redis):
    mock_redis.get.side_effect = RedisError("Redis down")
    cache = RedisTTLCache(mock_redis)
    assert await cache.get("key1") is None


async def test_redis_set_connection_error(mock_redis):
    mock_redis.set.side_effect = RedisError("Redis down")
    cache = RedisTTLCache(mock_redis)
    await cache.set("key1", "value1", ttl_seconds=300)  # should not raise


async def test_redis_delete_connection_error(mock_redis):
    mock_redis.delete.side_effect = RedisError("Redis down")
    cache = RedisTTLCache(mock_redis)
    await cache.delete("key1")  # should not raise
