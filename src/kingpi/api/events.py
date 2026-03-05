"""
FastAPI route handlers for the events API.

This module defines the HTTP endpoints related to install/uninstall events.
FastAPI uses a declarative, decorator-based style similar to Flask, but adds:
- Automatic request/response validation via Pydantic models
- Automatic OpenAPI (Swagger) documentation generation
- Native async/await support for non-blocking request handling
- Dependency injection via `Depends(...)` for services like the event store

Key FastAPI concepts used here:
- **APIRouter**: A mini-application that groups related routes. The main `app`
  (in app.py) includes this router with a prefix like `/api/v1`, keeping route
  definitions modular and organized by feature.
- **Response models**: Decorators like `@router.post(..., response_model=Foo)`
  tell FastAPI what shape the response should be, enabling automatic serialization
  and Swagger docs.
- **Dependency injection**: `Depends(get_event_store)` injects a shared service
  instance into route handlers. This avoids global state and makes routes easy
  to test by overriding dependencies (see conftest.py).
"""
from fastapi import APIRouter

# APIRouter groups related endpoints. Think of it as a blueprint (Flask term)
# or a sub-application. The prefix and tags are applied when this router is
# included in the main app via app.include_router(router, prefix="/api/v1").
router = APIRouter()

# Stub — no endpoints yet. Tests should fail (RED phase).
# Route handlers will be added here in the GREEN phase.
