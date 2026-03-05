import asyncio
from datetime import datetime, timezone

import pytest

from pypi_server.services.event_store import InMemoryEventStore


def ts(hour: int = 0, minute: int = 0) -> datetime:
    return datetime(2024, 1, 1, hour, minute, tzinfo=timezone.utc)


class TestRecordAndGetTotal:
    async def test_record_and_get_total(self, event_store: InMemoryEventStore):
        await event_store.record_event("requests", "install", ts(1))
        await event_store.record_event("requests", "install", ts(2))
        await event_store.record_event("requests", "install", ts(3))
        total = await event_store.get_total("requests", "install")
        assert total == 3

    async def test_get_total_unknown_package(self, event_store: InMemoryEventStore):
        total = await event_store.get_total("nonexistent", "install")
        assert total == 0

    async def test_get_total_unknown_event_type(self, event_store: InMemoryEventStore):
        await event_store.record_event("requests", "install", ts())
        total = await event_store.get_total("requests", "uninstall")
        assert total == 0


class TestGetCounts:
    async def test_get_counts_multiple_types(self, event_store: InMemoryEventStore):
        await event_store.record_event("numpy", "install", ts(1))
        await event_store.record_event("numpy", "install", ts(2))
        await event_store.record_event("numpy", "uninstall", ts(3))
        counts = await event_store.get_counts("numpy")
        assert counts["install"] == 2
        assert counts["uninstall"] == 1

    async def test_get_counts_unknown_package(self, event_store: InMemoryEventStore):
        counts = await event_store.get_counts("nonexistent")
        assert counts == {}

    async def test_get_counts_only_install(self, event_store: InMemoryEventStore):
        await event_store.record_event("pandas", "install", ts())
        counts = await event_store.get_counts("pandas")
        assert counts.get("install") == 1
        assert counts.get("uninstall", 0) == 0


class TestGetLast:
    async def test_get_last_returns_latest_timestamp(self, event_store: InMemoryEventStore):
        early = ts(1)
        middle = ts(5)
        late = ts(10)
        await event_store.record_event("flask", "install", middle)
        await event_store.record_event("flask", "install", early)
        await event_store.record_event("flask", "install", late)
        last = await event_store.get_last("flask", "install")
        assert last == late

    async def test_get_last_unknown_package_returns_none(self, event_store: InMemoryEventStore):
        last = await event_store.get_last("unknown_pkg", "install")
        assert last is None

    async def test_get_last_unknown_event_type_returns_none(self, event_store: InMemoryEventStore):
        await event_store.record_event("django", "install", ts())
        last = await event_store.get_last("django", "uninstall")
        assert last is None

    async def test_get_last_single_event(self, event_store: InMemoryEventStore):
        t = ts(7)
        await event_store.record_event("celery", "install", t)
        last = await event_store.get_last("celery", "install")
        assert last == t


class TestIsolation:
    async def test_record_event_different_packages_isolated(self, event_store: InMemoryEventStore):
        await event_store.record_event("pkg-a", "install", ts(1))
        await event_store.record_event("pkg-a", "install", ts(2))
        await event_store.record_event("pkg-b", "install", ts(3))

        assert await event_store.get_total("pkg-a", "install") == 2
        assert await event_store.get_total("pkg-b", "install") == 1

    async def test_install_and_uninstall_are_independent(self, event_store: InMemoryEventStore):
        await event_store.record_event("scipy", "install", ts(1))
        await event_store.record_event("scipy", "install", ts(2))
        await event_store.record_event("scipy", "uninstall", ts(3))

        assert await event_store.get_total("scipy", "install") == 2
        assert await event_store.get_total("scipy", "uninstall") == 1


class TestConcurrency:
    async def test_concurrent_record_events(self, event_store: InMemoryEventStore):
        package = "concurrent-pkg"
        event_type = "install"
        n = 100

        await asyncio.gather(
            *[event_store.record_event(package, event_type, ts(i % 24)) for i in range(n)]
        )

        total = await event_store.get_total(package, event_type)
        assert total == n

    async def test_concurrent_different_packages(self, event_store: InMemoryEventStore):
        packages = [f"pkg-{i}" for i in range(10)]
        events_per_package = 10

        await asyncio.gather(
            *[
                event_store.record_event(pkg, "install", ts(j))
                for pkg in packages
                for j in range(events_per_package)
            ]
        )

        for pkg in packages:
            total = await event_store.get_total(pkg, "install")
            assert total == events_per_package


class TestEdgeCases:
    async def test_empty_counts_returns_empty_dict(self, event_store: InMemoryEventStore):
        counts = await event_store.get_counts("empty-pkg")
        assert isinstance(counts, dict)
        assert len(counts) == 0

    async def test_same_timestamp_multiple_events(self, event_store: InMemoryEventStore):
        t = ts(12)
        await event_store.record_event("boto3", "install", t)
        await event_store.record_event("boto3", "install", t)
        await event_store.record_event("boto3", "install", t)
        assert await event_store.get_total("boto3", "install") == 3
        assert await event_store.get_last("boto3", "install") == t
