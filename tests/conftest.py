"""
Shared pytest fixtures for the entire test suite.

`conftest.py` is a special pytest file: any fixtures defined here are
automatically available to all test files in the same directory and below —
no import needed. pytest discovers and injects them by name.

This file sets up three categories of shared fixtures:
1. Real service instances (e.g., `event_store`) — for integration/unit tests
2. Mock service instances (e.g., `mock_event_store`) — for API tests that need
   predictable responses without running real business logic
3. HTTP test clients (e.g., `client`) — for making requests to the FastAPI app
   in-process, with no real network involved

Key concepts:
- **pytest fixtures**: Functions decorated with `@pytest.fixture` that set up
  (and optionally tear down) test dependencies. Tests declare what they need
  in their parameter list and pytest injects the right fixture.
- **AsyncMock**: For async functions/methods, you need `AsyncMock` instead of
  `MagicMock`. It returns awaitables so `await store.get_total(...)` works.
- **Dependency overrides**: FastAPI lets you replace any `Depends(...)` target
  at test time via `app.dependency_overrides`. This is the standard way to
  inject mock services into route handlers without changing production code.
- **ASGITransport**: Lets httpx send requests directly to the ASGI app (in
  memory) rather than over a real TCP socket. Faster and no port conflicts.
- **`async with ... yield`**: For fixtures that need cleanup (like closing the
  HTTP client), use `yield` — code before `yield` is setup, code after is teardown.
"""
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

from kingpi.app import create_app
from kingpi.dependencies import get_event_store
from kingpi.services.event_store import InMemoryEventStore


@pytest.fixture
def event_store():
    """Provide a fresh InMemoryEventStore for each test.

    Using the real implementation (not a mock) — suitable for unit tests
    that exercise the store's actual logic. Each test gets a new instance
    so state doesn't leak between tests.
    """
    return InMemoryEventStore()


@pytest.fixture
def mock_event_store():
    """Provide an AsyncMock that mimics EventStore for API-layer tests.

    API route tests shouldn't depend on the real store implementation.
    Using a mock here isolates route logic (validation, HTTP status codes,
    response shape) from storage logic. The mock's return values are set
    to realistic defaults so routes have something to work with.

    `AsyncMock` is required for async methods — regular `MagicMock` would
    return a coroutine that never resolves when awaited.
    """
    store = AsyncMock()
    store.record_event.return_value = None
    store.get_counts.return_value = {"install": 5, "uninstall": 1}
    store.get_total.return_value = 5
    store.get_last.return_value = None
    return store


@pytest.fixture
def mock_pypi_client():
    """Provide an AsyncMock that mimics PyPIClient for route-level tests.

    Tests for routes that call PyPI should not make real HTTP requests —
    that would make tests slow, flaky (network-dependent), and hard to
    control. This mock returns canned data so tests are deterministic.
    """
    client = AsyncMock()
    client.fetch_package_info.return_value = {
        "info": {"name": "requests", "version": "2.31.0"},
        "releases": {"2.31.0": []},
    }
    return client


@pytest.fixture
async def client(mock_event_store):
    """Provide an async HTTP client wired to the FastAPI app for API tests.

    This fixture:
    1. Creates the FastAPI app
    2. Overrides the `get_event_store` dependency with the mock store
    3. Wraps the app in an httpx AsyncClient using ASGITransport (in-process)
    4. Yields the client for the test to use
    5. Cleans up dependency overrides after the test completes

    The `async with ... yield` pattern ensures the client's __aexit__ is
    called (closing connections) even if the test raises an exception.
    `app.dependency_overrides.clear()` prevents mock state from leaking
    into other tests.
    """
    app = create_app()
    # Override the real dependency with our mock — FastAPI will inject the
    # mock wherever `Depends(get_event_store)` appears in route handlers.
    app.dependency_overrides[get_event_store] = lambda: mock_event_store
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    # Teardown: clear overrides so other test fixtures get fresh dependencies
    app.dependency_overrides.clear()
