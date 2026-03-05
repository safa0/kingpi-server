from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from pypi_server.app import create_app


@pytest.fixture
def mock_event_store():
    store = AsyncMock()
    store.record_event.return_value = None
    return store


@pytest.fixture
async def client(mock_event_store):
    app = create_app()
    # Override dependencies here once dependency injection exists
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


VALID_PAYLOAD = {
    "timestamp": "2026-03-05T10:00:00Z",
    "package": "requests",
    "type": "install",
}


async def test_post_event_success(client):
    response = await client.post("/api/v1/event", json=VALID_PAYLOAD)
    assert response.status_code == 201


async def test_post_event_invalid_type(client):
    payload = {**VALID_PAYLOAD, "type": "download"}
    response = await client.post("/api/v1/event", json=payload)
    assert response.status_code == 422


async def test_post_event_missing_fields(client):
    response = await client.post("/api/v1/event", json={})
    assert response.status_code == 422


async def test_post_event_invalid_package_name_empty(client):
    payload = {**VALID_PAYLOAD, "package": ""}
    response = await client.post("/api/v1/event", json=payload)
    assert response.status_code == 422


async def test_post_event_invalid_package_name_special_chars(client):
    payload = {**VALID_PAYLOAD, "package": "foo bar!!"}
    response = await client.post("/api/v1/event", json=payload)
    assert response.status_code == 422


async def test_post_event_records_to_store(client, mock_event_store):
    # Once DI is wired, mock_event_store.record_event should be called.
    # For now, just verify the endpoint exists and returns correct status.
    response = await client.post("/api/v1/event", json=VALID_PAYLOAD)
    assert response.status_code == 201
    # TODO: assert mock_event_store.record_event.called once DI is wired


async def test_post_event_future_timestamp(client):
    # Design decision: accept future timestamps (no server-side restriction)
    future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    payload = {**VALID_PAYLOAD, "timestamp": future}
    response = await client.post("/api/v1/event", json=payload)
    assert response.status_code == 201
