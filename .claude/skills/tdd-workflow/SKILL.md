---
name: tdd-workflow
description: Use this skill when writing new features, fixing bugs, or refactoring code. Enforces test-driven development with 80%+ coverage including unit, integration, and E2E tests.
origin: ECC
---

# Test-Driven Development Workflow

This skill ensures all code development follows TDD principles with comprehensive test coverage.

## When to Activate

- Writing new features or functionality
- Fixing bugs or issues
- Refactoring existing code
- Adding API endpoints

## Core Principles

### 1. Tests BEFORE Code
ALWAYS write tests first, then implement code to make tests pass.

### 2. Coverage Requirements
- Minimum 80% coverage (unit + integration + E2E)
- All edge cases covered
- Error scenarios tested
- Boundary conditions verified

### 3. Test Types

#### Unit Tests
- Individual functions and utilities
- Service/business logic
- Pure functions
- Helpers and utilities

#### Integration Tests
- API endpoints (FastAPI TestClient / httpx)
- Database operations (SQLAlchemy)
- Service interactions

#### E2E Tests (Playwright or pytest)
- Critical user/API flows
- Complete workflows

## TDD Workflow Steps

### Step 1: Write User Journeys
```
As a [role], I want to [action], so that [benefit]

Example:
As a user, I want to search for packages,
so that I can find relevant packages by name or keyword.
```

### Step 2: Generate Test Cases

```python
import pytest
from httpx import AsyncClient


class TestPackageSearch:
    @pytest.mark.asyncio
    async def test_returns_relevant_packages(self, client: AsyncClient):
        response = await client.get("/api/packages/search", params={"q": "requests"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) > 0

    @pytest.mark.asyncio
    async def test_handles_empty_query(self, client: AsyncClient):
        response = await client.get("/api/packages/search", params={"q": ""})
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_matches(self, client: AsyncClient):
        response = await client.get("/api/packages/search", params={"q": "xyznonexistent"})
        assert response.status_code == 200
        assert response.json()["data"] == []

    @pytest.mark.asyncio
    async def test_sorts_by_relevance(self, client: AsyncClient):
        response = await client.get("/api/packages/search", params={"q": "http"})
        data = response.json()["data"]
        assert len(data) > 1
```

### Step 3: Run Tests (They Should Fail)
```bash
pytest tests/
# Tests should fail - we haven't implemented yet
```

### Step 4: Implement Code
Write minimal code to make tests pass.

### Step 5: Run Tests Again
```bash
pytest tests/
# Tests should now pass
```

### Step 6: Refactor
Improve code quality while keeping tests green.

### Step 7: Verify Coverage
```bash
pytest --cov=src --cov-report=term-missing
# Verify 80%+ coverage achieved
```

## Testing Patterns

### Unit Test Pattern (pytest)
```python
import pytest

def test_calculate_total():
    result = calculate_total(items=[10.0, 20.0, 30.0])
    assert result == 60.0

def test_calculate_total_empty():
    result = calculate_total(items=[])
    assert result == 0.0

def test_calculate_total_negative():
    with pytest.raises(ValueError, match="negative"):
        calculate_total(items=[-1.0])
```

### API Integration Test Pattern
```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
async def client():
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
async def test_validates_query_params(client: AsyncClient):
    response = await client.get("/api/packages", params={"limit": "invalid"})
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_handles_database_errors(client: AsyncClient):
    # Mock database failure scenario
    ...
```

## Test File Organization

```
tests/
├── conftest.py                 # Shared fixtures
├── __init__.py
├── unit/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_utils.py
│   └── test_services.py
├── integration/
│   ├── __init__.py
│   ├── test_api.py
│   └── test_database.py
└── e2e/
    ├── __init__.py
    └── test_workflows.py
```

## Mocking External Services

### Database Mock
```python
from unittest.mock import AsyncMock, patch

@patch("app.services.package_service.PackageRepository")
async def test_service_with_mock_repo(mock_repo):
    mock_repo.find_all.return_value = [
        Package(id=1, name="test-package"),
    ]
    service = PackageService(mock_repo)
    result = await service.list_packages()
    assert len(result) == 1
    mock_repo.find_all.assert_awaited_once()
```

### Redis Mock
```python
@patch("app.cache.redis_client")
async def test_cached_lookup(mock_redis):
    mock_redis.get.return_value = '{"id": 1, "name": "cached-pkg"}'
    result = await get_cached_package(1)
    assert result.name == "cached-pkg"
    mock_redis.get.assert_awaited_once_with("package:1")
```

## Test Coverage Verification

### Run Coverage Report
```bash
pytest --cov=src --cov-report=term-missing --cov-report=html
```

### Coverage Thresholds (pyproject.toml)
```toml
[tool.pytest.ini_options]
addopts = "--cov=src --cov-report=term-missing --cov-fail-under=80"
```

## Common Testing Mistakes to Avoid

### Testing Implementation Details
```python
# BAD: Testing internal state
assert service._cache == {"key": "value"}

# GOOD: Test observable behavior
result = await service.get("key")
assert result == "value"
```

### No Test Isolation
```python
# BAD: Tests depend on each other
def test_creates_user(): ...
def test_updates_same_user(): ...  # depends on previous

# GOOD: Independent tests
def test_creates_user():
    user = create_test_user()
    ...

def test_updates_user():
    user = create_test_user()
    ...
```

## Continuous Testing

### Watch Mode During Development
```bash
ptw  # pytest-watch
# Tests run automatically on file changes
```

### Pre-Commit Hook
```bash
# Runs before every commit
pytest && ruff check .
```

### CI/CD Integration
```yaml
# GitHub Actions
- name: Run Tests
  run: pytest --cov=src --cov-report=xml
- name: Upload Coverage
  uses: codecov/codecov-action@v4
```

## Best Practices

1. **Write Tests First** - Always TDD
2. **One Assert Per Test** - Focus on single behavior
3. **Descriptive Test Names** - `test_search_returns_empty_for_unknown_query`
4. **Arrange-Act-Assert** - Clear test structure
5. **Mock External Dependencies** - Isolate unit tests
6. **Test Edge Cases** - None, empty, boundary values
7. **Test Error Paths** - Not just happy paths
8. **Keep Tests Fast** - Unit tests < 50ms each
9. **Clean Up After Tests** - Use fixtures with teardown
10. **Review Coverage Reports** - Identify gaps

---

**Remember**: Tests are not optional. They are the safety net that enables confident refactoring, rapid development, and production reliability.
