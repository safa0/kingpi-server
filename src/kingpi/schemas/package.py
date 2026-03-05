"""
Pydantic schemas for package API responses.

Defines a stable API contract for package endpoints. We cherry-pick
specific fields from PyPI's JSON API rather than proxying the full
response — this decouples our API shape from PyPI's evolving schema.
"""

from datetime import datetime

from pydantic import BaseModel

from kingpi.schemas.event import EventType


class PackageInfo(BaseModel):
    """Curated subset of PyPI package metadata."""

    name: str
    version: str
    summary: str | None = None
    author: str | None = None
    license: str | None = None
    home_page: str | None = None


class PackageEventStats(BaseModel):
    """Aggregate event statistics for a single event type."""

    count: int = 0
    last: datetime | None = None


class PackageSummaryResponse(BaseModel):
    """Response schema for GET /api/v1/package/{name}."""

    name: str
    info: PackageInfo
    # Deprecated by PyPI — may be removed in a future API response.
    # See: https://docs.pypi.org/api/json/
    releases: list[str] = []
    events: dict[EventType, PackageEventStats]
