import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

from kingpi.services.pypi_client import (
    PackageNotFoundError,
    PyPIClient,
    PyPIUpstreamError,
)


SAMPLE_PACKAGE_DATA = {
    "info": {"name": "requests", "version": "2.31.0", "summary": "HTTP library"},
    "releases": {"2.31.0": [], "2.30.0": []},
    "urls": [],
}


@pytest.fixture
def mock_httpx_client():
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def pypi_client(mock_httpx_client):
    return PyPIClient(client=mock_httpx_client)


async def test_fetch_package_info_success(pypi_client, mock_httpx_client):
    """Successful 200 response returns dict with 'info' and 'releases' keys."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_PACKAGE_DATA
    mock_httpx_client.get.return_value = mock_response

    result = await pypi_client.fetch_package_info("requests")

    assert "info" in result
    assert "releases" in result
    assert result["info"]["name"] == "requests"


async def test_fetch_package_info_not_found(pypi_client, mock_httpx_client):
    """404 response raises PackageNotFoundError."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_httpx_client.get.return_value = mock_response

    with pytest.raises(PackageNotFoundError):
        await pypi_client.fetch_package_info("nonexistent-package-xyz")


async def test_fetch_package_info_timeout(pypi_client, mock_httpx_client):
    """Timeout propagates as httpx.TimeoutException."""
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
