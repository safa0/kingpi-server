"""
Event store service: records and queries package install/uninstall events.

This module introduces two important design patterns:

1. **Protocol (structural typing)**: `EventStore` is a `Protocol` class, not a
   base class. Any class that implements the same methods automatically satisfies
   the protocol — no explicit `class Foo(EventStore)` inheritance needed.
   This is Python's structural subtyping (duck typing with type-checker support).
   It lets us swap implementations (in-memory for tests, database for production)
   without changing the interface or any code that depends on it.

2. **Event store pattern**: Rather than storing only the current state (e.g.,
   just a counter), an event store persists each individual event with its
   timestamp. This makes it possible to answer time-based queries like
   "what was the last install timestamp?" and supports audit trails.
   The tradeoff is higher storage usage vs. richer query capability.
"""

from datetime import datetime
from typing import Protocol, TypedDict


class EventEntry(TypedDict):
    """Type-safe structure for per-(package, event_type) aggregate data."""

    count: int
    last: datetime | None


class EventStore(Protocol):
    """Structural interface for any event store implementation.

    `Protocol` from `typing` defines a structural interface: any class
    with these four async methods will be accepted wherever `EventStore`
    is expected — no inheritance required. This is different from ABCs
    (Abstract Base Classes) which require explicit inheritance.

    All methods are `async` because real implementations (e.g., PostgreSQL)
    will involve I/O, and we want the interface to reflect that from the start.
    """

    async def record_event(self, package: str, event_type: str, timestamp: datetime) -> None: ...
    async def get_counts(self, package: str) -> dict[str, int]: ...
    async def get_last(self, package: str, event_type: str) -> datetime | None: ...
    async def get_total(self, package: str, event_type: str) -> int: ...


class InMemoryEventStore:
    """In-memory event store using plain dicts.

    No asyncio.Lock needed: with a single uvicorn worker, all async code
    runs on one event loop thread. Dict operations here are synchronous
    (no `await` between read and write), so no interleaving can occur.
    Multiple workers don't share memory anyway (separate processes).
    """

    def __init__(self) -> None:
        self._data: dict[str, dict[str, EventEntry]] = {}

    async def record_event(self, package: str, event_type: str, timestamp: datetime) -> None:
        pkg = self._data.setdefault(package, {})
        entry = pkg.get(event_type, EventEntry(count=0, last=None))
        new_last = timestamp if (entry["last"] is None or timestamp > entry["last"]) else entry["last"]
        pkg[event_type] = EventEntry(count=entry["count"] + 1, last=new_last)

    async def get_counts(self, package: str) -> dict[str, int]:
        pkg = self._data.get(package, {})
        return {et: info["count"] for et, info in pkg.items()}

    async def get_last(self, package: str, event_type: str) -> datetime | None:
        return self._data.get(package, {}).get(event_type, EventEntry(count=0, last=None))["last"]

    async def get_total(self, package: str, event_type: str) -> int:
        return self._data.get(package, {}).get(event_type, EventEntry(count=0, last=None))["count"]
