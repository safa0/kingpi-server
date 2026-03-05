---
name: backend-patterns
description: Backend architecture patterns, API design, database optimization, and server-side best practices for FastAPI and Python.
origin: ECC
---

# Backend Development Patterns

Backend architecture patterns and best practices for scalable FastAPI applications.

## When to Activate

- Designing REST API endpoints
- Implementing repository, service, or controller layers
- Optimizing database queries (N+1, indexing, connection pooling)
- Adding caching (Redis, in-memory, HTTP cache headers)
- Setting up background jobs or async processing
- Structuring error handling and validation for APIs
- Building middleware (auth, logging, rate limiting)

## API Design Patterns

### RESTful API Structure

```python
# Resource-based URLs
# GET    /api/packages                 # List resources
# GET    /api/packages/{id}            # Get single resource
# POST   /api/packages                 # Create resource
# PUT    /api/packages/{id}            # Replace resource
# PATCH  /api/packages/{id}            # Update resource
# DELETE /api/packages/{id}            # Delete resource

# Query parameters for filtering, sorting, pagination
# GET /api/packages?status=active&sort=downloads&limit=20&offset=0
```

### Repository Pattern

```python
from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class PackageRepository(ABC):
    @abstractmethod
    async def find_all(self, filters: PackageFilters | None = None) -> list[Package]:
        ...

    @abstractmethod
    async def find_by_id(self, id: int) -> Package | None:
        ...

    @abstractmethod
    async def create(self, data: CreatePackageDTO) -> Package:
        ...

    @abstractmethod
    async def update(self, id: int, data: UpdatePackageDTO) -> Package:
        ...

    @abstractmethod
    async def delete(self, id: int) -> None:
        ...


class SQLAlchemyPackageRepository(PackageRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def find_all(self, filters: PackageFilters | None = None) -> list[Package]:
        query = select(PackageModel)

        if filters and filters.status:
            query = query.where(PackageModel.status == filters.status)

        if filters and filters.limit:
            query = query.limit(filters.limit)

        result = await self._session.execute(query)
        return [Package.model_validate(row) for row in result.scalars().all()]
```

### Service Layer Pattern

```python
class PackageService:
    def __init__(self, package_repo: PackageRepository):
        self._package_repo = package_repo

    async def search_packages(self, query: str, limit: int = 10) -> list[Package]:
        """Search packages with business logic."""
        results = await self._package_repo.search(query, limit=limit)
        # Apply business rules, sorting, etc.
        return sorted(results, key=lambda p: p.downloads, reverse=True)
```

### Middleware / Dependencies Pattern

```python
from fastapi import Depends, HTTPException, Header

async def get_current_user(authorization: str = Header(...)) -> User:
    """FastAPI dependency for authentication."""
    token = authorization.replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        user = await verify_token(token)
        return user
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Usage in route
@router.get("/api/packages")
async def list_packages(user: User = Depends(get_current_user)):
    ...
```

## Database Patterns

### Query Optimization

```python
# GOOD: Select only needed columns
query = select(PackageModel.id, PackageModel.name, PackageModel.status)
    .where(PackageModel.status == "active")
    .order_by(PackageModel.downloads.desc())
    .limit(10)

# BAD: Select everything
query = select(PackageModel)
```

### N+1 Query Prevention

```python
# BAD: N+1 query problem
packages = await session.execute(select(PackageModel))
for pkg in packages.scalars():
    owner = await session.execute(
        select(UserModel).where(UserModel.id == pkg.owner_id)
    )

# GOOD: Eager loading with joinedload
from sqlalchemy.orm import joinedload

query = select(PackageModel).options(joinedload(PackageModel.owner))
result = await session.execute(query)
```

### Transaction Pattern

```python
async def create_package_with_release(
    session: AsyncSession,
    package_data: CreatePackageDTO,
    release_data: CreateReleaseDTO,
) -> Package:
    async with session.begin():
        package = PackageModel(**package_data.model_dump())
        session.add(package)
        await session.flush()

        release = ReleaseModel(package_id=package.id, **release_data.model_dump())
        session.add(release)

    return Package.model_validate(package)
```

## Caching Strategies

### Redis Caching Layer

