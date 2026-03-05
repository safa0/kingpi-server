"""
Package query service — assembles package info from PyPI + event store.

This service layer keeps route handlers thin. Routes validate input and
return responses; this module contains the business logic for combining
data from multiple sources (PyPI metadata + local event statistics).
"""

from kingpi.schemas.event import EventType
from kingpi.services.event_store import EventStore
from kingpi.services.pypi_client import PyPIClient


async def get_package_summary(
    name: str,
    pypi: PyPIClient,
    store: EventStore,
) -> dict:
    """Fetch PyPI metadata and combine with local event statistics.

    Returns a dict with: name, info, releases (list), and events
    (per event type: count + last timestamp).
    """
    data = await pypi.fetch_package_info(name)

    counts = await store.get_counts(name)
    events = {}
    for event_type in EventType:
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
