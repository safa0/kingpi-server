"""
Pydantic schemas for package API responses.

The ``info`` field passes through the full PyPI JSON API ``info`` dict
so clients get every field PyPI provides. We use ``dict[str, Any]`` to
avoid coupling to PyPI's evolving schema.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from kingpi.schemas.event import EventType


class PackageEventStats(BaseModel):
    """Aggregate event statistics for a single event type."""

    count: int = 0
    last: datetime | None = None


class PackageSummaryResponse(BaseModel):
    """Response schema for GET /api/v1/package/{name}."""

    name: str
    info: dict[str, Any]
    # Deprecated by PyPI — may be removed in a future API response.
    # See: https://docs.pypi.org/api/json/
    releases: list[str] = []
    events: dict[EventType, PackageEventStats]
