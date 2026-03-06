"""
API integration tests for the POST /api/v1/event endpoint.

These are integration tests — they exercise the full HTTP request/response cycle
through FastAPI, including:
- Request body parsing and Pydantic validation
- Route handler logic
- Dependency injection (mock_event_store is injected via conftest.py)
- HTTP response status codes

The `client` fixture (from conftest.py) provides an httpx.AsyncClient that
communicates with the FastAPI app in-process (no real server, no open port).

Testing strategy here: we test the HTTP contract, not the store internals.
The event store is mocked so tests are fast and isolated from storage logic.
"""
from datetime import datetime, timedelta, timezone


# A valid payload used as a baseline — individual tests copy and mutate it
# using dict unpacking: `{**VALID_PAYLOAD, "type": "download"}` creates a
# new dict with all VALID_PAYLOAD keys, overriding just "type". This pattern
# avoids modifying shared state and keeps each test self-contained.
VALID_PAYLOAD = {
    "timestamp": "2026-03-05T10:00:00Z",
    "package": "requests",
    "type": "install",
}


async def test_post_event_success(client):
    # `client` comes from conftest.py — pytest injects it by name.
    # 201 Created is the correct status for a resource that was just recorded.
    response = await client.post("/api/v1/event", json=VALID_PAYLOAD)
    assert response.status_code == 201


async def test_post_event_invalid_type(client):
    # "download" is not a valid event type. FastAPI/Pydantic should reject it
    # with 422 Unprocessable Entity before the route handler even runs.
    payload = {**VALID_PAYLOAD, "type": "download"}
    response = await client.post("/api/v1/event", json=payload)
    assert response.status_code == 422


async def test_post_event_missing_fields(client):
    # Empty body — all required fields are absent. FastAPI returns 422 with
    # a detailed list of validation errors per field.
    response = await client.post("/api/v1/event", json={})
    assert response.status_code == 422


async def test_post_event_invalid_package_name_empty(client):
    # Empty string is technically valid JSON but should fail field validation
    # (min_length constraint on the package field).
    payload = {**VALID_PAYLOAD, "package": ""}
    response = await client.post("/api/v1/event", json=payload)
    assert response.status_code == 422


async def test_post_event_nonexistent_package(client):
    # Package doesn't exist on PyPI — the route verifies via PyPI client
    # before recording, so this should return 404.
    payload = {**VALID_PAYLOAD, "package": "nonexistent-package-xyz"}
    response = await client.post("/api/v1/event", json=payload)
    assert response.status_code == 404


async def test_post_event_records_to_store(client, mock_event_store):
    # Verify the route actually calls the store — not just that it returns 201.
    # `assert_called_once()` fails if record_event was never called or called
    # more than once. This is a behavioural assertion on the mock.
    response = await client.post("/api/v1/event", json=VALID_PAYLOAD)
    assert response.status_code == 201
    mock_event_store.record_event.assert_called_once()


async def test_post_event_future_timestamp(client):
    # The API should accept future timestamps (pip clients may have clock skew,
    # or events might be batched and submitted after the fact).
    future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    payload = {**VALID_PAYLOAD, "timestamp": future}
    response = await client.post("/api/v1/event", json=payload)
    assert response.status_code == 201
