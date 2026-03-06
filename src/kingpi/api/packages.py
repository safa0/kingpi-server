"""
FastAPI route handlers for the package query endpoints.

This module provides read-side endpoints for looking up package information
from PyPI and querying recorded event statistics. Routes are kept thin —
business logic lives in the service layer (package_service.py).
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from kingpi.dependencies import get_event_store, get_pypi_client
from kingpi.schemas.event import EventType
from kingpi.schemas.package import PackageSummaryResponse
from kingpi.services.event_store import EventStore
from kingpi.services.package_service import get_package_summary
from kingpi.services.pypi_client import PackageNotFoundError, PyPIClient

router = APIRouter()


@router.get("/package/{name}", response_model=PackageSummaryResponse)
async def get_package(
    name: str,
    pypi: PyPIClient = Depends(get_pypi_client),
    store: EventStore = Depends(get_event_store),
):
    try:
        return await get_package_summary(name, pypi, store)
    except PackageNotFoundError:
        raise HTTPException(status_code=404, detail=f"Package '{name}' not found")


@router.get("/package/{name}/event/{event_type}/total", response_class=PlainTextResponse)
async def get_event_total(
    name: str,
    event_type: EventType,
    store: EventStore = Depends(get_event_store),
):
    total = await store.get_total(name, event_type)
    return str(total)


@router.get("/package/{name}/event/{event_type}/last", response_class=PlainTextResponse)
async def get_event_last(
    name: str,
    event_type: EventType,
    store: EventStore = Depends(get_event_store),
):
    last = await store.get_last(name, event_type)
    return last.isoformat() if last else ""
