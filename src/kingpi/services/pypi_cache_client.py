"""
Cached wrapper for PyPI API calls.

`PyPICacheClient` implements the cache-aside pattern: check cache first,
fall back to the real PyPI client on miss, then store the result. Only
successful responses are cached — errors pass through uncached.

`PackageInfoFetcher` is the protocol both `PyPIClient` and `PyPICacheClient`
implement, allowing the service layer to depend on the abstraction.
"""

from __future__ import annotations

import json
import re
from typing import Protocol

from kingpi.services.cache import Cache


class PackageInfoFetcher(Protocol):
    """Structural interface for anything that fetches PyPI package info."""

    async def fetch_package_info(self, package: str) -> dict: ...


_NORMALIZE_RE = re.compile(r"[-_.]+")


def normalize_package_name(name: str) -> str:
    """Normalize per PEP 503: lowercase, replace runs of [-_.] with a single dash."""
    return _NORMALIZE_RE.sub("-", name).lower()


class PyPICacheClient:
    """Cache-aside wrapper around PyPIClient for PyPI metadata.

    Cache key format: `pypi:package:{normalized_name}`
    Only successful responses are cached. Errors (404, 5xx) pass through.
    """

    def __init__(self, client: PackageInfoFetcher, cache: Cache, ttl_seconds: int) -> None:
        self._client = client
        self._cache = cache
        self._ttl_seconds = ttl_seconds

    async def fetch_package_info(self, package: str) -> dict:
        cache_key = f"pypi:package:{normalize_package_name(package)}"

        cached = await self._cache.get(cache_key)
        if cached is not None:
            return json.loads(cached)

        data = await self._client.fetch_package_info(package)
        await self._cache.set(cache_key, json.dumps(data), self._ttl_seconds)
        return data
