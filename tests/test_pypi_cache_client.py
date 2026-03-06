"""Unit tests for PyPICacheClient and normalize_package_name."""

import json
from unittest.mock import AsyncMock

import pytest

from kingpi.services.pypi_client import PackageNotFoundError, PyPIUpstreamError
from kingpi.services.pypi_cache_client import PyPICacheClient, normalize_package_name


SAMPLE_DATA = {"info": {"name": "requests", "version": "2.31.0"}, "releases": {"2.31.0": []}}


# --- normalize_package_name ---


@pytest.mark.parametrize(
    "input_name, expected",
    [
        ("requests", "requests"),
        ("Flask-RESTful", "flask-restful"),
        ("flask_restful", "flask-restful"),
        ("My.Package", "my-package"),
        ("UPPER", "upper"),
        ("a--b__c..d", "a-b-c-d"),
    ],
)
def test_normalize_package_name(input_name, expected):
    assert normalize_package_name(input_name) == expected


# --- PyPICacheClient ---


@pytest.fixture
def mock_pypi():
    client = AsyncMock()
    client.fetch_package_info.return_value = SAMPLE_DATA
    return client


@pytest.fixture
def cache():
    mock = AsyncMock()
    mock.get.return_value = None
    return mock


@pytest.fixture
def cached_client(mock_pypi, cache):
    return PyPICacheClient(client=mock_pypi, cache=cache, ttl_seconds=300)


async def test_cache_miss_fetches_from_pypi(cached_client, mock_pypi, cache):
    result = await cached_client.fetch_package_info("requests")
    assert result == SAMPLE_DATA
    mock_pypi.fetch_package_info.assert_awaited_once_with("requests")
    cache.set.assert_awaited_once()


async def test_cache_hit_skips_pypi(mock_pypi, cache):
    cache.get.return_value = json.dumps(SAMPLE_DATA)
    cached_client = PyPICacheClient(client=mock_pypi, cache=cache, ttl_seconds=300)

    result = await cached_client.fetch_package_info("requests")
    assert result == SAMPLE_DATA
    mock_pypi.fetch_package_info.assert_not_awaited()


async def test_normalized_names_share_cache(mock_pypi, cache):
    cache.get.return_value = json.dumps(SAMPLE_DATA)
    cached_client = PyPICacheClient(client=mock_pypi, cache=cache, ttl_seconds=300)

    await cached_client.fetch_package_info("Flask-RESTful")
    await cached_client.fetch_package_info("flask_restful")

    cache.get.assert_any_await("pypi:package:flask-restful")
    mock_pypi.fetch_package_info.assert_not_awaited()


async def test_404_not_cached(cached_client, mock_pypi):
    mock_pypi.fetch_package_info.side_effect = PackageNotFoundError("nope")

    with pytest.raises(PackageNotFoundError):
        await cached_client.fetch_package_info("nope")

    mock_pypi.fetch_package_info.side_effect = PackageNotFoundError("nope")
    with pytest.raises(PackageNotFoundError):
        await cached_client.fetch_package_info("nope")

    assert mock_pypi.fetch_package_info.await_count == 2


async def test_upstream_error_not_cached(cached_client, mock_pypi):
    mock_pypi.fetch_package_info.side_effect = PyPIUpstreamError("pkg", 503)

    with pytest.raises(PyPIUpstreamError):
        await cached_client.fetch_package_info("pkg")

    mock_pypi.fetch_package_info.side_effect = PyPIUpstreamError("pkg", 503)
    with pytest.raises(PyPIUpstreamError):
        await cached_client.fetch_package_info("pkg")

    assert mock_pypi.fetch_package_info.await_count == 2
