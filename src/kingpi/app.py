"""
Application factory for the KingPi FastAPI server.

WHY a factory function?
-----------------------
Using `create_app()` instead of a bare `app = FastAPI()` is called the
"application factory" pattern. Benefits:

1. **Testing** — each test can call `create_app()` to get a fresh, isolated app
   instance, avoiding shared state between tests.
2. **Configuration** — you can pass different settings (e.g. test DB URL) to the
   factory without monkey-patching module-level globals.
3. **Lifespan management** — the factory is the natural place to wire up
   startup/shutdown logic (DB connections, HTTP clients).

FastAPI concepts used here:
- `title`, `description`, `version` populate the auto-generated OpenAPI docs
  (visible at /docs when running the server).
- `lifespan` is an async context manager that runs setup before the app starts
  serving and teardown when it shuts down.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI

from kingpi.api.events import router as events_router
from kingpi.api.health import router as health_router
from kingpi.api.packages import router as packages_router
from kingpi.config import Settings
from kingpi.db.engine import build_engine
from kingpi.dependencies import get_settings, set_event_store, set_pypi_cache_client
from kingpi.services.cache import RedisTTLCache
from kingpi.services.event_store import InMemoryEventStore
from kingpi.services.pg_event_store import PostgresEventStore
from kingpi.services.pypi_cache_client import PyPICacheClient
from kingpi.services.pypi_client import PyPIClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage the lifecycle of shared resources (DB, Redis, HTTP client).

    The lifespan context manager is the right place to initialize and tear
    down resources that are shared across all requests. FastAPI calls this
    once at startup (before first request) and once at shutdown.
    """
    settings: Settings = get_settings()

    # --- Event store setup ---
    # Choose implementation based on config. The rest of the app doesn't
    # know or care which one is active — both satisfy the EventStore protocol.
    engine = None
    if settings.storage_backend == "postgres":
        engine, session_factory = build_engine(settings.database_url)
        set_event_store(PostgresEventStore(session_factory))
    else:
        set_event_store(InMemoryEventStore())

    # --- HTTP + Redis + PyPI cache setup ---
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(settings.pypi_request_timeout_seconds),
    ) as http_client:
        redis_client = aioredis.from_url(settings.redis_url)
        try:
            cache = RedisTTLCache(redis_client)
            cached_client = PyPICacheClient(
                client=PyPIClient(client=http_client),
                cache=cache,
                ttl_seconds=settings.pypi_cache_ttl_seconds,
            )
            set_pypi_cache_client(cached_client)
            yield
        finally:
            set_pypi_cache_client(None)
            set_event_store(None)
            await redis_client.aclose()
            if engine is not None:
                await engine.dispose()


def create_app() -> FastAPI:
    """Build and return a configured FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title="KingPi",
        description="Lightweight PyPI package analytics server",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(health_router)
    app.include_router(events_router, prefix=settings.api_prefix)
    app.include_router(packages_router, prefix=settings.api_prefix)

    return app


# Module-level instance used by ASGI servers (e.g. `uvicorn kingpi.app:app`).
# The ASGI server imports this variable by name to serve the application.
app = create_app()
