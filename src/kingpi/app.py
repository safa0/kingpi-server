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
from fastapi import FastAPI

from kingpi.api.events import router as events_router
from kingpi.api.health import router as health_router
from kingpi.api.packages import router as packages_router
from kingpi.config import Settings
import redis.asyncio as aioredis

from kingpi.dependencies import (
    get_settings,
    set_pypi_cache_client,
    set_redis_client,
)
from kingpi.services.cache import RedisTTLCache
from kingpi.services.pypi_cache_client import PyPICacheClient
from kingpi.services.pypi_client import PyPIClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = get_settings()
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(settings.pypi_request_timeout_seconds),
    ) as http_client:
        redis_client = aioredis.from_url(settings.redis_url)
        set_redis_client(redis_client)
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
            set_redis_client(None)
            await redis_client.aclose()


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
