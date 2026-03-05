"""
FastAPI route handlers for the package query endpoints.

This module provides read-side endpoints for looking up package information
from PyPI and querying recorded event statistics.
"""
from fastapi import APIRouter, Depends, HTTPException

from kingpi.dependencies import get_event_store, get_pypi_client
from kingpi.services.event_store import EventStore
from kingpi.services.pypi_client import PackageNotFoundError, PyPIClient

router = APIRouter()


@router.get("/package/{name}")
async def get_package(
    name: str,
    pypi: PyPIClient = Depends(get_pypi_client),
    store: EventStore = Depends(get_event_store),
):
    try:
        data = await pypi.fetch_package_info(name)
    except PackageNotFoundError:
        raise HTTPException(status_code=404, detail=f"Package '{name}' not found")

    counts = await store.get_counts(name)
    events = {}
    for event_type in ["install", "uninstall"]:
        last = await store.get_last(name, event_type)
        events[event_type] = {
            "count": counts.get(event_type, 0),
            "last": last.isoformat() if last else None,
        }

    return {
        "name": name,
        "info": data.get("info", {}),
        "releases": list(data.get("releases", {}).keys()),
        "events": events,
    }


@router.get("/package/{name}/event/{event_type}/total")
async def get_event_total(
    name: str,
    event_type: str,
    store: EventStore = Depends(get_event_store),
):
    total = await store.get_total(name, event_type)
    return {"total": total}


@router.get("/package/{name}/event/{event_type}/last")
async def get_event_last(
    name: str,
    event_type: str,
    store: EventStore = Depends(get_event_store),
):
    last = await store.get_last(name, event_type)
    return {"last": last.isoformat() if last else None}
