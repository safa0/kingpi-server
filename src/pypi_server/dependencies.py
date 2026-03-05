from functools import lru_cache

from pypi_server.config import Settings
from pypi_server.services.event_store import EventStore, InMemoryEventStore


@lru_cache
def get_settings() -> Settings:
    return Settings()


_event_store = InMemoryEventStore()


def get_event_store() -> EventStore:
    return _event_store
