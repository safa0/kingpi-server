# Architecture

## High-Level System Architecture

```mermaid
graph LR
    Client([Client])
    KingPi[KingPi Server<br/>FastAPI]
    PyPI[(pypi.org)]
    PG[(PostgreSQL)]
    Redis[(Redis)]

    Client -->|HTTP| KingPi
    KingPi -->|JSON API| PyPI
    KingPi -->|asyncpg| PG
    KingPi -->|aioredis| Redis
```

## Internal Layer Architecture

```mermaid
graph TD
    subgraph API["API Layer (routes)"]
        health["health.py<br/>GET /health"]
        events["events.py<br/>POST /api/v1/event"]
        packages["packages.py<br/>GET /api/v1/package/{name}"]
    end

    subgraph Services["Service Layer (business logic)"]
        pkg_svc["package_service.py"]
        cache_client["pypi_cache_client.py<br/>PackageInfoFetcher protocol"]
        pypi_client["pypi_client.py<br/>httpx async"]
        cache["cache.py<br/>Cache protocol + RedisTTLCache"]
        event_store["event_store.py<br/>EventStore protocol"]
        pg_store["pg_event_store.py<br/>PostgreSQL upserts"]
    end

    subgraph Data["Data Layer"]
        engine["db/engine.py<br/>async SQLAlchemy engine"]
        model["models/event.py<br/>PackageEvent ORM"]
    end

    events --> cache_client
    events --> event_store
    packages --> pkg_svc
    pkg_svc --> cache_client
    pkg_svc --> event_store
    cache_client --> pypi_client
    cache_client --> cache
    event_store -.->|protocol| pg_store
    pg_store --> engine
    engine --> model
```

## Request Flow: POST /api/v1/event

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Route (events.py)
    participant P as PyPICacheClient
    participant Redis as Redis
    participant PyPI as pypi.org
    participant S as PostgresEventStore
    participant PG as PostgreSQL

    C->>R: POST /api/v1/event (JSON body)
    Note over R: Pydantic validates EventIn

    R->>P: fetch_package_info(package)
    P->>Redis: GET pypi:package:{name}
    alt Cache HIT
        Redis-->>P: cached JSON
    else Cache MISS
        Redis-->>P: None
        P->>PyPI: GET /pypi/{name}/json
        PyPI-->>P: package metadata
        P->>Redis: SET key (TTL 300s)
    end
    P-->>R: package info

    R->>S: record_event(package, type, timestamp)
    S->>PG: INSERT ... ON CONFLICT DO UPDATE
    PG-->>S: OK
    S-->>R: done

    R-->>C: 201 {"status": "accepted"}
```

## Request Flow: GET /api/v1/package/{name}

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Route (packages.py)
    participant Svc as package_service
    participant P as PyPICacheClient
    participant Redis as Redis
    participant PyPI as pypi.org
    participant S as PostgresEventStore
    participant PG as PostgreSQL

    C->>R: GET /api/v1/package/{name}
    R->>Svc: get_package_summary(name)

    Svc->>P: fetch_package_info(name)
    P->>Redis: GET pypi:package:{name}
    alt Cache HIT
        Redis-->>P: cached JSON
    else Cache MISS
        Redis-->>P: None
        P->>PyPI: GET /pypi/{name}/json
        PyPI-->>P: metadata
        P->>Redis: SET key (TTL 300s)
    end
    P-->>Svc: package info

    Svc->>S: get_counts(name) + get_last(name, type)
    S->>PG: SELECT count, last_timestamp
    PG-->>S: event stats
    S-->>Svc: counts + timestamps

    Note over Svc: Assemble PackageSummaryResponse
    Svc-->>R: response
    R-->>C: 200 PackageSummaryResponse
```

## Cache-Aside Pattern

```mermaid
flowchart TD
    A[Incoming request] --> B{Redis cache<br/>lookup}
    B -->|HIT| C[Return cached JSON]
    B -->|MISS| D[Call PyPIClient]
    D --> E[Store in Redis<br/>TTL 300s]
    E --> F[Return fresh data]

    style B fill:#f9f,stroke:#333
    style C fill:#bfb,stroke:#333
    style F fill:#bfb,stroke:#333
```

## Dependency Injection Wiring

The `lifespan()` context manager in `app.py` wires all dependencies at startup.

```mermaid
graph TD
    subgraph Lifespan["lifespan() startup"]
        engine["build_engine(database_url)"]
        sf["session_factory"]
        pg["PostgresEventStore"]
        http["httpx.AsyncClient"]
        pypi["PyPIClient"]
        redis["aioredis.from_url()"]
        cache["RedisTTLCache"]
        cached["PyPICacheClient"]

        engine --> sf --> pg
        http --> pypi
        redis --> cache
        pypi --> cached
        cache --> cached
    end

    pg -->|set_event_store| DI
    cached -->|set_pypi_cache_client| DI

    subgraph DI["Dependencies (dependencies.py)"]
        get_es["get_event_store()"]
        get_pypi["get_pypi_cache_client()"]
    end

    subgraph Routes["Route Handlers"]
        r1["events.py"]
        r2["packages.py"]
    end

    get_es -->|"Depends()"| r1
    get_es -->|"Depends()"| r2
    get_pypi -->|"Depends()"| r1
    get_pypi -->|"Depends()"| r2
```
