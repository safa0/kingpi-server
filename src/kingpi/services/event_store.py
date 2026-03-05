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
from typing import Protocol


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
    """Stub — tests should fail (RED phase).

    TDD note: This is intentionally empty so tests fail first (RED phase).
    The GREEN phase will add the actual in-memory implementation using plain
    Python dicts/lists — no database, no external dependencies, fast for tests.

    An in-memory store is also useful in production for early-stage services
    where persistence across restarts isn't required yet.
    """
    pass
