"""
Event store service: records and queries package install/uninstall events.

This module defines the `EventStore` protocol — a structural interface that
any event store implementation must satisfy. The `PostgresEventStore` in
`pg_event_store.py` is the production implementation.

**Protocol (structural typing)**: `EventStore` is a `Protocol` class, not a
base class. Any class that implements the same methods automatically satisfies
the protocol — no explicit `class Foo(EventStore)` inheritance needed.
This is Python's structural subtyping (duck typing with type-checker support).
"""

from datetime import datetime
from typing import Protocol

class EventStore(Protocol):
    """Structural interface for any event store implementation.

    `Protocol` from `typing` defines a structural interface: any class
    with these four async methods will be accepted wherever `EventStore`
    is expected — no inheritance required. This is different from ABCs
    (Abstract Base Classes) which require explicit inheritance.

    All methods are `async` because the PostgreSQL implementation
    involves I/O, and we want the interface to reflect that.
    """

    async def record_event(self, package: str, event_type: str, timestamp: datetime) -> None: ...
    async def get_counts(self, package: str) -> dict[str, int]: ...
    async def get_last(self, package: str, event_type: str) -> datetime | None: ...
    async def get_total(self, package: str, event_type: str) -> int: ...
