"""
Centralized configuration using Pydantic Settings.

WHY Pydantic Settings?
----------------------
`BaseSettings` from `pydantic-settings` automatically reads values from
environment variables, giving us:

1. **Type safety** — env vars are always strings, but Pydantic coerces them
   to the declared Python type (str, int, bool, etc.) and raises clear errors
   if the value is invalid.
2. **Defaults** — each field has a sensible default so the app runs without
   any env vars set (great for local development).
3. **Validation** — all config is validated at startup, failing fast rather
   than crashing later with a confusing KeyError.
4. **Documentation** — the class itself serves as a single source of truth
   for every configurable value in the application.

HOW env vars map to fields:
  `env_prefix = "KINGPI_"` means the field `database_url` is read from
  the environment variable `KINGPI_DATABASE_URL` (uppercased automatically).
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration — all fields can be overridden via env vars."""

    # Connection string for the async database engine.
    # Default uses SQLite with aiosqlite for zero-config local development.
    # For PostgreSQL: "postgresql+asyncpg://user:pass@localhost:5432/kingpi"
    database_url: str = "sqlite+aiosqlite:///./kingpi.db"

    # Which EventStore implementation to use: "memory" or "postgres".
    # "memory" is fast and requires no external DB — perfect for local dev and tests.
    # "postgres" uses the database_url above for persistent, multi-worker safe storage
    # with atomic counter updates via INSERT ... ON CONFLICT DO UPDATE.
    storage_backend: str = "memory"

    # URL prefix for all API routes (enables versioned APIs like /api/v1/...).
    api_prefix: str = "/api/v1"

    # When True, enables detailed error responses and debug middleware.
    debug: bool = False
    pypi_request_timeout_seconds: float = 10.0
    redis_url: str = "redis://localhost:6379/0"  # validated at connection time by redis-py
    pypi_cache_ttl_seconds: int = 300

    # `model_config` is Pydantic's way of configuring the model class itself
    # (not an instance). `env_prefix` tells BaseSettings to look for env vars
    # prefixed with "KINGPI_" — e.g., KINGPI_DEBUG=true sets debug=True.
    model_config = {"env_prefix": "KINGPI_"}
