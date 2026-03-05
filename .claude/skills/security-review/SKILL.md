---
name: security-review
description: Use this skill when adding authentication, handling user input, working with secrets, creating API endpoints, or implementing sensitive features. Provides comprehensive security checklist and patterns for FastAPI/Python.
origin: ECC
---

# Security Review Skill

This skill ensures all code follows security best practices and identifies potential vulnerabilities.

## When to Activate

- Implementing authentication or authorization
- Handling user input or file uploads
- Creating new API endpoints
- Working with secrets or credentials
- Storing or transmitting sensitive data
- Integrating third-party APIs

## Security Checklist

### 1. Secrets Management

#### NEVER Do This
```python
API_KEY = "sk-proj-xxxxx"  # Hardcoded secret
DB_PASSWORD = "password123"  # In source code
```

#### ALWAYS Do This
```python
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    database_url: str

    model_config = {"env_file": ".env"}

settings = Settings()
# Raises ValidationError if required env vars are missing
```

#### Verification Steps
- [ ] No hardcoded API keys, tokens, or passwords
- [ ] All secrets in environment variables
- [ ] `.env` in .gitignore
- [ ] No secrets in git history
- [ ] Production secrets in hosting platform env vars

### 2. Input Validation

#### Always Validate User Input
```python
from pydantic import BaseModel, EmailStr, Field

class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=0, le=150)

@router.post("/api/users")
async def create_user(data: CreateUserRequest):
    # Pydantic validates automatically; invalid input returns 422
    return await user_service.create(data)
```

#### File Upload Validation
```python
from fastapi import UploadFile, HTTPException

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB

async def validate_upload(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Invalid file type")

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, "File too large (max 5MB)")
    await file.seek(0)
```

#### Verification Steps
- [ ] All user inputs validated with Pydantic models
- [ ] File uploads restricted (size, type)
- [ ] No direct use of user input in queries
- [ ] Error messages don't leak sensitive info

### 3. SQL Injection Prevention

#### NEVER Concatenate SQL
```python
# DANGEROUS
query = f"SELECT * FROM users WHERE email = '{user_email}'"
await session.execute(text(query))
```

#### ALWAYS Use Parameterized Queries
```python
# Safe - SQLAlchemy ORM
result = await session.execute(
    select(User).where(User.email == user_email)
)

# Safe - parameterized raw SQL
result = await session.execute(
    text("SELECT * FROM users WHERE email = :email"),
    {"email": user_email},
)
```

#### Verification Steps
- [ ] All database queries use parameterized queries or ORM
- [ ] No string concatenation/f-strings in SQL
- [ ] SQLAlchemy queries properly constructed

### 4. Authentication & Authorization

#### JWT Token Handling
```python
from fastapi import Response

def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=3600,
    )
```

#### Authorization Checks
```python
async def delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized")
    await user_service.delete(user_id)
```

#### Verification Steps
- [ ] Tokens stored in httpOnly cookies (not localStorage if UI exists)
- [ ] Authorization checks before sensitive operations
- [ ] Role-based access control implemented
- [ ] Session management secure

### 5. CSRF Protection

```python
from fastapi import Header, HTTPException

async def verify_csrf(x_csrf_token: str = Header(...)):
    if not csrf_service.verify(x_csrf_token):
        raise HTTPException(403, "Invalid CSRF token")

@router.post("/api/packages", dependencies=[Depends(verify_csrf)])
async def create_package(data: CreatePackageRequest):
    ...
```

### 6. Rate Limiting

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
async def search(request: Request, q: str):
    ...
```

#### Verification Steps
- [ ] Rate limiting on all API endpoints
- [ ] Stricter limits on expensive operations
- [ ] IP-based and user-based rate limiting

### 7. Sensitive Data Exposure

#### Logging
```python
import structlog

logger = structlog.get_logger()

# WRONG
logger.info("user_login", email=email, password=password)

# CORRECT
logger.info("user_login", email=email, user_id=user_id)
```

#### Error Messages
```python
# WRONG
except Exception as e:
    return JSONResponse(
        status_code=500,
        content={"error": str(e), "traceback": traceback.format_exc()},
    )

# CORRECT
except Exception:
    logger.exception("internal_error")
    return JSONResponse(
        status_code=500,
        content={"error": "An error occurred. Please try again."},
    )
```

#### Verification Steps
- [ ] No passwords, tokens, or secrets in logs
- [ ] Error messages generic for users
- [ ] Detailed errors only in server logs
- [ ] No stack traces exposed to users

### 8. Dependency Security

```bash
# Check for vulnerabilities
pip-audit

# Check for outdated packages
pip list --outdated

# Pin dependencies
pip-compile requirements.in
```

#### Verification Steps
- [ ] Dependencies up to date
- [ ] No known vulnerabilities (pip-audit clean)
- [ ] Lock files committed (requirements.txt or poetry.lock)
- [ ] Dependabot enabled on GitHub

## Security Testing

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_requires_authentication(client: AsyncClient):
    response = await client.get("/api/protected")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_requires_admin_role(client: AsyncClient, user_token: str):
    response = await client.get(
        "/api/admin",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_rejects_invalid_input(client: AsyncClient):
    response = await client.post(
        "/api/users",
        json={"email": "not-an-email"},
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_enforces_rate_limits(client: AsyncClient):
    responses = [
        await client.get("/api/endpoint")
        for _ in range(101)
    ]
    rate_limited = [r for r in responses if r.status_code == 429]
    assert len(rate_limited) > 0
```

## Pre-Deployment Security Checklist

Before ANY production deployment:

- [ ] **Secrets**: No hardcoded secrets, all in env vars
- [ ] **Input Validation**: All user inputs validated via Pydantic
- [ ] **SQL Injection**: All queries parameterized (SQLAlchemy ORM or bind params)
- [ ] **Authentication**: Proper token handling
- [ ] **Authorization**: Role checks via FastAPI dependencies
- [ ] **Rate Limiting**: Enabled on all endpoints (slowapi)
- [ ] **HTTPS**: Enforced in production
- [ ] **CORS**: Properly configured via FastAPI CORSMiddleware
- [ ] **Error Handling**: No sensitive data in errors
- [ ] **Logging**: No sensitive data logged
- [ ] **Dependencies**: Up to date, no vulnerabilities (pip-audit)
- [ ] **File Uploads**: Validated (size, type)

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Web Security Academy](https://portswigger.net/web-security)

---

**Remember**: Security is not optional. One vulnerability can compromise the entire platform. When in doubt, err on the side of caution.
