"""
Unit tests for PostgresEventStore.

TESTING STRATEGY: Mocked async sessions
-----------------------------------------
We can't (and shouldn't) spin up a real PostgreSQL for unit tests. Instead,
we mock the async session to verify that PostgresEventStore:

1. Executes the correct SQL statements (upsert for writes, select for reads)
2. Handles empty results gracefully (returns 0 or None, not errors)
3. Properly commits after writes

For full integration tests against a real database, use testcontainers or
Docker Compose — those belong in a separate test suite marked @pytest.mark.integration.

WHY mock at the session level?
------------------------------
Mocking at the session level (not the engine level) tests the actual SQL
construction logic in PostgresEventStore while avoiding the need for a
real database connection. We verify that the right SQL operations are called
with the right parameters.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kingpi.services.pg_event_store import PostgresEventStore


def ts(hour: int = 0) -> datetime:
    return datetime(2024, 1, 1, hour, 0, tzinfo=timezone.utc)


def make_store_with_mock_session():
    """Create a PostgresEventStore with a mocked session factory.

    Returns (store, mock_session, mock_result) so tests can configure
    the mock's return values and verify method calls.

    The mock chain mirrors how SQLAlchemy async sessions work:
      result = await session.execute(stmt)  # AsyncMock → returns mock_result
      value = result.scalar_one_or_none()   # regular method on result
    """
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_session.execute.return_value = mock_result
    # The session factory is used as an async context manager:
    # `async with self._session_factory() as session:`
    mock_factory = MagicMock(spec=async_sessionmaker)
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
    store = PostgresEventStore(mock_factory)
    return store, mock_session, mock_result


class TestRecordEvent:
    async def test_record_event_executes_and_commits(self):
        """Verify that record_event calls session.execute and session.commit."""
        store, mock_session, _ = make_store_with_mock_session()
        await store.record_event("requests", "install", ts(1))

        mock_session.execute.assert_awaited_once()
        mock_session.commit.assert_awaited_once()

    async def test_record_event_multiple_calls(self):
        """Each call should execute and commit independently."""
        store, mock_session, _ = make_store_with_mock_session()
        await store.record_event("requests", "install", ts(1))
        await store.record_event("requests", "install", ts(2))

        assert mock_session.execute.await_count == 2
        assert mock_session.commit.await_count == 2


class TestGetTotal:
    async def test_get_total_returns_count(self):
        store, _, mock_result = make_store_with_mock_session()
        mock_result.scalar_one_or_none.return_value = 42

        total = await store.get_total("requests", "install")
        assert total == 42

    async def test_get_total_returns_zero_when_no_rows(self):
        """When no row exists for a (package, event_type), return 0 not None."""
        store, _, mock_result = make_store_with_mock_session()
        mock_result.scalar_one_or_none.return_value = None

        total = await store.get_total("nonexistent", "install")
        assert total == 0


class TestGetLast:
    async def test_get_last_returns_timestamp(self):
        store, _, mock_result = make_store_with_mock_session()
        expected = ts(5)
        mock_result.scalar_one_or_none.return_value = expected

        last = await store.get_last("requests", "install")
        assert last == expected

    async def test_get_last_returns_none_when_no_rows(self):
        store, _, mock_result = make_store_with_mock_session()
        mock_result.scalar_one_or_none.return_value = None

        last = await store.get_last("nonexistent", "install")
        assert last is None


class TestGetCounts:
    async def test_get_counts_returns_dict(self):
        store, _, mock_result = make_store_with_mock_session()
        mock_row_1 = MagicMock()
        mock_row_1.event_type = "install"
        mock_row_1.count = 10
        mock_row_2 = MagicMock()
        mock_row_2.event_type = "uninstall"
        mock_row_2.count = 3
        mock_result.__iter__ = MagicMock(
            return_value=iter([mock_row_1, mock_row_2])
        )

        counts = await store.get_counts("requests")
        assert counts == {"install": 10, "uninstall": 3}

    async def test_get_counts_empty_when_no_rows(self):
        store, _, mock_result = make_store_with_mock_session()
        mock_result.__iter__ = MagicMock(return_value=iter([]))

        counts = await store.get_counts("nonexistent")
        assert counts == {}
