# PyPI Server — Incremental Implementation Plan

## Context
We have a FastAPI scaffold with empty modules. The goal is to build a PyPI analytics server that receives install/uninstall events and serves package info enriched with PyPI metadata. Key architectural decisions: abstract storage (start in-memory, swap to PostgreSQL later), Redis-style caching for counters, TTL-based caching for PyPI metadata, multi-worker safe.

## Incremental Phases

### Phase 1: Core In-Memory — Minimum Viable API
**Goal:** Working `/event` and `/package/{name}` endpoints with in-memory storage. No external dependencies.

Files to create/modify:
- `src/pypi_server/schemas/event.py` — Pydantic models: `EventType` enum (install/uninstall), `EventIn(timestamp: datetime, package: str, type: EventType)` with package name regex validation (`^[a-zA-Z0-9._-]+$`) and ISO 8601 timestamp, `EventSummary(count, last)`
- `src/pypi_server/schemas/package.py` — `PackageResponse(info, releases, events)`
- `src/pypi_server/schemas/error.py` — `ErrorResponse(detail: str, status_code: int)` — consistent error envelope for all error responses
- `src/pypi_server/services/event_store.py` — **Abstract `EventStore` protocol** + `InMemoryEventStore` implementation
  - Protocol methods: `record_event(package, type, timestamp)`, `get_counts(package)`, `get_last(package, type)`, `get_total(package, type)`
  - `InMemoryEventStore` uses `asyncio.Lock` for safe concurrent async access
- `src/pypi_server/services/pypi_client.py` — `fetch_package_info(package)` using `httpx.AsyncClient` to call `https://pypi.python.org/pypi/{package}/json`. Configurable timeout via `pypi_request_timeout_seconds` in config. Raises `PackageNotFoundError` on 404, distinct error on 5xx upstream failures.
- `src/pypi_server/api/events.py` — `POST /event`
- `src/pypi_server/api/packages.py` — `GET /package/{name}`, `GET /package/{name}/event/{type}/total`, `GET /package/{name}/event/{type}/last`
- `src/pypi_server/api/health.py` — `GET /health` — basic health check endpoint
- `src/pypi_server/app.py` — Wire routers, lifespan for httpx client, CORSMiddleware with configurable origins
- `src/pypi_server/dependencies.py` — FastAPI dependency injection for store & client; `Settings` available via `Depends()` for testability
- `.env.example` — Example environment variables
- `tests/conftest.py` — Shared fixtures (async client, mock stores, mock PyPI responses)
- `tests/test_event_store.py`, `tests/test_pypi_client.py`, `tests/test_app.py` — Per-service unit + integration tests with httpx `AsyncClient`; all PyPI calls mocked (never hit real PyPI)

Key design:
- `EventStore` is a **Protocol** so we can swap implementations without changing API code
- `InMemoryEventStore` uses a dict of `{package: {type: {count, last}}}` with `asyncio.Lock` for concurrent safety
- PyPI client is a thin async wrapper with configurable timeout, no caching yet
- All endpoints under `/api/v1` prefix (versioned)
- Dependency injection via FastAPI's `Depends()` so implementations are swappable; `Settings` also injectable via `Depends()` for testability
- `httpx` must be a **runtime dependency** in `pyproject.toml` (not dev-only) since `pypi_client.py` needs it at runtime
- All error responses use the `ErrorResponse` envelope for consistency
- CORSMiddleware configured with origins from settings

### Phase 2: PyPI Metadata Caching (TTL-based)
**Goal:** Cache PyPI responses to avoid hammering upstream. Multi-worker safe via TTL expiry.

Files:
- `src/pypi_server/services/cache.py` — `Cache` protocol + `InMemoryTTLCache` (dict + expiry timestamps)
- Modify `pypi_client.py` — Wrap fetches with cache lookup (cache-aside pattern)
- `src/pypi_server/config.py` — Add `pypi_cache_ttl_seconds: int = 300`

