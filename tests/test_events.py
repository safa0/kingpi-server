from datetime import datetime, timedelta, timezone


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
    response = await client.post("/api/v1/event", json=VALID_PAYLOAD)
    assert response.status_code == 201
    mock_event_store.record_event.assert_called_once()


async def test_post_event_future_timestamp(client):
    future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    payload = {**VALID_PAYLOAD, "timestamp": future}
    response = await client.post("/api/v1/event", json=payload)
    assert response.status_code == 201
