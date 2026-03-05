from functools import lru_cache

from pypi_server.config import Settings
from pypi_server.services.event_store import EventStore, InMemoryEventStore
from pypi_server.services.pypi_client import PyPIClient


@lru_cache
def get_settings() -> Settings:
    return Settings()


_event_store = InMemoryEventStore()


def get_event_store() -> EventStore:
    return _event_store


def get_pypi_client() -> PyPIClient:
    raise NotImplementedError("PyPIClient requires lifespan wiring")
