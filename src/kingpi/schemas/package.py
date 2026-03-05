"""
Pydantic schemas for PyPI package data responses.

This schema mirrors the subset of PyPI's JSON API response that we expose
to our clients. Using `dict[str, Any]` for `info` and `releases` keeps
the schema flexible — PyPI's response structure is large and evolving,
so we avoid tightly coupling to every field.
"""

from typing import Any

from pydantic import BaseModel


class PackageResponse(BaseModel):
    """Simplified representation of a PyPI package for API responses."""

    name: str
    # `dict[str, Any]` accepts arbitrary nested JSON — useful when proxying
    # third-party API data that we don't need to validate field-by-field.
    info: dict[str, Any] = {}
    releases: dict[str, Any] = {}
