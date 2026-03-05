---
name: fastapi-patterns
description: Advanced FastAPI patterns and best practices for production-grade Python APIs
version: 1.0.0
source: web-research-synthesis
triggers:
  - "when working on a FastAPI project"
  - "when creating Python API endpoints"
  - "when setting up a new FastAPI application"
  - "when reviewing FastAPI code"
---

# Advanced FastAPI Patterns

## Project Structure

Use domain-driven organization. Each domain is a package under `src/app/`:

```
src/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Application factory + lifespan
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py      # Shared dependencies (auth, rate limiting)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py        # Aggregates all v1 routers
│   │       ├── packages/        # Domain: each has its own set
│   │       │   ├── __init__.py
│   │       │   ├── router.py
│   │       │   ├── schemas.py
│   │       │   ├── service.py
│   │       │   ├── dependencies.py
│   │       │   ├── constants.py
│   │       │   └── exceptions.py
│   │       └── users/
│   │           └── ...          # Same structure per domain
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # BaseSettings (split per concern)
│   │   ├── security.py          # JWT, hashing
│   │   ├── logging.py           # Structured JSON logging
│   │   └── exceptions.py        # Global exception handlers
│   ├── db/
│   │   ├── __init__.py
│   │   ├── engine.py            # Async engine + sessionmaker
│   │   ├── base.py              # Declarative base + mixins
│   │   └── session.py           # Session dependency
│   ├── models/                  # SQLAlchemy models (shared)
│   │   └── __init__.py
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── request_id.py        # Correlation ID injection
│   │   └── timing.py            # Request duration logging
│   └── utils/
│       └── __init__.py
├── migrations/                  # Alembic
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── tests/
│   ├── conftest.py              # Fixtures: async client, db override
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```

### Key Rules
- One domain = one package with router, schemas, service, dependencies
- API versioning: mount all v1 routers under `/api/v1`
- Keep files 200-400 lines, max 800
- Shared models in `app/models/`, domain-specific schemas in domain package

## Application Factory & Lifespan

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TypedDict

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.db.engine import async_engine, async_session_factory
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.timing import TimingMiddleware


class AppState(TypedDict):
    db_session_factory: async_sessionmaker[AsyncSession]
    http_client: AsyncClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[AppState]:
    async with AsyncClient() as client:
        yield AppState(
            db_session_factory=async_session_factory,
            http_client=client,
        )
    await async_engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        lifespan=lifespan,
    )

    # Middleware (order matters: last added = first executed)
    app.add_middleware(TimingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # Routers
    from app.api.v1.router import api_v1_router
    app.include_router(api_v1_router, prefix="/api/v1")

    # Global exception handlers
    from app.core.exceptions import register_exception_handlers
    register_exception_handlers(app)

    return app


app = create_app()
```

## Async / Sync Rules

```python
# I/O-bound → async def (runs on event loop)
@router.get("/packages/{name}")
async def get_package(name: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Package).where(Package.name == name))
    return result.scalar_one_or_none()

# CPU-bound → sync def (auto runs in threadpool)
@router.post("/packages/{name}/validate")
def validate_package(payload: PackageUpload):
    checksum = hashlib.sha256(payload.content).hexdigest()
    return {"checksum": checksum}

# NEVER do this:
@router.get("/bad")
async def bad_route():
    time.sleep(5)            # Blocks the entire event loop
    result = sync_db_call()  # Blocks the entire event loop
```

### Dependency Async Rule

```python
# BAD: sync dependency runs in threadpool (extra overhead)
def get_http_client(request: Request) -> AsyncClient:
    return request.state.http_client

# GOOD: async dependency runs on event loop (zero overhead)
async def get_http_client(request: Request) -> AsyncClient:
    return request.state.http_client
```

## Dependency Injection

### Database Session

```python
from collections.abc import AsyncGenerator
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    session_factory = request.state.db_session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Chained Dependencies

```python
from typing import Annotated

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await authenticate_user(token, db)
    if not user:
        raise CredentialsException()
    return user


async def get_active_user(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_active:
        raise InactiveUserException()
    return user


# Use Annotated for reusability
ActiveUser = Annotated[User, Depends(get_active_user)]


@router.get("/me")
async def read_me(user: ActiveUser):
    return user
```

### Settings as Dependencies

```python
from functools import lru_cache
from pydantic_settings import BaseSettings


class AuthSettings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_prefix="AUTH_")


@lru_cache
def get_auth_settings() -> AuthSettings:
    return AuthSettings()
```

