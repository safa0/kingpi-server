"""
PostgreSQL-backed EventStore using atomic upserts.

CONCURRENCY: Why this is safe
-------------------------------
The core operation is an "upsert" — INSERT ... ON CONFLICT DO UPDATE.
PostgreSQL guarantees this is atomic at the row level:

  1. It acquires a row-level lock on the conflicting row
  2. Updates count and last_timestamp in a single operation
  3. Releases the lock when the transaction commits

This means multiple FastAPI workers (separate processes) can safely call
record_event() for the same package concurrently — the database serializes
the updates. No application-level locking needed.

WHY raw SQL dialect inserts instead of ORM session.merge()?
------------------------------------------------------------
`session.merge()` does a SELECT then INSERT-or-UPDATE — two round trips and
a race condition window between them. The dialect-level `insert().on_conflict_do_update()`
compiles to a single SQL statement, which is both faster and race-free.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kingpi.models.event import PackageEvent


class PostgresEventStore:
    """EventStore implementation backed by PostgreSQL.

    Satisfies the EventStore protocol via structural typing (duck typing) —
    no explicit inheritance needed. Any class with the same async method
    signatures is accepted wherever EventStore is expected.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record_event(self, package: str, event_type: str, timestamp: datetime) -> None:
        """Atomically increment the counter and update last_timestamp.

        Uses PostgreSQL's INSERT ... ON CONFLICT DO UPDATE (upsert):
        - First request for a (package, event_type) → INSERT with count=1
        - Subsequent requests → UPDATE count = count + 1

        The GREATEST() call ensures last_timestamp only moves forward,
        even if events arrive out of order.
        """
        stmt = (
            insert(PackageEvent)
            .values(
                package=package,
                event_type=event_type,
                count=1,
                last_timestamp=timestamp,
            )
            .on_conflict_do_update(
                constraint="uq_package_event_type",
                set_={
                    "count": PackageEvent.count + 1,
                    "last_timestamp": func.greatest(
                        PackageEvent.last_timestamp, timestamp
                    ),
                },
            )
        )
        async with self._session_factory() as session:
            await session.execute(stmt)
            await session.commit()

    async def get_counts(self, package: str) -> dict[str, int]:
        """Return {event_type: count} for all event types of a package."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(PackageEvent.event_type, PackageEvent.count).where(
                    PackageEvent.package == package
                )
            )
            return {row.event_type: row.count for row in result}

    async def get_last(self, package: str, event_type: str) -> datetime | None:
        """Return the most recent timestamp for a (package, event_type) pair."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(PackageEvent.last_timestamp).where(
                    PackageEvent.package == package,
                    PackageEvent.event_type == event_type,
                )
            )
            row = result.scalar_one_or_none()
            return row

    async def get_total(self, package: str, event_type: str) -> int:
        """Return the total count for a (package, event_type) pair."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(PackageEvent.count).where(
                    PackageEvent.package == package,
                    PackageEvent.event_type == event_type,
                )
            )
            return result.scalar_one_or_none() or 0
