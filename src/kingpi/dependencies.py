"""
FastAPI dependency injection (DI) providers.

WHY dependency injection?
-------------------------
FastAPI's `Depends()` system lets route handlers declare *what they need*
without knowing *how to create it*. This module defines the "provider"
functions that FastAPI calls to supply those dependencies.

HOW it works in a route:
    from fastapi import Depends
    from kingpi.dependencies import get_settings

    @router.get("/health")
    async def health(settings: Settings = Depends(get_settings)):
        ...

    # Or, using the modern `Annotated` style (preferred):
    from typing import Annotated
    SettingsDep = Annotated[Settings, Depends(get_settings)]

    @router.get("/health")
    async def health(settings: SettingsDep):
        ...

Benefits:
1. **Testability** — tests can override any dependency with `app.dependency_overrides`
   to inject mocks or test doubles without patching.
2. **Separation of concerns** — routes don't know about config files, DB
   connections, or HTTP client setup.
3. **Lifecycle control** — FastAPI manages when dependencies are created and
   (for generator deps) cleaned up.
"""

from functools import lru_cache

import redis.asyncio as aioredis

from kingpi.config import Settings
from kingpi.services.event_store import EventStore, InMemoryEventStore
from kingpi.services.pypi_cache_client import PyPICacheClient


# @lru_cache ensures Settings() is only instantiated once (singleton pattern).
# Without this, every request would re-read environment variables and
# re-validate config — wasteful for values that never change at runtime.
@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings (singleton)."""
    return Settings()


# Module-level instance — acts as an in-memory singleton for the event store.
# In production, this would be replaced by a database-backed implementation.
_event_store = InMemoryEventStore()


def get_event_store() -> EventStore:
    """Provide the event store dependency to route handlers."""
    return _event_store


_redis_client: aioredis.Redis | None = None


def set_redis_client(client: aioredis.Redis | None) -> None:
    global _redis_client
    _redis_client = client


def get_redis_client() -> aioredis.Redis:
    """Provide the shared Redis client — requires lifespan wiring."""
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized — is lifespan wired?")
    return _redis_client


_pypi_cache_client: PyPICacheClient | None = None


def set_pypi_cache_client(client: PyPICacheClient | None) -> None:
    global _pypi_cache_client
    _pypi_cache_client = client


def get_pypi_cache_client() -> PyPICacheClient:
    """Provide the cached PyPI client — the default dependency for routes."""
    if _pypi_cache_client is None:
        raise RuntimeError("PyPICacheClient not initialized — is lifespan wired?")
    return _pypi_cache_client