## Pydantic Schemas

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AppBaseModel(BaseModel):
    """Project-wide base with consistent serialization."""
    model_config = ConfigDict(
        from_attributes=True,
        ser_json_timedelta="iso8601",
    )


# Separate Create / Read / Update schemas
class PackageCreate(AppBaseModel):
    name: str = Field(..., min_length=1, max_length=200, pattern=r"^[a-zA-Z0-9._-]+$")
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+")
    description: str | None = None


class PackageRead(AppBaseModel):
    id: int
    name: str
    version: str
    description: str | None
    created_at: datetime


class PackageUpdate(AppBaseModel):
    description: str | None = None
```

## Error Handling

### Service-Layer Exceptions (NOT HTTPException)

```python
# app/core/exceptions.py
class AppException(Exception):
    """Base for all application exceptions."""
    def __init__(self, error_code: str, detail: str, status_code: int = 400):
        self.error_code = error_code
        self.detail = detail
        self.status_code = status_code


class NotFoundException(AppException):
    def __init__(self, resource: str, identifier: str | int):
        super().__init__(
            error_code="NOT_FOUND",
            detail=f"{resource} not found",
            status_code=404,
        )


class ConflictException(AppException):
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(error_code="CONFLICT", detail=detail, status_code=409)


# Register globally
def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "error_code": exc.error_code},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error_code": "INTERNAL"},
        )
```

## Database (SQLAlchemy 2.0 Async)

```python
# app/db/engine.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

async_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

async_session_factory = async_sessionmaker(
    async_engine,
    expire_on_commit=False,
)
```

### Repository Pattern

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession


class PackageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_name(self, name: str) -> Package | None:
        result = await self._session.execute(
            select(Package)
            .where(Package.name == name)
            .options(selectinload(Package.releases))  # prevent N+1
        )
        return result.scalar_one_or_none()

    async def create(self, data: PackageCreate) -> Package:
        package = Package(**data.model_dump())
        self._session.add(package)
        await self._session.flush()
        return package
```

### Alembic Naming Conventions

```python
# app/db/base.py
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
```

## Middleware

### Request ID

```python
# app/middleware/request_id.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

## Testing

### Async Test Setup

```python
# tests/conftest.py
import pytest
from httpx import ASGITransport, AsyncClient
from asgi_lifespan import LifespanManager
from app.main import create_app
from app.api.dependencies import get_db


@pytest.fixture
async def app():
    application = create_app()
    async with LifespanManager(application) as manager:
        yield manager.app


@pytest.fixture
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
async def db_session():
    """Override DB dependency with test database."""
    async with test_session_factory() as session:
        yield session


@pytest.fixture
def override_deps(app, db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    app.dependency_overrides.clear()
```

### Test Example

```python
import pytest

@pytest.mark.asyncio
async def test_create_package(client, override_deps):
    response = await client.post("/api/v1/packages/", json={
        "name": "my-package",
        "version": "1.0.0",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "my-package"
```

## Health Check

```python
@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
```

## Performance Checklist

```toml
# pyproject.toml - production extras
[project.optional-dependencies]
production = [
    "uvloop; sys_platform != 'win32'",
    "httptools",
    "orjson",
]
```

```python
# Thread pool tuning in lifespan
import anyio

@asynccontextmanager
async def lifespan(app: FastAPI):
    limiter = anyio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = 100  # default is 40
    # ... rest of lifespan
```

## Deployment

```dockerfile
# Dockerfile
FROM python:3.12-slim AS base
RUN groupadd -r app && useradd -r -g app app
WORKDIR /app

FROM base AS builder
COPY pyproject.toml .
RUN pip install --no-cache-dir ".[production]"

FROM base AS runtime
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src/ ./src/
USER app
EXPOSE 8000
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000"]
```

## Linting & Tooling

```toml
# pyproject.toml
[tool.ruff]
target-version = "py312"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "ASYNC"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

## Sources

- [zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices)
- [kludex/fastapi-tips](https://github.com/kludex/fastapi-tips)
- [FastAPI Official Docs](https://fastapi.tiangolo.com)
- [orchestrator.dev - Production Patterns](https://orchestrator.dev/blog/2025-1-30-fastapi-production-patterns/)
- [FastAPI Boilerplate](https://benavlabs.github.io/FastAPI-boilerplate/)
- [fastapi-practices/fastapi_best_architecture](https://github.com/fastapi-practices/fastapi_best_architecture)
