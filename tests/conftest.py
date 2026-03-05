import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

from pypi_server.app import create_app
from pypi_server.dependencies import get_event_store
from pypi_server.services.event_store import InMemoryEventStore


@pytest.fixture
def event_store():
    return InMemoryEventStore()


@pytest.fixture
def mock_event_store():
    store = AsyncMock()
    store.record_event.return_value = None
    store.get_counts.return_value = {"install": 5, "uninstall": 1}
    store.get_total.return_value = 5
    store.get_last.return_value = None
    return store


@pytest.fixture
def mock_pypi_client():
    client = AsyncMock()
    client.fetch_package_info.return_value = {
        "info": {"name": "requests", "version": "2.31.0"},
        "releases": {"2.31.0": []},
    }
    return client


@pytest.fixture
async def client(mock_event_store):
    app = create_app()
    app.dependency_overrides[get_event_store] = lambda: mock_event_store
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
