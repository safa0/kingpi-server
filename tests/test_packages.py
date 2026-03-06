"""
API integration tests for the package query endpoints.

These tests cover the read-side API: looking up package information from PyPI
and querying recorded event statistics. They differ from test_events.py in that:
- They need TWO mocked dependencies (PyPI client + event store)
- They use a local `test_client` fixture that overrides both dependencies

This file demonstrates a common pattern in FastAPI testing: creating a
fixture-local HTTP client when you need a specific combination of dependency
overrides that isn't shared across the whole test suite.

Why a local fixture instead of conftest.py?
The global `client` fixture only overrides `get_event_store`. These tests also
need to mock `get_pypi_client` so we don't make real HTTP calls to PyPI.
Defining `test_client` locally keeps this setup self-contained.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from kingpi.app import create_app
from kingpi.dependencies import get_event_store, get_pypi_client


# Realistic but minimal PyPI API response — used by the mock_pypi_client fixture
# (defined in conftest.py) to return canned data for any package lookup.
SAMPLE_PYPI_DATA = {
    "info": {"name": "requests", "version": "2.31.0"},
    "releases": {"2.31.0": []},
}


@pytest.fixture
async def test_client(mock_pypi_client, mock_event_store):
    """Async HTTP client with BOTH PyPI client and event store mocked.

    This fixture depends on two fixtures from conftest.py:
    - `mock_pypi_client`: prevents real PyPI HTTP calls
    - `mock_event_store`: provides predictable event data

    Both are overridden via `dependency_overrides` so FastAPI injects the
    mocks wherever `Depends(get_pypi_client)` or `Depends(get_event_store)`
    appear in route handlers.
    """
    app = create_app()
    app.dependency_overrides[get_event_store] = lambda: mock_event_store
    app.dependency_overrides[get_pypi_client] = lambda: mock_pypi_client
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    # Always clear overrides after the test — prevents state leaking into
    # other fixtures that create the same app instance.
    app.dependency_overrides.clear()


async def test_get_package_success(test_client):
    """GET /api/v1/package/requests returns PackageResponse with PyPI info."""
    response = await test_client.get("/api/v1/package/requests")
    assert response.status_code == 200
    data = response.json()
    # Assert the response shape — not the exact values — so the test doesn't
    # break when the mock data changes. Structure > content for API contracts.
    assert data["name"] == "requests"
    assert data["info"]["name"] == "requests"
    assert data["info"]["version"] == "2.31.0"
    assert isinstance(data["releases"], list)
    assert "events" in data
    # info should be the full PyPI dict, not a curated subset
    assert isinstance(data["info"], dict)


async def test_get_package_not_found_on_pypi(test_client):
    """GET /api/v1/package/nonexistent returns 404.

    The mock_pypi_client in conftest.py returns data for "requests" but the
    route should raise PackageNotFoundError for unknown packages, which the
    route handler should translate into a 404 HTTP response.
    """
    response = await test_client.get("/api/v1/package/nonexistent-package-xyz-abc")
    assert response.status_code == 404


async def test_get_package_event_total(test_client):
    """GET /api/v1/package/requests/event/install/total returns bare integer."""
    response = await test_client.get("/api/v1/package/requests/event/install/total")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert response.text == "5"


async def test_get_package_event_last(test_client):
    """GET /api/v1/package/requests/event/install/last returns bare timestamp or empty."""
    response = await test_client.get("/api/v1/package/requests/event/install/last")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"


async def test_get_package_event_total_no_events(test_client):
    """Returns "0" when no events recorded.

    The mock uses `side_effect` to return 5 for "requests" and 0 for any
    other package (see conftest.py). This tests the zero-case contract.
    """
    response = await test_client.get("/api/v1/package/new-package/event/install/total")
    assert response.status_code == 200
    assert response.text == "0"
