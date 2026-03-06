# Phase 2: PyPI Metadata Caching

## Goal
Cache PyPI JSON API responses in Redis so multiple FastAPI workers share a single cache with automatic TTL expiration. Eliminate redundant upstream calls for the same package within the TTL window.

## Architecture

```
Request -> PackageService -> PyPICacheClient -> Redis (hit?) -> return cached
                                    |
                                    └-> (miss?) -> PyPIClient -> PyPI API
                                                       |
                                                       └-> store in Redis with TTL -> return
```

### Key Components

| Component | File | Responsibility |
|-----------|------|----------------|
| `Cache` protocol | `services/cache.py` | Abstract async cache interface (`get`, `set`, `delete`) |
| `RedisTTLCache` | `services/cache.py` | Redis-backed implementation using `redis.asyncio` |
| `InMemoryTTLCache` | `services/cache.py` | Dict-based implementation for tests and local dev |
| `PyPICacheClient` | `services/pypi_cache_client.py` | Cache-aside wrapper around `PyPIClient`, specific to PyPI metadata |
| Config additions | `config.py` | `redis_url`, `pypi_cache_ttl_seconds`, `pypi_cache_max_size` |
| DI wiring | `dependencies.py` | Provide `PyPICacheClient` instead of raw `PyPIClient` to services |
| Lifespan | `app.py` | Redis connection open/close in FastAPI lifespan |

### Cache Protocol

```python
class Cache(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ttl_seconds: int) -> None: ...
    async def delete(self, key: str) -> None: ...
```

Stores serialized JSON strings. Serialization/deserialization is the caller's responsibility (keeps the protocol generic).

### PackageInfoFetcher Protocol

Both `PyPIClient` and `PyPICacheClient` implement a shared protocol so the service layer is decoupled from caching:

```python
class PackageInfoFetcher(Protocol):
    async def fetch_package_info(self, package: str) -> dict: ...
```

`package_service.get_package_summary` types its parameter as `PackageInfoFetcher`, not `PyPIClient` or `PyPICacheClient`. This makes the "drop-in replacement" claim true at the type level.

### PyPICacheClient

```python
class PyPICacheClient:
    def __init__(self, client: PyPIClient, cache: Cache, ttl_seconds: int) -> None: ...
    async def fetch_package_info(self, package: str) -> dict: ...
```

- Implements `PackageInfoFetcher` protocol
- Cache key format: `pypi:package:{normalized_name}`
- On cache miss: fetches from PyPI, serializes to JSON, stores with TTL
- On cache hit: deserializes and returns
- On PyPI error (404, 5xx): does NOT cache errors — only successful responses are cached
- Package name normalization: lowercase, replace `.`/`-`/`_` with `-` (PEP 503) before building cache key. Add `normalize_package_name()` utility in `pypi_cache_client.py`

### Why PyPICacheClient, not a generic CachedClient

This cache is specifically for PyPI metadata. Event counters (Phase 4) will have different invalidation strategies (write-through vs TTL). Naming it `PyPICacheClient` makes the scope explicit and avoids a premature abstraction that tries to serve both use cases.

## Config Additions

```python
# config.py - new fields
redis_url: str = "redis://localhost:6379/0"
pypi_cache_ttl_seconds: int = 300  # 5 minutes
```

Env vars: `KINGPI_REDIS_URL`, `KINGPI_PYPI_CACHE_TTL_SECONDS`

Note: `pypi_cache_max_size` removed from Settings — it's only relevant to `InMemoryTTLCache` and is passed directly to its constructor (default 1000). No need to expose it as global config.

## Dependency Wiring

```python
# dependencies.py
def get_pypi_cache_client() -> PyPICacheClient:
    # Returns PyPICacheClient wrapping PyPIClient + Cache
    ...
```

DI migration:
- `get_pypi_cache_client()` **replaces** `get_pypi_client()` as the dependency used by route handlers
- `get_pypi_client()` remains but is only used internally by `get_pypi_cache_client()`
- Route handler in `packages.py` updated: `Depends(get_pypi_client)` -> `Depends(get_pypi_cache_client)`
- `package_service.get_package_summary` parameter typed as `PackageInfoFetcher` (not `PyPIClient` or `PyPICacheClient`)

