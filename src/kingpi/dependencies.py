from functools import lru_cache

from kingpi.config import Settings
from kingpi.services.event_store import EventStore, InMemoryEventStore
from kingpi.services.pypi_client import PyPIClient


@lru_cache
def get_settings() -> Settings:
    return Settings()


_event_store = InMemoryEventStore()


def get_event_store() -> EventStore:
    return _event_store


_pypi_client: PyPIClient | None = None


def set_pypi_client(client: PyPIClient) -> None:
    global _pypi_client
    _pypi_client = client


def get_pypi_client() -> PyPIClient:
    if _pypi_client is None:
        raise RuntimeError("PyPIClient not initialized — is lifespan wired?")
    return _pypi_client
