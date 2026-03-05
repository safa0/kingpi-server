from datetime import datetime
from typing import Protocol


class EventStore(Protocol):
    async def record_event(self, package: str, event_type: str, timestamp: datetime) -> None: ...
    async def get_counts(self, package: str) -> dict[str, int]: ...
    async def get_last(self, package: str, event_type: str) -> datetime | None: ...
    async def get_total(self, package: str, event_type: str) -> int: ...


class InMemoryEventStore:
    """Stub — tests should fail (RED phase)."""
    pass