## Dependencies

Add to `pyproject.toml`:
- `redis>=5.0` (includes `redis.asyncio`)

Dev/test: no Redis needed — `InMemoryTTLCache` is used in tests via DI override.

## Files to Create/Modify

### New files
- `src/kingpi/services/cache.py` — `Cache` protocol, `RedisTTLCache`, `InMemoryTTLCache`
- `src/kingpi/services/pypi_cache_client.py` — `PyPICacheClient`, `PackageInfoFetcher` protocol, `normalize_package_name()`
- `tests/test_cache.py` — Unit tests for both cache implementations
- `tests/test_pypi_cache_client.py` — Tests for cache-aside logic (hit, miss, error passthrough)

### Modified files
- `src/kingpi/config.py` — Add Redis URL and cache TTL settings
- `src/kingpi/dependencies.py` — Wire `PyPICacheClient` as the dependency
- `src/kingpi/services/package_service.py` — Accept `PyPICacheClient` instead of `PyPIClient`
- `src/kingpi/app.py` — Redis connection lifecycle in lifespan
- `pyproject.toml` — Add `redis` dependency

## Test Strategy

All tests use `InMemoryTTLCache` — no Redis in CI.

1. **Unit: `test_cache.py`**
   - `InMemoryTTLCache`: get/set/delete, TTL expiration, key miss returns None
   - `RedisTTLCache`: same tests but with mocked `redis.asyncio` client

2. **Unit: `test_pypi_cache_client.py`**
   - Cache miss -> calls PyPIClient -> stores result -> returns data
   - Cache hit -> returns cached data, PyPIClient NOT called
   - PyPI 404 -> raises PackageNotFoundError, nothing cached
   - PyPI 5xx -> raises PyPIUpstreamError, nothing cached
   - TTL expiration -> re-fetches from PyPI
   - Package name normalization: `Flask-RESTful` and `flask_restful` hit same cache key

3. **Unit: `test_cache.py` — Redis failure degradation**
   - Mock Redis raises `ConnectionError` on `get` -> `RedisTTLCache` returns `None` (cache miss), logs warning
   - Mock Redis raises `ConnectionError` on `set` -> `RedisTTLCache` no-ops, logs warning
   - System continues to work uncached when Redis is down

4. **Integration: existing `test_packages.py` / `test_e2e.py`**
   - Override `get_pypi_cache_client` with InMemoryTTLCache-backed instance
   - Existing tests should pass without changes (same API contract)

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Redis over in-memory | Redis | Multi-worker requirement — shared cache |
| Cache protocol | Yes | Swap Redis/InMemory without changing callers |
| Serialize as JSON string | Yes | Redis stores strings; safe serialization |
| Don't cache errors | Correct | Transient failures shouldn't poison the cache |
| TTL only, no explicit invalidation | Yes | PyPI metadata changes infrequently; TTL is sufficient |
| Wrapper class over decorator | Yes | Explicit, testable, debuggable |
| `PackageInfoFetcher` protocol | Yes | Decouples service from cache/client implementations |
| Graceful Redis degradation | Yes | `RedisTTLCache` catches `ConnectionError`, degrades to uncached |
| PEP 503 name normalization | Yes | Prevents duplicate cache entries for same package |

## Cache Stampede

Acknowledged: if N concurrent requests hit a cold cache for the same package, all N will call PyPI before any response is cached. For PyPI metadata with 5-min TTL this is low-risk (small window, PyPI handles the load). Future mitigation if needed: single-flight / lock-per-key pattern in `PyPICacheClient`.

## Redis Failure Handling

`RedisTTLCache` catches `redis.ConnectionError` (and `redis.TimeoutError`) in both `get` and `set`:
- `get` returns `None` (treated as cache miss)
- `set` / `delete` become no-ops
- Logs warning on each failure

The system degrades to uncached PyPI calls — never fails a user request due to Redis being down.

## Reuse in Phase 4

The `Cache` protocol and `RedisTTLCache` implementation will be reused for counter caching in Phase 4. Only the invalidation strategy differs (write-invalidation for counters vs pure TTL for PyPI metadata).
