import pytest
from pypi_server.services.event_store import InMemoryEventStore


@pytest.fixture
def event_store():
    return InMemoryEventStore()