Design: TTL-based invalidation (e.g., 5 min). Each worker has its own cache in-memory mode — acceptable for now. When we add Redis later, it becomes shared.

### Phase 3: PostgreSQL Event Storage
**Goal:** Persistent, multi-worker safe event storage with row-level locking.

Files:
- `src/pypi_server/models/event.py` — SQLAlchemy model: `PackageEvent(id, package, event_type, count, last_timestamp)` — one row per (package, type) pair with atomic counter updates
- `src/pypi_server/services/pg_event_store.py` — `PostgresEventStore` implementing `EventStore` protocol
  - `record_event`: `INSERT ... ON CONFLICT DO UPDATE SET count = count + 1, last_timestamp = ...` (atomic, row-level lock)
  - Read methods: simple SELECT queries
- `src/pypi_server/db/engine.py` — Async SQLAlchemy engine + session factory
- Modify `config.py` — `storage_backend: str = "memory"` toggle
- Modify `dependencies.py` — Factory that returns correct store based on config
- Update `pyproject.toml` — Add `asyncpg`, `alembic` dependencies
- Alembic setup: `alembic init`, migrations directory, initial migration script, CI migration check

Design note: Consider storing raw events in a separate table for audit/time-series alongside the aggregate counter table.

### Phase 4: Redis Counter Cache (Cache-Aside with Write Invalidation)
**Goal:** Fast reads for counters; cache invalidated on every event write.

Files:
- `src/pypi_server/services/redis_cache.py` — Redis-backed cache implementing `Cache` protocol
- Modify `pg_event_store.py` — After `record_event`, invalidate/delete the Redis key for that (package, type)
- On read: check Redis first -> fallback to DB -> populate Redis
- Modify `config.py` — `redis_url`, `counter_cache_enabled`

This ensures cache is always hot: reads come from Redis, writes invalidate stale entries.

### Phase 5: Production Hardening
- Rate limiting (slowapi)
- Structured logging
- Error handling middleware (catch httpx errors from PyPI, DB connection errors)
- Graceful degradation: if PyPI is down, return cached or partial response
- Docker Compose with PostgreSQL + Redis

## Verification Strategy
Each phase is independently testable:
1. `pytest` with httpx `AsyncClient` — no external deps needed for Phase 1-2
2. Phase 3+: Use testcontainers or docker-compose for integration tests
3. Manual: `uvicorn src.pypi_server.app:app --reload` then curl endpoints

## Current State
- Scaffold exists with empty modules
- `pyproject.toml` has FastAPI, uvicorn, SQLAlchemy, pydantic-settings, httpx (dev — must move to runtime)
- No routers wired, no endpoints implemented

## Starting Point
We begin with **Phase 1** — get the API working end-to-end with in-memory storage and mocked PyPI fetches in tests.

## Revision Notes
1. Moved `httpx` from dev to runtime dependency (PyPI client needs it)
2. Added `asyncio.Lock` to `InMemoryEventStore` for concurrent async safety
3. Phase 1 tests must mock httpx responses — never hit real PyPI
4. Added input validation: `EventType` enum, package name regex, ISO 8601 timestamp
5. Moved `GET /health` from Phase 5 to Phase 1
6. Added `tests/conftest.py`, `tests/test_event_store.py`, `tests/test_pypi_client.py`, `tests/test_app.py` to Phase 1
7. Added `ErrorResponse` schema for consistent error envelope
8. Added CORSMiddleware with configurable origins to Phase 1 app wiring
9. PyPI client: configurable timeout, `PackageNotFoundError` on 404, distinct 5xx handling
10. `Settings` injectable via `Depends()` for testability
11. Renamed Phase 4 from "Write-Through Invalidation" to "Cache-Aside with Write Invalidation"
12. Added `.env.example` to Phase 1 file list
13. Expanded Phase 3 with Alembic setup details and raw event storage consideration
