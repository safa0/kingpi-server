"""
Package query service — assembles package info from PyPI + event store.

This service layer keeps route handlers thin. Routes validate input and
return responses; this module contains the business logic for combining
data from multiple sources (PyPI metadata + local event statistics).
"""

from kingpi.schemas.event import EventType
from kingpi.schemas.package import PackageEventStats, PackageInfo, PackageSummaryResponse
from kingpi.services.event_store import EventStore
from kingpi.services.pypi_client import PyPIClient


async def get_package_summary(
    name: str,
    pypi: PyPIClient,
    store: EventStore,
) -> PackageSummaryResponse:
    """Fetch PyPI metadata and combine with local event statistics."""
    data = await pypi.fetch_package_info(name)

    raw_info = data.get("info", {})
    info = PackageInfo(
        name=raw_info.get("name", name),
        version=raw_info.get("version", ""),
        summary=raw_info.get("summary", ""),
        author=raw_info.get("author", ""),
        license=raw_info.get("license", ""),
        home_page=raw_info.get("home_page", ""),
    )

    counts = await store.get_counts(name)
    events: dict[EventType, PackageEventStats] = {}
    for event_type in EventType:
        last = await store.get_last(name, event_type)
        events[event_type] = PackageEventStats(
            count=counts.get(event_type, 0),
            last=last,
        )

    return PackageSummaryResponse(
        name=name,
        info=info,
        releases=list(data.get("releases", {}).keys()),
        events=events,
    )
