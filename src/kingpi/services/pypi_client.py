"""
PyPI API client service.

This module is responsible for one thing: talking to the public PyPI JSON API
(https://pypi.org/pypi/<package>/json) and returning structured data.

Key patterns to understand here:
- **httpx.AsyncClient**: We use httpx instead of the built-in `urllib` or the
  popular `requests` library because httpx supports async/await natively.
  In an async web server (FastAPI + asyncio), you must use async I/O for HTTP
  calls — blocking I/O (like `requests.get(...)`) would freeze the event loop
  and prevent other requests from being handled concurrently.
- **Dependency injection via constructor**: The client receives an
  `httpx.AsyncClient` instead of creating one internally. This makes the class
  testable — in tests we can pass a mock client without hitting the real network.
- **Domain exceptions**: We define specific exception types so callers can
  handle each failure case (not found vs. upstream error) without inspecting
  raw HTTP status codes.
"""

import re

import httpx


# Custom exceptions give callers precise control over error handling.
# Instead of catching a generic Exception or checking status codes, callers
# can do: `except PackageNotFoundError` to handle 404s specifically.
class PackageNotFoundError(Exception):
    def __init__(self, package: str) -> None:
        self.package = package
        super().__init__(f"Package '{package}' not found on PyPI")


class PyPIUpstreamError(Exception):
    def __init__(self, package: str, status_code: int) -> None:
        self.package = package
        self.status_code = status_code
        super().__init__(f"PyPI returned {status_code} for package '{package}'")


PYPI_BASE_URL = "https://pypi.org/pypi"
_VALID_PACKAGE_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$")


class PyPIClient:
    """HTTP client for the PyPI JSON API.

    The constructor accepts an httpx.AsyncClient rather than creating its own
    session — this is the Dependency Injection pattern. Callers (or FastAPI's
    DI container via the lifespan) are responsible for creating and configuring
    the client (timeouts, base URLs, headers), keeping this class focused
    purely on PyPI-specific logic.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        # Store the injected client as a private attribute (convention: _ prefix)
        self._client = client

    async def fetch_package_info(self, package: str) -> dict:
        """Fetch package metadata from PyPI.

        `async def` + `await` lets the event loop do other work while we
        wait for the network response. Without async, the whole server stalls.
        """
        if not _VALID_PACKAGE_RE.match(package):
            raise ValueError(f"Invalid package name: {package!r}")

        response = await self._client.get(f"{PYPI_BASE_URL}/{package}/json")

        if response.status_code == 200:
            return response.json()
        if response.status_code == 404:
            raise PackageNotFoundError(package)
        raise PyPIUpstreamError(package, response.status_code)
