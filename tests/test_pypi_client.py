"""
Unit tests for PyPIClient.

These tests verify that `PyPIClient.fetch_package_info` correctly handles the
range of responses the real PyPI API can return: success, not found, server
errors, and network timeouts.

Mocking strategy:
- We do NOT make real HTTP requests to pypi.org. Real network calls would make
  tests slow, flaky (depends on internet), and hard to trigger error scenarios
  (you can't force pypi.org to return a 500 error on demand).
- Instead, we mock `httpx.AsyncClient` using `AsyncMock(spec=httpx.AsyncClient)`.
  The `spec` argument ensures the mock only exposes methods that the real class
  has — this catches typos like `mock.gett(...)` at test time.
- Individual responses are mocked with `MagicMock(spec=httpx.Response)`. We set
  `status_code` and `json.return_value` to simulate specific API responses.

TDD phase: RED — these tests are written before the implementation exists.
They will all fail until `fetch_package_info` is properly implemented.
"""
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

from kingpi.services.pypi_client import (
    PackageNotFoundError,
    PyPIClient,
    PyPIUpstreamError,
)


# Module-level constant: realistic PyPI JSON API response shape.
# Defined once and reused across tests to avoid repetition and keep tests
# focused on behaviour rather than data setup.
SAMPLE_PACKAGE_DATA = {
    "info": {"name": "requests", "version": "2.31.0", "summary": "HTTP library"},
    "releases": {"2.31.0": [], "2.30.0": []},
    "urls": [],
}


@pytest.fixture
def mock_httpx_client():
    """Create an AsyncMock mimicking httpx.AsyncClient.

    `AsyncMock` is needed because `client.get(...)` is an async method —
    tests need to `await` it. `spec=httpx.AsyncClient` constrains the mock
    to only the methods that really exist on AsyncClient.
    """
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def pypi_client(mock_httpx_client):
    """Create a PyPIClient injected with the mock HTTP client.

    This fixture depends on `mock_httpx_client` — pytest automatically
    resolves and injects it. Both fixtures are available to any test
    that lists `pypi_client` in its parameters.
    """
    return PyPIClient(client=mock_httpx_client)


async def test_fetch_package_info_success(pypi_client, mock_httpx_client):
    """Successful 200 response returns dict with 'info' and 'releases' keys."""
    # Arrange: set up a fake 200 response with realistic JSON data
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_PACKAGE_DATA
    # When `client.get(...)` is called, return our fake response
    mock_httpx_client.get.return_value = mock_response

    # Act: call the method under test
    result = await pypi_client.fetch_package_info("requests")

    # Assert: verify the returned dict has the expected structure
    assert "info" in result
    assert "releases" in result
    assert result["info"]["name"] == "requests"


async def test_fetch_package_info_not_found(pypi_client, mock_httpx_client):
    """404 response raises PackageNotFoundError."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_httpx_client.get.return_value = mock_response

    # `pytest.raises` as a context manager asserts that the block raises
    # the specified exception. The test fails if the exception is NOT raised.
    with pytest.raises(PackageNotFoundError):
        await pypi_client.fetch_package_info("nonexistent-package-xyz")


async def test_fetch_package_info_timeout(pypi_client, mock_httpx_client):
    """Timeout propagates as httpx.TimeoutException."""
    # `side_effect` makes the mock raise an exception when called,
    # simulating a network timeout without any real network involved.
    mock_httpx_client.get.side_effect = httpx.TimeoutException("Request timed out")

    with pytest.raises(httpx.TimeoutException):
        await pypi_client.fetch_package_info("requests")


async def test_fetch_package_info_server_error(pypi_client, mock_httpx_client):
    """500 response raises PyPIUpstreamError."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 500
    mock_httpx_client.get.return_value = mock_response

    with pytest.raises(PyPIUpstreamError):
        await pypi_client.fetch_package_info("requests")


@pytest.mark.parametrize(
    "invalid_name",
    [
        "",
        "../../../etc/passwd",
        "foo bar",
        "pkg?q=1",
        "pkg#fragment",
        ".leading-dot",
        "-leading-dash",
        "trailing-dot.",
        "trailing-dash-",
        "...",
        "---",
    ],
)
async def test_fetch_package_info_rejects_invalid_names(pypi_client, invalid_name):
    """Invalid package names raise ValueError before any HTTP call."""
    with pytest.raises(ValueError, match="Invalid package name"):
        await pypi_client.fetch_package_info(invalid_name)


@pytest.mark.integration
async def test_fetch_real_package_from_pypi():
    """Integration: fetch 'fastapi' from real pypi.org and verify response shape."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as http_client:
        client = PyPIClient(client=http_client)
        data = await client.fetch_package_info("text2digits")

    assert data["info"]["name"] == "text2digits"
    assert isinstance(data["info"]["version"], str)
    assert len(data["releases"]) > 0


@pytest.mark.integration
async def test_fetch_nonexistent_package_from_pypi():
    """Integration: confirm real pypi.org returns 404 for a nonexistent package."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as http_client:
        client = PyPIClient(client=http_client)
        with pytest.raises(PackageNotFoundError):
            await client.fetch_package_info("zzz-nonexistent-pkg-12345678")
