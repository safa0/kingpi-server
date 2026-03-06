"""
End-to-end tests exercising the full request lifecycle.

Unlike unit/integration tests that mock dependencies, these tests use
an AsyncMock event store and only mock the PyPI client (to avoid
network calls). This verifies that routes, services, schemas, and the
event store work together correctly through realistic multi-step flows.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

from kingpi.app import create_app
from kingpi.dependencies import get_event_store, get_pypi_cache_client
from kingpi.services.pypi_client import PackageNotFoundError


PYPI_PACKAGES = {
    "requests": {
        "info": {
            "name": "requests",
            "version": "2.31.0",
            "summary": "HTTP for Humans",
            "author": "Kenneth Reitz",
            "license": "Apache-2.0",
            "home_page": "https://requests.readthedocs.io",
        },
        "releases": {"2.31.0": [], "2.30.0": []},
    },
    "fastapi": {
        "info": {
            "name": "fastapi",
            "version": "0.135.1",
            "summary": "FastAPI framework",
            "author": None,
            "license": None,
            "home_page": None,
        },
        "releases": {"0.135.1": [], "0.135.0": []},
    },
}


class FakePyPIClient:
    """Fake PyPI client returning canned data without network calls."""

    async def fetch_package_info(self, package: str) -> dict:
        if package in PYPI_PACKAGES:
            return PYPI_PACKAGES[package]
        raise PackageNotFoundError(package)


@pytest.fixture
async def e2e_client():
    """HTTP client with mock event store and fake PyPI client."""
    app = create_app()
    store = AsyncMock()
    store.record_event.return_value = None
    store.get_counts.return_value = {}
    store.get_total.return_value = 0
    store.get_last.return_value = None
    pypi = FakePyPIClient()
    app.dependency_overrides[get_event_store] = lambda: store
    app.dependency_overrides[get_pypi_cache_client] = lambda: pypi
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        client._mock_store = store  # type: ignore[attr-defined]
        yield client
    app.dependency_overrides.clear()


async def test_health_check(e2e_client):
    response = await e2e_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_post_event_returns_201(e2e_client):
    """Recording an event for a valid package returns 201."""
    r = await e2e_client.post("/api/v1/event", json={
        "package": "requests",
        "type": "install",
        "timestamp": "2026-03-01T10:00:00Z",
    })
    assert r.status_code == 201
    e2e_client._mock_store.record_event.assert_awaited_once()


async def test_query_package_returns_pypi_info_and_events(e2e_client):
    """GET package combines PyPI info with event stats from the store."""
    from datetime import datetime, timezone
    store = e2e_client._mock_store
    store.get_counts.return_value = {"install": 2, "uninstall": 1}
    store.get_last.side_effect = lambda pkg, et: (
        datetime(2026, 3, 2, 10, tzinfo=timezone.utc) if et == "install"
        else datetime(2026, 3, 3, 12, tzinfo=timezone.utc)
    )

    r = await e2e_client.get("/api/v1/package/requests")
    assert r.status_code == 200
    data = r.json()

    assert data["name"] == "requests"
    assert data["info"]["version"] == "2.31.0"
    assert data["info"]["summary"] == "HTTP for Humans"
    assert set(data["releases"]) == {"2.31.0", "2.30.0"}

    assert data["events"]["install"]["count"] == 2
    assert data["events"]["install"]["last"] == "2026-03-02T10:00:00Z"
    assert data["events"]["uninstall"]["count"] == 1
    assert data["events"]["uninstall"]["last"] == "2026-03-03T12:00:00Z"


async def test_query_totals_and_last(e2e_client):
    """Verify per-type total and last endpoints delegate to event store."""
    from datetime import datetime, timezone
    store = e2e_client._mock_store
    store.get_total.side_effect = lambda pkg, et: 3 if et == "install" else 0
    store.get_last.return_value = datetime(2026, 3, 3, 8, tzinfo=timezone.utc)

    r = await e2e_client.get("/api/v1/package/fastapi/event/install/total")
    assert r.status_code == 200
    assert r.text == "3"

    r = await e2e_client.get("/api/v1/package/fastapi/event/install/last")
    assert r.status_code == 200
    assert r.text == "2026-03-03T08:00:00+00:00"

    store.get_total.side_effect = None
    store.get_total.return_value = 0
    r = await e2e_client.get("/api/v1/package/fastapi/event/uninstall/total")
    assert r.status_code == 200
    assert r.text == "0"


async def test_post_event_nonexistent_package_rejected(e2e_client):
    """Events for packages not on PyPI should be rejected with 404."""
    r = await e2e_client.post("/api/v1/event", json={
        "package": "nonexistent-pkg-xyz",
        "type": "install",
        "timestamp": "2026-03-06T00:00:00Z",
    })
    assert r.status_code == 404
    assert "not found on PyPI" in r.json()["detail"]


async def test_get_package_not_on_pypi(e2e_client):
    """GET for a package not on PyPI returns 404."""
    r = await e2e_client.get("/api/v1/package/nonexistent-pkg-xyz")
    assert r.status_code == 404


async def test_package_with_null_fields(e2e_client):
    """Packages with null author/license/home_page should still work."""
    r = await e2e_client.post("/api/v1/event", json={
        "package": "fastapi",
        "type": "install",
        "timestamp": "2026-03-06T00:00:00Z",
    })
    assert r.status_code == 201

    r = await e2e_client.get("/api/v1/package/fastapi")
    assert r.status_code == 200
    data = r.json()
    # Full PyPI info dict is passed through — these fields are null in the fake
    assert data["info"]["author"] is None
    assert data["info"]["license"] is None
    assert data["info"]["home_page"] is None


async def test_get_package_returns_zero_counts_by_default(e2e_client):
    """A package with no recorded events shows zero counts."""
    r = await e2e_client.get("/api/v1/package/fastapi")
    assert r.status_code == 200
    assert r.json()["events"]["install"]["count"] == 0
