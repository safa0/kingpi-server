import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock

from pypi_server.app import create_app


SAMPLE_PYPI_DATA = {
    "info": {"name": "requests", "version": "2.31.0"},
    "releases": {"2.31.0": []},
}


@pytest.fixture
def mock_pypi_client():
    client = AsyncMock()
    client.fetch_package_info.return_value = SAMPLE_PYPI_DATA
    return client


@pytest.fixture
def mock_event_store():
    store = AsyncMock()
    store.get_counts.return_value = {"install": 5, "uninstall": 1}
    store.get_total.return_value = 5
    store.get_last.return_value = None
    return store


@pytest.fixture
async def test_client(mock_pypi_client, mock_event_store):
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def test_get_package_success(test_client):
    """GET /api/v1/package/requests returns PackageResponse with PyPI info + event data."""
    response = await test_client.get("/api/v1/package/requests")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "info" in data
    assert "releases" in data
    assert "events" in data


async def test_get_package_not_found_on_pypi(test_client):
    """GET /api/v1/package/nonexistent returns 404."""
    response = await test_client.get("/api/v1/package/nonexistent-package-xyz-abc")
    assert response.status_code == 404


async def test_get_package_event_total(test_client):
    """GET /api/v1/package/requests/event/install/total returns {"total": N}."""
    response = await test_client.get("/api/v1/package/requests/event/install/total")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert isinstance(data["total"], int)


async def test_get_package_event_last(test_client):
    """GET /api/v1/package/requests/event/install/last returns {"last": ...}."""
    response = await test_client.get("/api/v1/package/requests/event/install/last")
    assert response.status_code == 200
    data = response.json()
    assert "last" in data


async def test_get_package_event_total_no_events(test_client):
    """Returns {"total": 0} when no events recorded."""
    response = await test_client.get("/api/v1/package/new-package/event/install/total")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
