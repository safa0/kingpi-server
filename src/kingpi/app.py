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

from kingpi.config import Settings
from kingpi.dependencies import get_settings, set_pypi_client
from kingpi.services.pypi_client import PyPIClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = get_settings()
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(settings.pypi_request_timeout_seconds),
    ) as http_client:
        set_pypi_client(PyPIClient(client=http_client))
        yield
        set_pypi_client(None)


def create_app() -> FastAPI:
    """Build and return a configured FastAPI application instance."""
    app = FastAPI(
        title="KingPi",
        description="Lightweight PyPI package analytics server",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Future: register routers here with app.include_router(...)

    return app


# Module-level instance used by ASGI servers (e.g. `uvicorn kingpi.app:app`).
# The ASGI server imports this variable by name to serve the application.
app = create_app()
