"""Tests for the /health/ready deep health check endpoint."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from kingpi.app import create_app
from kingpi.dependencies import (
    get_event_store,
    get_pypi_cache_client,
    get_session_factory,
    get_redis_client,
)


@pytest.fixture
def mock_session_factory():
    """Provide a mock async session factory for health check tests.

    async_sessionmaker() is a regular call returning an async context manager,
    so we use MagicMock for the factory and AsyncMock for the session.
    """
    session = AsyncMock()
    session.execute.return_value = None
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=ctx)
    factory._session = session
    return factory


@pytest.fixture
def mock_redis():
    """Provide a mock Redis client for health check tests."""
    redis = AsyncMock()
    redis.ping.return_value = True
    return redis


@pytest.fixture
async def health_client(mock_event_store, mock_pypi_client, mock_session_factory, mock_redis):
    """Provide a client with session_factory and redis_client overrides."""
    app = create_app()
    app.dependency_overrides[get_event_store] = lambda: mock_event_store
    app.dependency_overrides[get_pypi_cache_client] = lambda: mock_pypi_client
    app.dependency_overrides[get_session_factory] = lambda: mock_session_factory
    app.dependency_overrides[get_redis_client] = lambda: mock_redis
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def test_health_ready_all_healthy(health_client):
    """When both DB and Redis are reachable, return 200 with status healthy."""
    response = await health_client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["dependencies"]["database"]["status"] == "up"
    assert body["dependencies"]["redis"]["status"] == "up"
    assert isinstance(body["dependencies"]["database"]["response_time_ms"], (int, float))
    assert isinstance(body["dependencies"]["redis"]["response_time_ms"], (int, float))


async def test_health_ready_db_down(health_client, mock_session_factory):
    """When DB is unreachable, return 503 with status unhealthy."""
    session = AsyncMock()
    session.execute.side_effect = Exception("connection refused")
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_factory.return_value = ctx

    response = await health_client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unhealthy"
    assert body["dependencies"]["database"]["status"] == "down"
    assert body["dependencies"]["redis"]["status"] == "up"


async def test_health_ready_redis_down(health_client, mock_redis):
    """When Redis is down but DB is up, return 200 with status degraded."""
    mock_redis.ping.side_effect = Exception("connection refused")

    response = await health_client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["dependencies"]["database"]["status"] == "up"
    assert body["dependencies"]["redis"]["status"] == "down"


async def test_health_ready_both_down(health_client, mock_session_factory, mock_redis):
    """When both DB and Redis are down, return 503 with status unhealthy."""
    session = AsyncMock()
    session.execute.side_effect = Exception("connection refused")
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_factory.return_value = ctx
    mock_redis.ping.side_effect = Exception("connection refused")

    response = await health_client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unhealthy"
    assert body["dependencies"]["database"]["status"] == "down"
    assert body["dependencies"]["redis"]["status"] == "down"


async def test_health_liveness_unchanged(health_client):
    """The existing /health liveness probe must remain unchanged."""
    response = await health_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
