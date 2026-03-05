---
name: e2e-testing
description: E2E and API testing patterns for FastAPI using pytest, httpx, Playwright for UI, configuration, CI/CD integration, and flaky test strategies.
origin: ECC
---

# E2E Testing Patterns

Comprehensive patterns for building stable, fast, and maintainable E2E and API test suites for FastAPI applications.

## Test File Organization

```
tests/
├── e2e/
│   ├── test_auth.py
│   ├── test_packages.py
│   └── test_search.py
├── integration/
│   ├── test_api_endpoints.py
│   └── test_database.py
├── conftest.py
└── playwright/          # If UI testing needed
    ├── test_browse.py
    └── conftest.py
```

## FastAPI TestClient Pattern

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
async def client():
    """Async test client for FastAPI."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_list_packages(client: AsyncClient):
    response = await client.get("/api/packages")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

@pytest.mark.asyncio
async def test_create_package(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/packages",
        json={"name": "test-package", "version": "1.0.0"},
        headers=auth_headers,
    )
    assert response.status_code == 201

@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    response = await client.post("/api/packages", json={"name": "test"})
    assert response.status_code == 401
```

## Database Test Fixtures

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine("postgresql+asyncpg://test:test@localhost/test_db")
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(test_engine):
    async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        async with session.begin():
            yield session
        await session.rollback()
```

## Playwright UI Testing (if applicable)

```python
import pytest
from playwright.sync_api import Page

def test_search_packages(page: Page):
    page.goto("/packages")
    page.wait_for_load_state("networkidle")

    page.locator('[data-testid="search-input"]').fill("requests")
    page.wait_for_response(lambda resp: "/api/search" in resp.url)

    results = page.locator('[data-testid="package-card"]')
    assert results.count() > 0

def test_no_results(page: Page):
    page.goto("/packages")
    page.locator('[data-testid="search-input"]').fill("xyznonexistent123")

    page.locator('[data-testid="no-results"]').wait_for(state="visible")
    assert page.locator('[data-testid="package-card"]').count() == 0
```

## Flaky Test Patterns

### Quarantine

```python
@pytest.mark.skip(reason="Flaky - Issue #123")
def test_flaky_search():
    ...

@pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="Flaky in CI - Issue #123",
)
def test_conditionally_skipped():
    ...
```

### Identify Flakiness

```bash
pytest tests/test_search.py --count=10  # with pytest-repeat
pytest tests/test_search.py --flake-finder  # with pytest-flake-finder
```

## CI/CD Integration

```yaml
# .github/workflows/e2e.yml
name: E2E Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: pytest tests/e2e/ -v --tb=short
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/test_db
```

## Test Report Template

```markdown
# E2E Test Report

**Date:** YYYY-MM-DD HH:MM
**Duration:** Xm Ys
**Status:** PASSING / FAILING

## Summary
- Total: X | Passed: Y (Z%) | Failed: A | Skipped: B

## Failed Tests

### test_name
**File:** `tests/e2e/test_feature.py:45`
**Error:** AssertionError: expected 200 got 500
**Recommended Fix:** [description]
```
