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
from fastapi import APIRouter, Depends

from kingpi.dependencies import get_event_store
from kingpi.schemas.event import EventIn
from kingpi.services.event_store import EventStore

router = APIRouter()


@router.post("/event", status_code=201)
async def post_event(event: EventIn, store: EventStore = Depends(get_event_store)):
    await store.record_event(event.package, event.type, event.timestamp)
    return {"status": "accepted"}