```python
import json
from redis.asyncio import Redis

class CachedPackageRepository:
    def __init__(self, base_repo: PackageRepository, redis: Redis):
        self._base_repo = base_repo
        self._redis = redis

    async def find_by_id(self, id: int) -> Package | None:
        cache_key = f"package:{id}"
        cached = await self._redis.get(cache_key)

        if cached:
            return Package.model_validate_json(cached)

        package = await self._base_repo.find_by_id(id)

        if package:
            await self._redis.setex(cache_key, 300, package.model_dump_json())

        return package

    async def invalidate_cache(self, id: int) -> None:
        await self._redis.delete(f"package:{id}")
```

## Error Handling Patterns

### Centralized Error Handler

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

class ApiError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message

app = FastAPI()

@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.message},
    )

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"success": False, "error": "Validation failed", "details": exc.errors()},
    )
```

### Retry with Exponential Backoff

```python
import asyncio
from typing import TypeVar, Callable, Awaitable

T = TypeVar("T")

async def retry_with_backoff(
    fn: Callable[[], Awaitable[T]],
    max_retries: int = 3,
) -> T:
    last_error: Exception | None = None

    for i in range(max_retries):
        try:
            return await fn()
        except Exception as e:
            last_error = e
            if i < max_retries - 1:
                delay = (2 ** i) * 1.0
                await asyncio.sleep(delay)

    raise last_error  # type: ignore[misc]
```

## Authentication & Authorization

### JWT Token Validation

```python
from datetime import datetime, timezone
import jwt
from pydantic import BaseModel

class JWTPayload(BaseModel):
    user_id: str
    email: str
    role: str

def verify_token(token: str) -> JWTPayload:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return JWTPayload(**payload)
    except jwt.PyJWTError:
        raise ApiError(401, "Invalid token")

async def require_auth(request: Request) -> JWTPayload:
    auth_header = request.headers.get("authorization", "")
    token = auth_header.replace("Bearer ", "")
    if not token:
        raise ApiError(401, "Missing authorization token")
    return verify_token(token)
```

### Role-Based Access Control

```python
from enum import StrEnum
from functools import wraps

class Permission(StrEnum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"

ROLE_PERMISSIONS: dict[str, list[Permission]] = {
    "admin": [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN],
    "moderator": [Permission.READ, Permission.WRITE, Permission.DELETE],
    "user": [Permission.READ, Permission.WRITE],
}

def has_permission(user: JWTPayload, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(user.role, [])

def require_permission(permission: Permission):
    async def dependency(user: JWTPayload = Depends(require_auth)) -> JWTPayload:
        if not has_permission(user, permission):
            raise ApiError(403, "Insufficient permissions")
        return user
    return Depends(dependency)

# Usage
@router.delete("/api/packages/{id}")
async def delete_package(
    id: int,
    user: JWTPayload = require_permission(Permission.DELETE),
):
    ...
```

## Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/api/packages")
@limiter.limit("100/minute")
async def list_packages(request: Request):
    ...

@router.get("/api/search")
@limiter.limit("10/minute")
async def search_packages(request: Request, q: str):
    ...
```

## Background Jobs & Queues

```python
from fastapi import BackgroundTasks

async def index_package(package_id: int) -> None:
    """Background task to index a package."""
    # indexing logic
    ...

@router.post("/api/packages")
async def create_package(
    data: CreatePackageDTO,
    background_tasks: BackgroundTasks,
):
    package = await package_service.create(data)
    background_tasks.add_task(index_package, package.id)
    return {"success": True, "data": package}
```

## Structured Logging

```python
import structlog

logger = structlog.get_logger()

@router.get("/api/packages")
async def list_packages(request: Request):
    request_id = request.headers.get("x-request-id", "")
    logger.info("fetching_packages", request_id=request_id, method="GET", path="/api/packages")

    try:
        packages = await package_service.list_all()
        return {"success": True, "data": packages}
    except Exception:
        logger.exception("failed_to_fetch_packages", request_id=request_id)
        raise ApiError(500, "Internal server error")
```

**Remember**: Backend patterns enable scalable, maintainable server-side applications. Choose patterns that fit your complexity level.
