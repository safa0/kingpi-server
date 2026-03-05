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
    app = FastAPI(
        title="KingPi",
        description="Lightweight PyPI package analytics server",
        version="0.1.0",
        lifespan=lifespan,
    )

    return app


app = create_app()
